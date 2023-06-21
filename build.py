import os
from nornir import InitNornir
from nornir_napalm.plugins.tasks import napalm_configure
from nornir_utils.plugins.functions import print_result
import pyavd


def deploy_network(task):
    """deploying stuff"""
    _deploy = task.run(
        name=f"{task.host.name}: Configuring with NAPALM",
        task=napalm_configure,
        filename=f"configs/{task.host.name}.cfg",
    )


def patch_pyeapi_ciphers():
    """
    Patch pyeapi to set ssl context ciphers, because Python set defaults that might be too high,
    see https://github.com/python/cpython/blob/3.10/Modules/_ssl.c#L158

    ```sh
    python -c 'import ssl; print(ssl._DEFAULT_CIPHERS)'
    @SECLEVEL=2:ECDH+AESGCM:ECDH+CHACHA20:ECDH+AES:DHE+AES:!aNULL:!eNULL:!aDSS:!SHA1:!AESCCM
    ```
    """
    try:
        import pyeapi.eapilib
    except ImportError:
        return

    connect_orig = pyeapi.eapilib.HttpsConnection.connect

    def connect(self):
        self._context.set_ciphers("DEFAULT@SECLEVEL=2")
        return connect_orig(self)

    pyeapi.eapilib.HttpsConnection.connect = connect


def main():
    """
    Main function that calls deploy_network function
    """

    nr = InitNornir(config_file="config.yml")

    patch_pyeapi_ciphers()

    hostvars = {}

    for hostname in nr.inventory.hosts:
        host = nr.inventory.hosts[hostname]

        # Using .dict() or .data was not getting the group variables
        data = host.items()
        res = {}
        for k, v in data:
            res[k] = v

        hostvars[hostname] = res

    # Validate input and convert types as needed
    pyavd.validate_inputs(hostvars)

    # Generate facts
    avd_facts = pyavd.get_avd_facts(hostvars)
    structured_configs = {
        hostname: pyavd.get_device_structured_config(
            hostname, hostvars[hostname], avd_facts
        )
        for hostname in hostvars
    }
    configs = {
        hostname: pyavd.get_device_config(hostname, structured_configs[hostname])
        for hostname in structured_configs
    }

    # Ensure the 'configs' directory exists
    if not os.path.exists("configs"):
        os.makedirs("configs")

    for hostname, config in configs.items():
        config_path = f"configs/{hostname}.cfg"
        with open(
            config_path,
            "w",
            encoding="utf-8",
        ) as file:
            file.write(config)

        # Get byte count of the file
        byte_count = os.path.getsize(config_path)

        print(
            f"Written config for {hostname} to {config_path}, byte count: {byte_count}"
        )

    result = nr.run(task=deploy_network)

    print_result(result)


if __name__ == "__main__":
    main()
