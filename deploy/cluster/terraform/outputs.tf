output "cluster_name" {
  value = module.cluster.name
}

output "connect_command" {
  value = format("aws eks update-kubeconfig --region %s --name %s", data.aws_region.current.name, module.cluster.name)
}
