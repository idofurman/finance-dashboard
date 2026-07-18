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


