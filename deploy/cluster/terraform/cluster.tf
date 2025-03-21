locals {
  cluster_name      = "${local.prefix}-cluster"
  oidc_provider_url = module.cluster.oidc_provider_url
}

##############################################
## MARK: Main EKS Config
##############################################
module "cluster" {
  source        = "./modules/eks"
  prefix        = local.prefix
  resource_name = "cluster"
  common_tags   = local.common_tags

  cluster_name = local.cluster_name
  scaling_config = {
    desired_size = 2
    max_size     = 2
    min_size     = 1
  }

  vpc_id = module.network.vpc_id
  ingress_access = [
    {
      description = "Allow traffic to proxy",
      port        = 8080,
      cidr_blocks = ["0.0.0.0/0"]
    }
  ]
  egress_access = [
    {
      description = "Allow responses to http (port 80)",
      port        = 80,
      cidr_blocks = ["0.0.0.0/0"]
    },
    {
      description = "Allow responses to https (port 443)",
      port        = 443,
      cidr_blocks = ["0.0.0.0/0"]
    },
    {
      description = "Allow requests from the cluster to the database"
      port        = 5432
      cidr_blocks = local.private_subnet_cidr_blocks
    }
  ]
  private_subnet_ids = local.private_subnet_ids
}

##############################################
## MARK: Service Accounts
##############################################

module "ebs_csi_sa" {
  source        = "./modules/eks-service-account"
  prefix        = local.prefix
  common_tags   = local.common_tags
  resource_name = "ebs-csi"

  cluster_name              = local.cluster_name
  service_account_namespace = "kube-system"
  service_account_name      = "ebs-csi-controller-sa"

  oidc_provider_url  = local.oidc_provider_url
  policy_description = "Allow EKS cluster to access EBS resources."
  policy_file        = file("./templates/eks/eks-ebs-service-role-policy.json")

  depends_on = [module.cluster]
}

module "secrets_manager_sa" {
  source        = "./modules/eks-service-account"
  prefix        = local.prefix
  common_tags   = local.common_tags
  resource_name = "secrets-manager"

  cluster_name              = local.cluster_name
  service_account_namespace = "main"
  service_account_name      = "secretsmanager-sa"

  oidc_provider_url  = local.oidc_provider_url
  policy_description = "Allow EKS cluster to access secrets manager."
  policy_file        = file("./templates/eks/eks-access-secrets-manager-policy.json")

  depends_on = [module.cluster]
}

module "vpc_cni_sa" {
  source        = "./modules/eks-service-account"
  prefix        = local.prefix
  common_tags   = local.common_tags
  resource_name = "vpc-cni"

  cluster_name              = local.cluster_name
  service_account_namespace = "kube-system"
  service_account_name      = "aws-node"

  oidc_provider_url  = local.oidc_provider_url
  policy_description = "Allow EKS cluster to access VPC CNI addon resources."
  policy_file        = file("./templates/eks/eks-vpccni-service-role-policy.json")

  depends_on = [module.cluster]
}

module "external_dns_sa" {
  source        = "./modules/eks-service-account"
  prefix        = local.prefix
  common_tags   = local.common_tags
  resource_name = "external-dns"

  cluster_name              = local.cluster_name
  service_account_namespace = "kube-system"
  service_account_name      = "external-dns"

  oidc_provider_url  = local.oidc_provider_url
  policy_description = "Allow EKS cluster to manage DNS resources with Route53."
  policy_file        = file("./templates/eks/eks-manage-dns-policy.json")

  depends_on = [module.cluster]
}

module "alb_controller_sa" {
  source        = "./modules/eks-service-account"
  prefix        = local.prefix
  common_tags   = local.common_tags
  resource_name = "alb-controller"

  cluster_name              = local.cluster_name
  service_account_namespace = "kube-system"
  service_account_name      = "aws-load-balancer-controller"

  oidc_provider_url  = local.oidc_provider_url
  policy_description = "Allow EKS cluster to manage application load balancer resources."
  policy_file        = file("./templates/eks/eks-manage-alb-policy.json")

  depends_on = [module.cluster]
}


##############################################
## MARK: EKS Addons
##############################################

resource "aws_eks_addon" "eks_ebs_addon" {
  addon_name               = "aws-ebs-csi-driver"
  cluster_name             = local.cluster_name
  service_account_role_arn = module.ebs_csi_sa.iam_role.arn
}

resource "aws_eks_addon" "eks_identity_agent_addon" {
  addon_name               = "eks-pod-identity-agent"
  cluster_name             = local.cluster_name
  service_account_role_arn = module.secrets_manager_sa.iam_role.arn
}

resource "aws_eks_addon" "eks_cni_addon" {
  addon_name               = "vpc-cni"
  cluster_name             = local.cluster_name
  service_account_role_arn = module.vpc_cni_sa.iam_role.arn
}


##############################################
## MARK: Cluster Initialization
##############################################

data "template_file" "k8s_init_config" {
  template = file("./templates/eks/eks-k8s-init-script.sh.tpl")

  vars = {
    cluster_region = data.aws_region.current.name
    cluster_name   = local.cluster_name

    cluster_main_namespace = var.clubs_namespace

    cluster_secretsmanager_namespace   = module.secrets_manager_sa.service_account.namespace
    cluster_secretsmanager_sa_name     = module.secrets_manager_sa.service_account.name
    cluster_secretsmanager_sa_role_arn = module.secrets_manager_sa.iam_role.arn

    external_dns_namespace   = module.external_dns_sa.service_account.namespace
    external_dns_sa_name     = module.external_dns_sa.service_account.name
    external_dns_sa_role_arn = module.external_dns_sa.iam_role.arn

    alb_controller_namespace   = module.alb_controller_sa.service_account.namespace
    alb_controller_sa_name     = module.alb_controller_sa.service_account.name
    alb_controller_sa_role_arn = module.alb_controller_sa.iam_role.arn


  }
}

# Manually run init script
# This is done to pass some context from here to k8s
resource "null_resource" "update_kubeconfig" {
  provisioner "local-exec" {
    command = data.template_file.k8s_init_config.rendered
  }

  depends_on = [
    module.cluster,
    module.ebs_csi_sa,
    module.secrets_manager_sa,
    module.external_dns_sa,
    module.vpc_cni_sa
  ]

  triggers = {
    script = data.template_file.k8s_init_config.rendered
  }
}
