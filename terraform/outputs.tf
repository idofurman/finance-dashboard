output "cluster_name" {
  description = "EKS cluster name — use with: aws eks update-kubeconfig --name <value>"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "URL of the EKS API server"
  value       = module.eks.cluster_endpoint
}

output "ecr_urls" {
  description = "ECR repository URLs for backend and frontend"
  value       = module.ecr.repository_urls
}

output "dns_nameservers" {
  description = "Nameservers to set at your domain registrar (allexpense.me)"
  value       = module.dns.nameservers
}

output "state_bucket" {
  description = "S3 bucket storing Terraform state"
  value       = module.s3.bucket_name
}
