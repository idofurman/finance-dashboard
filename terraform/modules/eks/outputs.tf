output "cluster_name" {
  description = "Name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "URL of the EKS API server"
  value       = module.eks.cluster_endpoint
}

output "cluster_ca_certificate" {
  description = "Base64-encoded certificate authority data for the cluster"
  value       = module.eks.cluster_certificate_authority_data
}

output "oidc_provider_arn" {
  description = "ARN of the OIDC provider — used for IAM Roles for Service Accounts (IRSA)"
  value       = module.eks.oidc_provider_arn
}

output "cluster_oidc_issuer_url" {
  description = "OIDC issuer URL of the cluster — used to build IRSA trust policies"
  value       = module.eks.cluster_oidc_issuer_url
}
