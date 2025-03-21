#############################################
## Public S3 Bucket
#############################################

resource "aws_s3_bucket" "this" {
  bucket_prefix = "${var.prefix}-${var.resource_name}"
  force_destroy = true

  tags = merge(var.common_tags, tomap({ Type = "public" }))
}

resource "aws_s3_bucket_ownership_controls" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_acl" "this" {
  bucket = aws_s3_bucket.this.id
  acl    = "public-read"

  depends_on = [
    aws_s3_bucket_ownership_controls.this,
    aws_s3_bucket_public_access_block.this,
  ]
}

data "template_file" "this" {
  template = file("${path.module}/templates/s3-allow-public-access-policy.json.tpl")

  vars = {
    bucket_name = aws_s3_bucket.this.bucket
  }
}

resource "aws_s3_bucket_policy" "this" {
  bucket = aws_s3_bucket.this.id
  policy = data.template_file.this.rendered

  depends_on = [aws_s3_bucket_acl.this]

}

resource "aws_s3_bucket_website_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  depends_on = [aws_s3_bucket_acl.this]

  index_document {
    suffix = "index.html"
  }

  dynamic "routing_rule" {
    for_each = var.routing_rules

    content {
      condition {
        key_prefix_equals = each.value.url_path_prefix
      }
      redirect {
        replace_key_prefix_with = each.value.directory_path
      }
    }
  }
}
