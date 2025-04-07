###########
# General #
###########
variable "prefix" {
  description = "Prefix used to differentiate between environments."
  default     = "default"
}
variable "common_tags" {
  description = "Tags to give all associated resources."
  type        = map(string)

  default = {}
}

#############################
# Secrets Manager Resources #
#############################

variable "secrets" {
  description = "List of secrets to create in Secrets Manager."
  type        = map(string)
  default     = {}
}

variable "oidc_provider_arn" {
  description = "OpenID Connect provider arn to allow secret access to it."
  default     = ""
}
variable "secret_recovery_window_days" {
  description = "Value for aws_secretsmanager_secret.recovery_window_in_days"
  default     = 0
}
