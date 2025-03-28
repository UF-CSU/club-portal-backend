resource "aws_db_subnet_group" "this" {
  name       = local.resource_name
  subnet_ids = var.subnet_ids

  tags = merge(
    var.common_tags,
    tomap({ Name = local.resource_name })
  )
}

resource "aws_security_group" "this" {
  description = "Allow access to RDS database resource."
  name        = "${local.resource_name}-inbound-access"
  vpc_id      = var.vpc_id

  ingress {
    protocol  = "tcp"
    from_port = 5432
    to_port   = 5432

    cidr_blocks     = var.ingress_cidr_blocks
    security_groups = var.ingress_security_groups
  }

  tags = merge(
    var.common_tags,
    tomap({ Name = local.resource_name })
  )
}
