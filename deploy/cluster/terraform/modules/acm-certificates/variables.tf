################################
## General
################################
variable "prefix" {
  description = "Prefix used to differentiate between environments."
  default     = "default"
}
variable "common_tags" {
  description = "Tags to give all associated resources."
  type        = map(string)

  default = {}
}

################################
## Certificate Variables
################################
variable "domain_name" {
  description = "The FQDN attached to the certificate. Include subdomains, exclude paths."
  type        = string
  default     = null
}
variable "subdomains" {
  description = "List of subdomain values to register a certificate for (exclude domain name)."
  type        = list(string)
  default     = []

}
variable "dns_ttl" {
  description = "Value for aws_route53_record.ttl."
  default     = "60"
}
variable "allow_validation_record_overwrites" {
  description = "Whether to allow overwrite of Route53 records"
  default     = true
}

