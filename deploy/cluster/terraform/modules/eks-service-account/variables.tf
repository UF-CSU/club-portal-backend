##################################
## General
##################################
variable "prefix" {
  description = "Prefix used to differentiate between environments."
  default     = "default"
}
variable "common_tags" {
  description = "Tags to give all associated resources."
  type        = map(string)

  default = {}
}

variable "resource_name" {
  description = "Used for aws_iam_role name and aws_iam_policy name."
}

##################################
## OIDC and Roles 
##################################
variable "oidc_provider_url" {
  description = "Url used to look up aws_iam_openid_connect_provider resource."
}

variable "policy_description" {
  description = "What the policy does."
}

variable "policy_file" {
  description = "Content to use for the service role policy."
}


##################################
## EKS & K8s Connections
##################################
variable "cluster_name" {
  description = "Name of the aws_eks_cluster resource."
}

variable "service_account_namespace" {
  description = "K8s namespace the service account will be registered in."
  default     = "default"
}

variable "service_account_name" {
  description = "Name to give the k8s service account."
}


