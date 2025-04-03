###############################################
## General 
###############################################

variable "prefix" {
  description = "Prefix used to differentiate between environments."
  default     = "default"
}

variable "resource_name" {
  description = "Identify the bucket created, and related resources."
}

variable "common_tags" {
  description = "Tags to give all associated resources."
  type        = map(string)

  default = {}
}


###############################################
## Cluster Config 
###############################################
variable "cluster_name" {
  description = "Name of the cluster. This is can be provided separately to prevent circular dependencies."
  default     = ""

}

variable "scaling_config" {
  description = "Manage how EKS will scale nodes up or down."
  type = object({
    desired_size = number
    max_size     = number
    min_size     = number
  })
}

variable "max_unavailable" {
  description = "Desired max number of unavailable worker nodes during node group update."
  type        = number
  default     = 1
}

variable "node_instance_types" {
  description = "List of instance types associated with the EKS Node Group. Terraform will only perform drift detection if a configuration value is provided."
  type        = list(string)
  default     = ["t3.medium"]
}

###############################################
## VPC Connection
###############################################

variable "vpc_id" {
  description = "VPC id to use in the cluster's security group."
  type        = string
}

variable "ingress_access" {
  description = "Allow access to the cluster from the outside. Ports should match on the from/to sides, this makes it easier to maintain."
  type = list(object({
    description = string
    port        = number
    cidr_blocks = list(string)
  }))
}

variable "egress_access" {
  description = "Allow access from the cluster to another resource in the network. Ports should match on the from/to sides, this makes it easier to maintain."
  type = list(object({
    description = string
    port        = number
    cidr_blocks = list(string)
  }))
}

variable "private_subnet_ids" {
  description = "List of ids for private subnets the cluster will use for networking tasks."
  type        = list(string)
}
