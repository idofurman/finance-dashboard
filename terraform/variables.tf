variable "anthropic_api_key" {
  description = "Anthropic API key for receipt scanner"
  type        = string
  sensitive   = true
}

variable "admin_cidr_blocks" {
  description = "Your home/office IP ranges allowed to SSH and access k3s API. Get your IP: curl ifconfig.me"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Override in terraform.tfvars: admin_cidr_blocks = ["YOUR_IP/32"]
}