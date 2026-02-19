output "vm_public_ip" {
  description = "Public IP address of the VM"
  value       = yandex_compute_instance.lab.network_interface[0].nat_ip_address
}

output "vm_private_ip" {
  description = "Private IP address of the VM"
  value       = yandex_compute_instance.lab.network_interface[0].ip_address
}

output "ssh_command" {
  description = "SSH command to connect to the VM"
  value       = "ssh -i ~/.ssh/id_ed25519 ${var.ssh_username}@${yandex_compute_instance.lab.network_interface[0].nat_ip_address}"
}
