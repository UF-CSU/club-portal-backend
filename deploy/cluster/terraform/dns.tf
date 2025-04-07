locals {
  base_url = "https://${var.domain_name}"
}

# Creates certificate for domain name and each sub domain
module "dns_certificates" {
  source      = "./modules/acm-certificates"
  prefix      = local.prefix
  common_tags = local.common_tags

  domain_name = var.domain_name
  subdomains  = []
}
