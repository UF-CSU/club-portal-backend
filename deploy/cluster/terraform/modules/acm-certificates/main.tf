###############################
### ACM Certificates Module ###
###############################
#
# Reference: https://www.stacksimplify.com/aws-eks/aws-alb-ingress/learn-to-enable-ssl-on-alb-ingress-service-in-kubernetes-on-aws-eks/
# Reference: https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.1/guide/ingress/cert_discovery/
#
# Module based on: https://github.com/terraform-aws-modules/terraform-aws-acm
#

locals {
  target_domains = toset(flatten([var.domain_name, [for sub in var.subdomains : "${sub}.${var.domain_name}"]]))
}

data "aws_route53_zone" "zone" {
  name = "${var.domain_name}."
}

resource "aws_acm_certificate" "this" {
  for_each = local.target_domains

  domain_name       = each.key
  validation_method = "DNS"

  tags = var.common_tags

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "validation" {
  for_each = aws_acm_certificate.this

  zone_id = data.aws_route53_zone.zone.zone_id
  name    = tolist(each.value.domain_validation_options)[0].resource_record_name
  type    = tolist(each.value.domain_validation_options)[0].resource_record_type
  ttl = var.dns_ttl

  records = [
    tolist(each.value.domain_validation_options)[0].resource_record_value
  ]

  allow_overwrite = var.allow_validation_record_overwrites
}

resource "aws_acm_certificate_validation" "this" {
  for_each = aws_acm_certificate.this

  certificate_arn         = each.value.arn
  validation_record_fqdns = [
    for record in aws_route53_record.validation : record 
    if tolist(each.value.domain_validation_options)[0].resource_record_name == record.name][*].fqdn
}
