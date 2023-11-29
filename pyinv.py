import time
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from rich.progress import Progress
from pyavd import get_avd_facts, get_device_structured_config, get_device_config


dl = DataLoader()
im = InventoryManager(loader=dl, sources=["inventory.yml"])
vm = VariableManager(loader=dl, inventory=im)

hosts = {}

for host in im.get_hosts("all"):
    host_vars = vm.get_vars(host=host)
    hosts[str(host)] = host_vars

with Progress() as progress:
    total = len(hosts)
    task1 = progress.add_task("[red]facts...", total = total)
    task2 = progress.add_task("[yellow]structured config...", total = total)
    task3 = progress.add_task("[green]build config...", total = total)

    for k, v in hosts.items():
        facts = get_avd_facts(hosts)
        progress.update(task1, advance=1)
        time.sleep(.5)

        struct_conf = get_device_structured_config(k, v, facts)
        progress.update(task2, advance=1)
        time.sleep(.5)

        config = get_device_config(struct_conf)
        with open(f"py_conf/{k}.cfg", "w") as f:
            f.writelines(config)
        progress.update(task3, advance=1)
        time.sleep(.5)
