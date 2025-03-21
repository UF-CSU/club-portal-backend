output "bucket_name" {
  description = "Full name of the S3 bucket created."
  value       = aws_s3_bucket.this.bucket
}
