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
## Bucket Config
###############################################

variable "routing_rules" {
  description = "Route url requests to specific directories. Ex: url_prefix: '/', directory_path: 'static/'."
  type = list(object({
    url_path_prefix = string
    directory_path  = string
  }))

  default = []
}
