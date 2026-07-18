variable "aws_region" {
  description = "AWS region to deploy all resources into"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name — applied as a tag to every resource"
  type        = string
  default     = "production"
}

variable "anthropic_api_key" {
  description = "Anthropic API key for the receipt scanner feature"
  type        = string
  sensitive   = true
}

variable "load_balancer_hostname" {
  description = "Hostname of the EKS load balancer — set this after the cluster is created"
  type        = string
  default     = ""
}
