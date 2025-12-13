#!/bin/sh

set -e

db_uri="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_NAME"
backup_dir="/var/backups"
backup_file_name="$@"

# Make sure user provided correct input for backup file name
if [ "$#" -eq 0 ]; then
    # User provided no input
    echo "Error: No backup file provided."
    echo "Usage: $0 <backup_file_name>"
    echo "Example: $0 backup_testdb_2025-10-20_14-16-42"
    exit 1
elif [[ "$backup_file_name" == *"/"* ]]; then
    # User provided directory path
    echo "Error: Only provide backup file name, not directory."
    echo "Example: $0 backup_testdb_2025-10-20_14-16-42"
    exit 1
elif [[ "$backup_file_name" == *".sql.gz" ]]; then
    # User provided file extension
    echo "Error: Do not put extension in file name."
    echo "Example: $0 backup_testdb_2025-10-20_14-16-42"
    exit 1
fi

backup_file="$backup_dir/$backup_file_name.sql.gz"
echo "Restoring backup file $backup_file for $db_uri..."

# Ensure backup file exists
if [ ! -f "$backup_file" ]; then
    echo "Error: Backup file $backup_file_name does not exist in backups directory."
    exit 1
fi

# Un-compress file and apply the postgres dump
gunzip -c "$backup_file" | psql --dbname="$db_uri"

echo "Successfully restored backup $backup_file"
