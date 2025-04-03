###################################
## General 
###################################
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
  description = "Used to label resources created by this module."
}

###################################
## Authentication 
###################################
# variable "db_identifier" {
#   description = "Unique name to give database."
#   default     = null
# }
variable "db_name" {
  description = "Name to give RDS database."
}
variable "db_username" {
  description = "Authentication username for RDS database."
}
variable "db_password" {
  description = "Authentication password for RDS database."
}

###################################
## Storage Config 
###################################
variable "allocated_storage" {
  description = "Amount of storage in Gb to reserve for database."
  default     = 20
}
variable "storage_type" {
  description = "Defines underlying storage, IOPS, and throughput specs."
  default     = "gp2"
}
variable "instance_class" {
  default = "db.t3.micro"
}
variable "engine_version" {
  description = "Postgres version."
  default     = "12.16"
}

###################################
## Network and Security 
###################################
variable "vpc_id" {
  description = "VPC identifier for security groups, RDS, etc."
}
variable "ingress_security_groups" {
  description = "Security group ids for resources allowed to access database."
  default     = []
}
variable "subnet_ids" {
  description = "Private subnet ids used to connect to VPC."
  default     = []
}
variable "ingress_cidr_blocks" {
  description = "CIDR blocks allowed to access database."
  default     = []
}

###################################
## Backups and Safety 
###################################
variable "enable_blue_green_update" {
  description = "Whether RDS Blue/Green updates are enabled. Creates staging database for smoother updates. Default: false."
  type        = bool
  default     = false
}
variable "enable_final_snapshot" {
  description = "Whether a final snapshot should be taken. Default: false."
  type        = bool
  default     = false
}
variable "create_from_snapshot" {
  description = "Create instance from a certain snapshot. This can be used to revert to a backup."
  type        = string
  default     = ""
}
