import pulumi
import pulumi_yandex as yandex

config = pulumi.Config()
zone = config.get("zone") or "ru-central1-a"
ssh_username = config.get("sshUsername") or "yc-user"
ssh_pub_key_path = config.get("sshPubKeyPath") or "~/.ssh/id_ed25519.pub"

import os

ssh_pub_key = open(os.path.expanduser(ssh_pub_key_path)).read().strip()

labels = {"project": "devops-lab04", "tool": "pulumi"}

image = yandex.get_compute_image(family="ubuntu-2204-lts")

network = yandex.VpcNetwork("lab04-network", name="lab04-network", labels=labels)

subnet = yandex.VpcSubnet(
    "lab04-subnet",
    name="lab04-subnet",
    zone=zone,
    network_id=network.id,
    v4_cidr_blocks=["10.0.1.0/24"],
    labels=labels,
)

sg = yandex.VpcSecurityGroup(
    "lab04-sg",
    name="lab04-sg",
    network_id=network.id,
    labels=labels,
    ingresses=[
        yandex.VpcSecurityGroupIngressArgs(
            description="SSH", protocol="TCP", port=22, v4_cidr_blocks=["0.0.0.0/0"]
        ),
        yandex.VpcSecurityGroupIngressArgs(
            description="HTTP", protocol="TCP", port=80, v4_cidr_blocks=["0.0.0.0/0"]
        ),
        yandex.VpcSecurityGroupIngressArgs(
            description="App", protocol="TCP", port=5000, v4_cidr_blocks=["0.0.0.0/0"]
        ),
    ],
    egresses=[
        yandex.VpcSecurityGroupEgressArgs(
            description="Allow all outbound",
            protocol="ANY",
            v4_cidr_blocks=["0.0.0.0/0"],
        ),
    ],
)

user_data = f"""#cloud-config
users:
  - name: {ssh_username}
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - {ssh_pub_key}
"""

vm = yandex.ComputeInstance(
    "lab04-vm",
    name="lab04-vm",
    hostname="lab04-vm",
    platform_id="standard-v2",
    zone=zone,
    labels=labels,
    resources=yandex.ComputeInstanceResourcesArgs(
        cores=2, core_fraction=20, memory=1
    ),
    boot_disk=yandex.ComputeInstanceBootDiskArgs(
        initialize_params=yandex.ComputeInstanceBootDiskInitializeParamsArgs(
            image_id=image.id, size=10, type="network-hdd"
        )
    ),
    network_interfaces=[
        yandex.ComputeInstanceNetworkInterfaceArgs(
            subnet_id=subnet.id, nat=True, security_group_ids=[sg.id]
        )
    ],
    metadata={"user-data": user_data},
)

pulumi.export("vm_public_ip", vm.network_interfaces[0].nat_ip_address)
pulumi.export("vm_private_ip", vm.network_interfaces[0].ip_address)
pulumi.export(
    "ssh_command",
    vm.network_interfaces[0].nat_ip_address.apply(
        lambda ip: f"ssh -i ~/.ssh/id_ed25519 {ssh_username}@{ip}"
    ),
)
