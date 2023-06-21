from nornir import InitNornir
from rich import print, inspect
import pyavd
import os


nr = InitNornir(config_file="config.yml")

hostvars = {}

for hostname in nr.inventory.hosts:
    host = nr.inventory.hosts[hostname]

    # Using .dict() or .data was not getting the group variables
    data = host.items()
    res = {}
    for (k, v) in data:
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
    with open(config_path, "w") as file:
        file.write(config)

    # Get byte count of the file
    byte_count = os.path.getsize(config_path)

    print(f"Written config for {hostname} to {config_path}, byte count: {byte_count}")
