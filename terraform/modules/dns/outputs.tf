output "zone_id" {
  description = "Route53 hosted zone ID"
  value       = aws_route53_zone.this.zone_id
}

output "nameservers" {
  description = "Nameservers to configure at your domain registrar"
  value       = aws_route53_zone.this.name_servers
}
