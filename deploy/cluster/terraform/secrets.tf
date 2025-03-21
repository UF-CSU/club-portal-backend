#####################################
## Secrets Manager Modules
#####################################

module "cluster_secrets" {
  source            = "./modules/secrets-manager"
  prefix            = local.prefix
  common_tags       = local.common_tags
  oidc_provider_arn = local.oidc_provider_url

  depends_on = [module.cluster_database]

  secrets = {
    cluster_db_auth = jsonencode({
      address  = module.cluster_database.address
      name     = local.cluster_db_name
      username = local.cluster_db_username
      password = local.cluster_db_password
    })

    clubs_static_bucket = jsonencode({
      s3_storage_bucket_name   = module.clubs_static_bucket.bucket_name
      s3_storage_bucket_region = data.aws_region.current.name
    })

    clubs_admin_auth = jsonencode({
      admin_email    = var.clubs_admin_email
      admin_password = var.clubs_admin_password
    })

    clubs_security = jsonencode({
      allowed_hosts        = "*"
      base_url             = local.base_url
      csrf_trusted_origins = local.base_url
    })
  }
}


