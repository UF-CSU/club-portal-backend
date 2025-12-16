#!/bin/sh

set -e

db_uri="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$BACKUPS_POSTGRES_HOST:$BACKUPS_POSTGRES_PORT/$POSTGRES_NAME"
backup_dir="/var/backups"
backup_file_name=""

# bucket_name="$BACKUPS_BUCKET_NAME"

# Determine backup file name
if [ "$#" -gt 0 ]; then
    # User input a name
    backup_file_name="$@"

    # Make sure new name doesn't have slashes or ends in .sql
    if [[ "$backup_file_name" == *"/"* || "$backup_file_name" == *".sql" ]]; then
        echo "Error: Only provide backup file name without extension or directory."
        echo "Example: $0 example_backup"
        exit 1 
    fi
else
    # User did not input a name, use auto generated name
    backup_file_name="AUTO_backup_${POSTGRES_NAME}_$(date +%Y-%m-%d_%H-%M-%S)"
fi

backup_file="${backup_dir}/${backup_file_name}.sql.gz"
echo "Creating new backup $backup_file..."

# Ensure backup file doesn't already exist
if [ -f "$backup_file" ]; then
    echo "Error: Backup file $backup_file already exists."
    exit 1
fi

# Create and compress postgres backup file
pg_dump --dbname="$db_uri" | gzip > "$backup_file"

echo "Successfully created new backup $backup_file"

# TODO: Add new s3 bucket for backups
# echo "Uploading to S3..."
# aws s3 cp "$backup_file" "s3://$bucket_name"
