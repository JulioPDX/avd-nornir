from pathlib import Path
from nornir import InitNornir
from nornir_napalm.plugins.tasks import napalm_configure
from nornir_utils.plugins.functions import print_result
from rich import print
import pyavd


# def deploy_network(task):
#     """deploying stuff"""
#     _deploy = task.run(
#         name=f"{task.host.name}: Configuring with NAPALM",
#         task=napalm_configure,
#         filename=f"configs/{task.host.name}.cfg",
#         replace=True,
#     )


def patch_pyeapi_ciphers():
    """
    Patch pyeapi to set ssl context ciphers, because Python set defaults that might
    be too high, see https://github.com/python/cpython/blob/3.10/Modules/_ssl.c#L158

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


def create_files(doc_type, content, extension):
    """Loop over content to create relevant files for hosts."""
    if not Path(f"{doc_type}").exists():
        Path(f"{doc_type}").mkdir(parents=True)

    for hostname, doc in content.items():
        doc_path = f"{doc_type}/{hostname}.{extension}"
        with open(
            doc_path,
            "w",
            encoding="utf-8",
        ) as file:
            file.write(doc)


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
        # data = host.items()
        res = {}
        for k, v in host.items():
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

    # print(structured_configs["leaf1"])

    configs = {
        hostname: pyavd.get_device_config(hostname, structured_configs[hostname])
        for hostname in structured_configs
    }

    create_files("configs", configs, "cfg")

    docs = {
        hostname: pyavd.get_device_doc(hostname, structured_configs[hostname])
        for hostname in structured_configs
    }

    create_files("docs", docs, "md")

    # result = nr.run(task=deploy_network)

    # print_result(result)


if __name__ == "__main__":
    main()
