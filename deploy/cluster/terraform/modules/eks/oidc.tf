################################################
## OpenID Connect Config
################################################

data "tls_certificate" "this" {
  url = aws_eks_cluster.this.identity.0.oidc.0.issuer
}

resource "aws_iam_openid_connect_provider" "this" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.this.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.this.identity.0.oidc.0.issuer

  tags = var.common_tags
}

resource "aws_eks_identity_provider_config" "this_oidc_provider" {
  cluster_name = aws_eks_cluster.this.name

  oidc {
    identity_provider_config_name = "cluster_oidc"
    client_id                     = aws_iam_openid_connect_provider.this.id
    issuer_url                    = "https://oidc.eks.${data.aws_region.current.name}.amazonaws.com"
  }
}
