terraform {
  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = "~> 0.135"
    }
  }
  required_version = ">= 1.5"
}

provider "yandex" {
  zone = var.zone
}

data "yandex_compute_image" "ubuntu" {
  family = var.image_family
}

resource "yandex_vpc_network" "lab" {
  name   = "lab04-network"
  labels = var.labels
}

resource "yandex_vpc_subnet" "lab" {
  name           = "lab04-subnet"
  zone           = var.zone
  network_id     = yandex_vpc_network.lab.id
  v4_cidr_blocks = ["10.0.1.0/24"]
  labels         = var.labels
}

resource "yandex_vpc_security_group" "lab" {
  name       = "lab04-sg"
  network_id = yandex_vpc_network.lab.id
  labels     = var.labels

  ingress {
    description    = "SSH"
    protocol       = "TCP"
    port           = 22
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description    = "HTTP"
    protocol       = "TCP"
    port           = 80
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description    = "App"
    protocol       = "TCP"
    port           = 5000
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description    = "Allow all outbound"
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "yandex_compute_instance" "lab" {
  name        = "lab04-vm"
  hostname    = "lab04-vm"
  platform_id = var.platform_id
  zone        = var.zone
  labels      = var.labels

  resources {
    cores         = var.cores
    core_fraction = var.core_fraction
    memory        = var.memory
  }

  boot_disk {
    initialize_params {
      image_id = data.yandex_compute_image.ubuntu.id
      size     = var.disk_size
      type     = var.disk_type
    }
  }

  network_interface {
    subnet_id          = yandex_vpc_subnet.lab.id
    nat                = true
    security_group_ids = [yandex_vpc_security_group.lab.id]
  }

  metadata = {
    user-data = <<-EOF
      #cloud-config
      users:
        - name: ${var.ssh_username}
          sudo: ALL=(ALL) NOPASSWD:ALL
          shell: /bin/bash
          ssh_authorized_keys:
            - ${file(var.ssh_public_key_path)}
      EOF
  }
}
