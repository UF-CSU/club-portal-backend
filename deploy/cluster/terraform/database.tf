resource "random_password" "database_passwords" {
  count   = 1
  length  = 25
  special = false
}

locals {
  cluster_db_name     = var.cluster_db_name
  cluster_db_username = var.cluster_db_username
  cluster_db_password = random_password.database_passwords[0].result
}


module "cluster_database" {
  source        = "./modules/rds"
  prefix        = local.prefix
  common_tags   = local.common_tags
  resource_name = "cluster-db"

  db_name                  = local.cluster_db_name
  db_username              = local.cluster_db_username
  db_password              = local.cluster_db_password
  engine_version           = "12.19"
  enable_blue_green_update = true
  enable_final_snapshot    = true
  create_from_snapshot     = ""

  vpc_id                  = module.network.vpc_id
  subnet_ids              = local.private_subnet_ids
  ingress_cidr_blocks     = local.private_subnet_cidr_blocks
  ingress_security_groups = [module.cluster.security_group.id]
}
