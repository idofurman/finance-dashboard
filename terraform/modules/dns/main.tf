resource "aws_route53_zone" "this" {
  name = var.domain
  tags = var.tags
}

resource "aws_route53_record" "root" {
  zone_id = aws_route53_zone.this.zone_id
  name    = var.domain
  type    = "CNAME"
  ttl     = 300
  records = [var.load_balancer_hostname]
}

resource "aws_route53_record" "www" {
  zone_id = aws_route53_zone.this.zone_id
  name    = "www.${var.domain}"
  type    = "CNAME"
  ttl     = 300
  records = [var.load_balancer_hostname]
}
