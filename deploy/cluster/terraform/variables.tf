#############################
## MARK: General
#############################
variable "prefix" {
  default = "clubs"
}

variable "project" {
  default = "Club Manager"
}

variable "contact" {
  default = "web@ikehunter.dev"
}

#############################
## MARK: Database 
#############################
variable "cluster_db_name" {
  description = "Postgres database name."
  type        = string
  default     = "clusterdb"
}
variable "cluster_db_username" {
  description = "Postgres database auth username."
  type        = string
  sensitive   = true
}

#############################
## MARK: Club Manager Env
#############################

variable "clubs_admin_email" {
  description = "Email used to create initial super user."
  type        = string
  sensitive   = true
}

variable "clubs_admin_password" {
  description = "Password for initial super user."
  type        = string
  sensitive   = true
}

variable "clubs_namespace" {
  description = "K8s namespace for club manager resources."
  type        = string
  default     = "main"
}

#############################
## Cluster & Network
#############################

variable "domain_name" {
  description = "Custom domain name to assign to cluster for public access. Must already exist in AWS Route53."
  type        = string
}
