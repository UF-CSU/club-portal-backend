############################################
### AWS Relational Database (RDS) Module ###
############################################
# Docs: https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_instance

locals {
  resource_name       = "${var.prefix}-${var.resource_name}"
  snapshot_identifier = var.create_from_snapshot != "" ? var.create_from_snapshot : null
}

resource "aws_db_instance" "this" {
  identifier_prefix    = local.resource_name
  db_name              = var.db_name
  allocated_storage    = var.allocated_storage
  storage_type         = var.storage_type
  engine               = "postgres"
  engine_version       = var.engine_version
  instance_class       = var.instance_class
  db_subnet_group_name = aws_db_subnet_group.this.name

  username = var.db_username
  password = var.db_password

  backup_retention_period   = 5 # days
  skip_final_snapshot       = var.enable_final_snapshot
  final_snapshot_identifier = var.enable_final_snapshot ? "${local.resource_name}-snapshot-${replace(timestamp(), ":", "-")}" : null
  apply_immediately         = true
  snapshot_identifier       = local.snapshot_identifier

  multi_az               = false
  vpc_security_group_ids = [aws_security_group.this.id]

  blue_green_update {
    enabled = var.enable_blue_green_update
  }

  lifecycle {
    create_before_destroy = true
    ignore_changes = [
      final_snapshot_identifier,
    ]
  }

  tags = merge(
    var.common_tags,
    tomap({ Name = local.resource_name })
  )
}
