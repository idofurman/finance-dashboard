variable "domain" {
  description = "Root domain name (e.g. allexpense.me)"
  type        = string
}

variable "load_balancer_hostname" {
  description = "Hostname of the EKS load balancer to point the domain at"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
