########################################
## Virtual Private Cloud 
########################################
# Inspired by: https://github.com/terraform-aws-modules/terraform-aws-vpc/tree/master

data "aws_availability_zones" "available" {}
data "aws_region" "current" {}

locals {
  availability_zones = slice(data.aws_availability_zones.available.names, 0, var.availability_zone_count)
  
}


resource "aws_vpc" "this" {
  cidr_block           = "${var.cidr_block_prefix}.0.0/16"
  enable_dns_support   = var.enable_dns_support
  enable_dns_hostnames = var.enable_dns_hostnames

  tags = merge(
    var.common_tags,
    tomap({ Name = "${var.prefix}-vpc" })
  )
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(
    var.common_tags,
    tomap({ Name = "${var.prefix}-gateway" })
  )
}

