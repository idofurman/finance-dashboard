locals {
  tags = {
    Project     = "finance-dashboard"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
