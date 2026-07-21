resource "aws_route53_zone" "allexpense" {
  name = "allexpense.me"
  tags = local.tags
}

data "kubernetes_service" "ingress_nginx" {
  metadata {
    name      = "ingress-nginx-controller"
    namespace = "ingress-nginx"
  }
  depends_on = [helm_release.ingress_nginx]
}

data "aws_elb_hosted_zone_id" "main" {}

resource "aws_route53_record" "apex" {
  zone_id = aws_route53_zone.allexpense.zone_id
  name    = "allexpense.me"
  type    = "A"

  alias {
    name                   = data.kubernetes_service.ingress_nginx.status[0].load_balancer[0].ingress[0].hostname
    zone_id                = data.aws_elb_hosted_zone_id.main.id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "wildcard" {
  zone_id = aws_route53_zone.allexpense.zone_id
  name    = "*.allexpense.me"
  type    = "A"

  alias {
    name                   = data.kubernetes_service.ingress_nginx.status[0].load_balancer[0].ingress[0].hostname
    zone_id                = data.aws_elb_hosted_zone_id.main.id
    evaluate_target_health = true
  }
}

output "nameservers" {
  value       = aws_route53_zone.allexpense.name_servers
  description = "Copy these 4 nameservers into Namecheap DNS settings"
}
