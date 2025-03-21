output "security_group" {
  description = "Security group created for the cluster, manages inbound/outbound access."
  value       = aws_security_group.this
}

output "oidc_provider_url" {
  description = "Url used to look up aws_iam_openid_connect_provider resource."
  value       = aws_iam_openid_connect_provider.this.url
}

output "id" {
  description = "Resource aws_eks_cluster id."
  value       = aws_eks_cluster.this.id
}

output "name" {
  description = "Identifier for the created EKS cluster."
  value       = aws_eks_cluster.this.name
}

output "endpoint" {
  description = "Cluster api endpoint used with helm."
  value       = aws_eks_cluster.this.endpoint
}

output "ca_certificate" {
  description = "Certificate used with helm."
  value       = base64decode(aws_eks_cluster.this.certificate_authority[0].data)
}
