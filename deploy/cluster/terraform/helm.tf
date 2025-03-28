#
# Reference: https://medium.com/@sahibgasimov/terraform-mastery-deploying-eks-cluster-custom-module-with-alb-ingress-controller-and-external-dns-9fe328de9f95
#

######################################
## AWS ALB Controller
######################################
resource "helm_release" "aws_load_balancer_controller" {
  name = "aws-load-balancer-controller"

  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  namespace  = module.alb_controller_sa.service_account.namespace

  set {
    name  = "clusterName"
    value = local.cluster_name
  }

  set {
    name  = "serviceAccount.name"
    value = module.alb_controller_sa.service_account.name
  }

  set {
    name  = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    value = module.alb_controller_sa.iam_role.arn
  }

  set {
    name  = "vpcId"
    value = local.vpc_id
  }

  set {
    name  = "replicaCount"
    value = 1
  }

  depends_on = [
    module.cluster,
    module.alb_controller_sa,
  ]
}


