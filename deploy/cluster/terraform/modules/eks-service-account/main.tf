#######################################################
## EKS Addon & OpenID Connect Service Accounts
#######################################################


data "aws_iam_openid_connect_provider" "oidc_provider" {
  url = "https://${var.oidc_provider_url}"
}

# Service Role Config
#################################
data "template_file" "oidc_assume_role_policy" {
  template = file("${path.module}/templates/eks-oidc-assume-role-policy.json.tpl")

  vars = {
    oidc_uri                  = replace(data.aws_iam_openid_connect_provider.oidc_provider.url, "https://", "")
    oidc_provider_arn         = data.aws_iam_openid_connect_provider.oidc_provider.arn
    service_account_name      = var.service_account_name
    service_account_namespace = var.service_account_namespace
  }
}

resource "aws_iam_role" "this_oidc_service_role" {
  name               = "${var.prefix}-eks-oidc-${var.resource_name}-service-role"
  assume_role_policy = data.template_file.oidc_assume_role_policy.rendered

  tags = var.common_tags
}

# Service Account for Addon
#################################

resource "aws_iam_role" "this" {
  name               = "${var.prefix}-${var.resource_name}-service-role"
  assume_role_policy = data.template_file.oidc_assume_role_policy.rendered

  tags = var.common_tags
}

resource "aws_iam_policy" "this" {
  name        = "${var.prefix}-access-${var.resource_name}-policy"
  path        = "/"
  description = var.policy_description
  policy      = var.policy_file
}

resource "aws_iam_role_policy_attachment" "this" {
  role       = aws_iam_role.this.name
  policy_arn = aws_iam_policy.this.arn
}

resource "aws_eks_pod_identity_association" "this" {
  cluster_name    = var.cluster_name
  namespace       = var.service_account_namespace
  service_account = var.service_account_name
  role_arn        = aws_iam_role.this.arn
}

