#!/bin/sh

set -e

db_uri="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$BACKUPS_POSTGRES_HOST:$BACKUPS_POSTGRES_PORT/$POSTGRES_NAME"
backup_dir="/var/backups"
backup_file_name=""
backup_type="auto" # Enum: auto | manual
s3_bucket_name="$BACKUPS_BUCKET_NAME"

# Determine backup file name
if [ "$#" -gt 0 ]; then
    # User input a name
    backup_file_name="$@"
    backup_type="manual"

    # Make sure new name doesn't have slashes or ends in .sql
    if [[ "$backup_file_name" == *"/"* || "$backup_file_name" == *".sql" ]]; then
        echo "Error: Only provide backup file name without extension or directory."
        echo "Example: $0 example_backup"
        exit 1 
    fi
else
    # User did not input a name, use auto generated name
    backup_file_name="auto_backup_${POSTGRES_NAME}_$(date +%Y-%m-%d_%H-%M-%S)"
fi

backup_file="${backup_file_name}.sql.gz"
backup_file_path="${backup_dir}/${backup_file}"
echo "Creating new backup $backup_file..."

# Ensure backup file doesn't already exist
if [ -f "$backup_file_path" ]; then
    echo "Error: Backup file $backup_file_path already exists."
    exit 1
fi

# Create and compress postgres backup file
pg_dump --dbname="$db_uri" | gzip > "$backup_file_path"

echo "Successfully created new backup $backup_file_path"


# ==================================
# Upload backup to S3
# ==================================

if [[ -z "$s3_bucket_name" ]]; then
    echo "No S3 bucket defined, skipping upload"
    exit 0
fi

# Set AWS credentials
export AWS_ACCESS_KEY_ID="$BACKUPS_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$BACKUPS_AWS_SECRET_ACCESS_KEY"

# Upload backup 
aws s3api put-object \
    --bucket "$s3_bucket_name" \
    --key "$backup_file" \
    --body "$backup_file_path" \
    --tagging "BackupType=$backup_type" > /dev/null

echo "Successfully uploaded $backup_type backup to S3 bucket $s3_bucket_name"

