###############################################
## General 
###############################################
variable "prefix" {
  description = "Prefix used to differentiate between environments."
  default     = "default"
}

variable "common_tags" {
  description = "Tags to give all associated resources."
  type        = map(string)

  default = {}
}

##############################################
## VPC Vars 
##############################################

variable "cidr_block_prefix" {
  description = "First two parts of the vpc cidr block. "
  type        = string
  default     = "10.0"
}

variable "enable_dns_hostnames" {
  description = "Should be true to enable DNS hostnames in the VPC"
  type        = bool
  default     = true
}

variable "enable_dns_support" {
  description = "Should be true to enable DNS support in the VPC"
  type        = bool
  default     = true
}

variable "availability_zone_count" {
  description = "Number of availability zones to use. Min: 2, Max: 9"
  type        = number
  default     = 2
}

##############################################
## Resource Tags
##############################################
variable "public_subnet_tags" {
  description = "Extra tags to add to public subnets."
  type        = map(string)
  default     = {}
}

variable "private_subnet_tags" {
  description = "Extra tags to add to private subnets."
  type        = map(string)
  default     = {}
}
