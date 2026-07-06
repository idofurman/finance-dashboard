terraform {
  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

provider "kubernetes" {
  config_path = "~/.kube/config"
}

provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
  }
}

resource "kubernetes_secret" "finance_secrets" {
  metadata {
    name = "finance-secrets"
  }
  data = {
    anthropic-api-key = var.anthropic_api_key
  }
}

resource "helm_release" "finance" {
  name      = "finance"
  chart     = "../finance-chart"
}