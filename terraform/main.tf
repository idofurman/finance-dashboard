module "vpc" {
  source       = "./modules/vpc"
  name         = "finance-vpc"
  cluster_name = "finance-eks"
  tags         = local.tags
}

module "eks" {
  source     = "./modules/eks"
  cluster_name = "finance-eks"
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  tags       = local.tags
}

module "ecr" {
  source = "./modules/ecr"
  repository_names = [
    "finance-backend",
    "finance-frontend",
    "finance-receipt-service",
    "finance-exchange-rate-service",
  ]
  tags = local.tags
}

# DNS: the allexpense.me hosted zone and A record were created manually in Route53.
# To bring DNS under Terraform management:
#   1. Add route53:ChangeResourceRecordSets + route53:CreateHostedZone to the CI IAM user
#   2. Import the existing hosted zone: terraform import module.dns.aws_route53_zone.this <ZONE_ID>
#   3. Uncomment the module below
# module "dns" {
#   source                 = "./modules/dns"
#   domain                 = "allexpense.me"
#   load_balancer_hostname = var.load_balancer_hostname
#   tags                   = local.tags
# }
