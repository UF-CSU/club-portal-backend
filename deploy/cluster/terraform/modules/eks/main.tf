#######################################################
## Elastic Kubernetes Service (EKS)
#######################################################
# Node Group docs: https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group#argument-reference

locals {
  common_name = "${var.prefix}-${var.resource_name}"
}
data "aws_region" "current" {}

# MARK: Cluster Security
###########################
resource "aws_iam_policy" "this_role_policy" {
  name        = "${local.common_name}-role-policy"
  path        = "/"
  description = "Allow EKS to manage cluster."
  policy      = file("${path.module}/templates/eks-cluster-role-policy.json")
}

resource "aws_iam_role" "this_role" {
  name               = "${local.common_name}-role"
  assume_role_policy = file("${path.module}/templates/eks-assume-role-policy.json")

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "this_role" {
  role       = aws_iam_role.this_role.name
  policy_arn = aws_iam_policy.this_role_policy.arn
}

resource "aws_security_group" "this" {
  description = "Allow eks to access ALB"
  name        = "${local.common_name}-access"
  vpc_id      = var.vpc_id

  # TODO: Refactor to use preferred aws_vpc_security_group_ingress_rule resource
  dynamic "ingress" {
    for_each = var.ingress_access

    content {
      protocol    = "tcp"
      description = ingress.value.description
      from_port   = ingress.value.port
      to_port     = ingress.value.port
      cidr_blocks = ingress.value.cidr_blocks
    }
  }

  # TODO: Refactor to use preferred aws_vpc_security_group_egress_rule resource
  dynamic "egress" {
    for_each = var.egress_access

    content {
      protocol    = "tcp"
      description = egress.value.description
      from_port   = egress.value.port
      to_port     = egress.value.port
      cidr_blocks = egress.value.cidr_blocks
    }
  }

  tags = var.common_tags
}

# MARK: EKS Cluster
###########################
resource "aws_eks_cluster" "this" {
  name     = coalesce(var.cluster_name, local.common_name) # Use manual value if provided, or default to derrived name
  role_arn = aws_iam_role.this_role.arn

  vpc_config {
    subnet_ids              = var.private_subnet_ids
    endpoint_private_access = true
    security_group_ids      = [aws_security_group.this.id]
  }

  tags       = var.common_tags
  depends_on = [aws_iam_role_policy_attachment.this_role]
}

# MARK: Node Group Security
###########################
resource "aws_iam_policy" "this_node_group_role_policy" {
  name        = "${local.common_name}-node-group-role-policy"
  path        = "/"
  description = "Allow EKS to manage cluster."
  policy      = file("${path.module}/templates/eks-node-group-role-policy.json")
}

resource "aws_iam_role" "this_node_group_role" {
  name               = "${local.common_name}-node-group-role"
  assume_role_policy = file("${path.module}/templates/eks-assume-role-policy.json")

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "this_node_group_role" {
  role       = aws_iam_role.this_node_group_role.name
  policy_arn = aws_iam_policy.this_node_group_role_policy.arn
}

# MARK: EKS Node Group
###########################
resource "aws_eks_node_group" "this_node_group" {
  cluster_name           = aws_eks_cluster.this.name
  node_group_name_prefix = "${local.common_name}-nodes"
  node_role_arn          = aws_iam_role.this_node_group_role.arn
  subnet_ids             = var.private_subnet_ids
  instance_types         = var.node_instance_types

  scaling_config {
    desired_size = var.scaling_config.desired_size
    max_size     = var.scaling_config.max_size
    min_size     = var.scaling_config.min_size
  }

  update_config {
    max_unavailable = var.max_unavailable
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [aws_iam_role_policy_attachment.this_node_group_role]
  tags       = var.common_tags
}
