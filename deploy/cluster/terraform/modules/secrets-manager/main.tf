####################################
## Secrets Manager Module
####################################
# Resources: 
#  - https://github.com/external-secrets/external-secrets/blob/main/docs/provider/aws-secrets-manager.md
#  - https://overcast.blog/how-to-use-the-secrets-store-csi-driver-to-mount-secrets-to-kubernetes-pods-e0e61b481d79

data "template_file" "sm_allow_access_policy" {
  template = file("${path.module}/templates/sm-access-policy.json.tpl")

  vars = {
    oidc_provider_arn = var.oidc_provider_arn
  }
}

resource "aws_secretsmanager_secret" "this" {
  for_each = var.secrets

  name                           = each.key
  recovery_window_in_days        = var.secret_recovery_window_days
  force_overwrite_replica_secret = true

  tags = var.common_tags

  lifecycle {
    create_before_destroy = false
  }
}

resource "aws_secretsmanager_secret_policy" "this" {
  for_each = aws_secretsmanager_secret.this

  secret_arn = each.value.arn
  policy     = data.template_file.sm_allow_access_policy.rendered
}

resource "aws_secretsmanager_secret_version" "this" {
  for_each = var.secrets

  secret_id     = aws_secretsmanager_secret.this[each.key].id
  secret_string = each.value
}
