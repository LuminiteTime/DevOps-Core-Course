# LAB04 - Infrastructure as Code (Terraform and Pulumi)

## 1. Cloud Provider and Infrastructure

- Provider: Yandex Cloud
  - Reason: recommended for Russia-based students, free tier available, no credit card required.
- Region/zone: ru-central1-a
- Instance type: standard-v2, 2 cores at 20% fraction, 1 GB RAM
- Boot disk: 10 GB network-hdd, Ubuntu 22.04 LTS
- Total cost: $0 (within free tier limits)
- Resources created (per tool):
  - VPC network
  - VPC subnet (10.0.1.0/24)
  - Security group (SSH/22, HTTP/80, App/5000 inbound; all outbound)
  - Compute instance with public IP

## 2. Terraform Implementation

Terraform version: 1.5.7 (Homebrew, last open-source release)

Yandex Cloud provider: yandex-cloud/yandex v0.187.0 (installed via `terraform-mirror.yandexcloud.net` because `registry.terraform.io` is blocked from Russia).

Project structure:

```text
terraform/
  .gitignore        # state, tfvars, .terraform/
  main.tf           # provider, data source, resources
  variables.tf      # input variables with defaults
  outputs.tf        # public IP, private IP, SSH command
```

Key decisions:

- All configurable values (zone, platform, cores, memory, disk, image family, SSH user) extracted into variables with sensible defaults.
- Outputs expose the public IP and a ready-to-paste SSH command.
- Authentication via environment variables (`YC_CLOUD_ID`, `YC_FOLDER_ID`, `YC_SERVICE_ACCOUNT_KEY_FILE`) -- no secrets in code.
- Used `user-data` cloud-config metadata instead of `ssh-keys` because the latter did not propagate the key on the Ubuntu 22.04 image.

Challenges:

- `registry.terraform.io` is unreachable from the network. Fixed by configuring `~/.terraformrc` with `terraform-mirror.yandexcloud.net` as a network mirror.
- The `ssh-keys` metadata field was not picked up by cloud-init on the Ubuntu 22.04 image. Switched to `user-data` with full cloud-config and recreated the VM.

### terraform init

```text
Initializing the backend...
Initializing provider plugins...
- Finding yandex-cloud/yandex versions matching "~> 0.135"...
- Installing yandex-cloud/yandex v0.187.0...
- Installed yandex-cloud/yandex v0.187.0 (unauthenticated)

Terraform has been successfully initialized!
```

### terraform plan

```text
data.yandex_compute_image.ubuntu: Read complete after 0s [id=fd8t9g30r3pc23et5krl]

Terraform will perform the following actions:

  # yandex_compute_instance.lab will be created
  + resource "yandex_compute_instance" "lab" {
      + hostname    = "lab04-vm"
      + name        = "lab04-vm"
      + platform_id = "standard-v2"
      + zone        = "ru-central1-a"
      + labels      = { "project" = "devops-lab04", "tool" = "terraform" }
      + resources { cores = 2, core_fraction = 20, memory = 1 }
      + boot_disk { image_id = "fd8t9g30r3pc23et5krl", size = 10, type = "network-hdd" }
      + network_interface { subnet_id = (known after apply), nat = true }
    }

  # yandex_vpc_network.lab will be created
  + resource "yandex_vpc_network" "lab" { name = "lab04-network" }

  # yandex_vpc_security_group.lab will be created
  + resource "yandex_vpc_security_group" "lab" {
      + name = "lab04-sg"
      + ingress { description = "SSH",  port = 22,   protocol = "TCP" }
      + ingress { description = "HTTP", port = 80,   protocol = "TCP" }
      + ingress { description = "App",  port = 5000, protocol = "TCP" }
      + egress  { description = "Allow all outbound", protocol = "ANY" }
    }

  # yandex_vpc_subnet.lab will be created
  + resource "yandex_vpc_subnet" "lab" {
      + name = "lab04-subnet", zone = "ru-central1-a", v4_cidr_blocks = ["10.0.1.0/24"]
    }

Plan: 4 to add, 0 to change, 0 to destroy.
```

### terraform apply

```text
yandex_vpc_network.lab: Creating...
yandex_vpc_network.lab: Creation complete after 3s [id=enpvte4s34qj0q38is12]
yandex_vpc_subnet.lab: Creating...
yandex_vpc_security_group.lab: Creating...
yandex_vpc_subnet.lab: Creation complete after 0s [id=e9b5viveamq80l3p8ibs]
yandex_vpc_security_group.lab: Creation complete after 2s [id=enp7oirsi4f9st9tqhov]
yandex_compute_instance.lab: Creating...
yandex_compute_instance.lab: Creation complete after 43s [id=fhmfdsq5cbtis1qg36j3]

Apply complete! Resources: 4 added, 0 changed, 0 destroyed.

Outputs:
ssh_command   = "ssh -i ~/.ssh/id_ed25519 yc-user@93.77.187.164"
vm_private_ip = "10.0.1.20"
vm_public_ip  = "93.77.187.164"
```

### SSH access proof

```text
$ ssh -i ~/.ssh/id_ed25519 yc-user@93.77.187.164 "hostname && uname -a && uptime"
lab04-vm
Linux lab04-vm 5.15.0-170-generic #180-Ubuntu SMP Fri Jan 9 16:10:31 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux
 09:51:44 up 0 min,  0 users,  load average: 0.23, 0.07, 0.02
```

