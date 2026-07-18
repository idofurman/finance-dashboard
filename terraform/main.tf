module "s3" {
  source      = "./modules/s3"
  bucket_name = "finance-dashboard-tfstate-579083551085"
  tags        = local.tags
}

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

module "dns" {
  source                 = "./modules/dns"
  domain                 = "allexpense.me"
  load_balancer_hostname = var.load_balancer_hostname
  tags                   = local.tags
}
