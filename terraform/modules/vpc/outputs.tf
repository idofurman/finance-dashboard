output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "private_subnets" {
  description = "IDs of the private subnets (used by EKS worker nodes)"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "IDs of the public subnets (used by load balancers)"
  value       = module.vpc.public_subnets
}
