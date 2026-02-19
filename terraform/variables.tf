variable "zone" {
  description = "Yandex Cloud availability zone"
  type        = string
  default     = "ru-central1-a"
}

variable "platform_id" {
  description = "VM platform identifier"
  type        = string
  default     = "standard-v2"
}

variable "cores" {
  description = "Number of CPU cores"
  type        = number
  default     = 2
}

variable "core_fraction" {
  description = "Guaranteed vCPU share (%)"
  type        = number
  default     = 20
}

variable "memory" {
  description = "RAM in GB"
  type        = number
  default     = 1
}

variable "disk_size" {
  description = "Boot disk size in GB"
  type        = number
  default     = 10
}

variable "disk_type" {
  description = "Boot disk type"
  type        = string
  default     = "network-hdd"
}

variable "image_family" {
  description = "OS image family"
  type        = string
  default     = "ubuntu-2204-lts"
}

variable "ssh_username" {
  description = "SSH user created on the VM"
  type        = string
  default     = "yc-user"
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key"
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

variable "labels" {
  description = "Resource labels"
  type        = map(string)
  default = {
    project = "devops-lab04"
    tool    = "terraform"
  }
}
