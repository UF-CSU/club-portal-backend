# Bucket for static public files (images, css, js, etc)
module "clubs_static_bucket" {
  source        = "./modules/public-bucket"
  resource_name = "clubmanager-public"
  prefix        = local.prefix
  common_tags   = local.common_tags
}
