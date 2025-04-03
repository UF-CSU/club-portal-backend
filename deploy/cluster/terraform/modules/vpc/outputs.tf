output "vpc_id" {
  description = "VPC resource id"
  value       = aws_vpc.this.id
}


output "private_subnets" {
  description = "List of private subnets that were created."
  value       = aws_subnet.private
}