## 3. Pulumi Implementation

Pulumi version: 3.222.0, language: Python 3.11

Provider package: `pulumi-yandex` (installed via pip into a virtual environment).

Project structure:

```text
pulumi/
  .gitignore           # venv/, .pulumi-state/, Pulumi.*.yaml, __pycache__/
  Pulumi.yaml          # project metadata (name, runtime)
  requirements.txt     # pulumi, pulumi-yandex
  __main__.py          # all infrastructure definitions
```

How code differs from Terraform:

- Resources are Python objects (`yandex.VpcNetwork(...)`) instead of HCL blocks.
- Data source call is a regular function (`yandex.get_compute_image(family=...)`).
- Outputs use `pulumi.export(...)` instead of `output` blocks.
- Variables are plain Python / Pulumi config (`config.get(...)`) rather than a separate `variables.tf` file.
- The security group rules use typed `*Args` dataclasses.

Advantages discovered:

- IDE autocompletion and type hints reduce guessing about argument names.
- Composing user-data strings with f-strings is more natural than HCL `<<-EOF` heredocs.
- Everything lives in a single `.py` file without requiring multiple `.tf` files.

Challenges:

- Local backend requires explicitly setting `PULUMI_BACKEND_URL` and `PULUMI_CONFIG_PASSPHRASE`.
- The `pulumi-yandex` provider emits a deprecation warning about `pkg_resources` - cosmetic, no functional impact.

### terraform destroy (before Pulumi)

```text
yandex_compute_instance.lab: Destroying... [id=fhmfdsq5cbtis1qg36j3]
yandex_compute_instance.lab: Destruction complete after 43s
yandex_vpc_subnet.lab: Destroying... [id=e9b5viveamq80l3p8ibs]
yandex_vpc_security_group.lab: Destroying... [id=enp7oirsi4f9st9tqhov]
yandex_vpc_security_group.lab: Destruction complete after 1s
yandex_vpc_subnet.lab: Destruction complete after 5s
yandex_vpc_network.lab: Destroying... [id=enpvte4s34qj0q38is12]
yandex_vpc_network.lab: Destruction complete after 2s

Destroy complete! Resources: 4 destroyed.
```

### pulumi preview

```text
Previewing update (dev):
 +  pulumi:pulumi:Stack lab04-pulumi-dev create
 +  yandex:index:VpcNetwork lab04-network create
 +  yandex:index:VpcSubnet lab04-subnet create
 +  yandex:index:VpcSecurityGroup lab04-sg create
 +  yandex:index:ComputeInstance lab04-vm create

Resources:
    + 5 to create
```

### pulumi up

```text
Updating (dev):
 +  yandex:index:VpcNetwork lab04-network created (2s)
 +  yandex:index:VpcSecurityGroup lab04-sg created (2s)
 +  yandex:index:VpcSubnet lab04-subnet created (0.85s)
 +  yandex:index:ComputeInstance lab04-vm created (59s)
 +  pulumi:pulumi:Stack lab04-pulumi-dev created (65s)

Outputs:
    ssh_command  : "ssh -i ~/.ssh/id_ed25519 yc-user@93.77.191.242"
    vm_private_ip: "10.0.1.10"
    vm_public_ip : "93.77.191.242"

Resources:
    + 5 created
Duration: 1m6s
```

### SSH access proof (Pulumi VM)

```text
$ ssh -i ~/.ssh/id_ed25519 yc-user@93.77.191.242 "hostname && uname -a && uptime"
lab04-vm
Linux lab04-vm 5.15.0-170-generic #180-Ubuntu SMP Fri Jan 9 16:10:31 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux
 09:56:11 up 0 min,  0 users,  load average: 0.12, 0.04, 0.01
```

## 4. Terraform vs Pulumi Comparison

- Ease of Learning: Terraform was slightly easier to start with because HCL is purpose-built for infrastructure and the documentation structure maps directly to resource blocks. Pulumi requires knowing both the cloud API and the Python SDK conventions.

- Code Readability: For this small project both are comparable. Terraform's declarative style makes it obvious what resources exist. Pulumi's Python code is familiar to developers but mixes infrastructure declarations with imperative logic.

- Debugging: Terraform errors reference specific HCL blocks and line numbers, which is straightforward. Pulumi errors include Python tracebacks, which can be noisier but give more context for complex logic errors.

- Documentation: Terraform has a larger community and more examples online. The Yandex Cloud Terraform provider docs are comprehensive. The Pulumi Yandex provider docs are thinner and the package itself shows deprecation warnings.

- Use Case: Terraform fits well for declarative, auditable infrastructure definitions where the team includes non-developers. Pulumi is better when infrastructure requires complex logic (loops, conditionals, abstractions) and the team is comfortable writing code.

## 5. Lab 5 Preparation and Cleanup

VM for Lab 5: No - all cloud resources have been destroyed. Will recreate using Terraform when Lab 5 begins (takes under a minute with the existing code).

### Cleanup status

Both tools' resources fully destroyed:

Terraform:

```text
Destroy complete! Resources: 4 destroyed.
```

Pulumi:

```text
Resources:
    - 5 deleted
Duration: 48s
```

No compute instances, networks, or security groups remain in the Yandex Cloud folder.
