output "iam_role" {
  description = "Info for the aws_iam_role resource."
  value = aws_iam_role.this
}

output "service_account" {
  description = "Return service account inputs for reuse."
  value = {
    name      = var.service_account_name
    namespace = var.service_account_namespace
  }
}
