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
  ]
  tags = local.tags
}

# DNS module requires route53:CreateHostedZone permission on the CI user.
# Uncomment once that permission is added to the CI IAM user.
# module "dns" {
#   source                 = "./modules/dns"
#   domain                 = "allexpense.me"
#   load_balancer_hostname = var.load_balancer_hostname
#   tags                   = local.tags
# }
