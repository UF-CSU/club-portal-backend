#!/bin/sh

set -e

db_uri="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$BACKUPS_POSTGRES_HOST:$BACKUPS_POSTGRES_PORT/$POSTGRES_NAME"
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
    exit 2
elif [[ "$backup_file_name" == *".sql.gz" ]]; then
    # User provided file extension
    echo "Error: Do not put extension in file name."
    echo "Example: $0 backup_testdb_2025-10-20_14-16-42"
    exit 3
fi

backup_file="$backup_dir/$backup_file_name.sql.gz"


# Ensure backup file exists
if [ ! -f "$backup_file" ]; then
    echo "Error: Backup file $backup_file_name does not exist in backups directory."
    exit 4
fi

# Create new backup with the current data
timestamp="$(date +%Y-%m-%d_%H-%M-%S)"
new_backup_file_name="pre_restore_${POSTGRES_NAME}_${timestamp}"
new_backup_file="${backup_dir}/${new_backup_file_name}.sql.gz"

pg_dump --dbname="$db_uri" | gzip > "$new_backup_file"
echo "Created backup of current data: $new_backup_file_name"


# Drop and recreate database so the backup data doesn't interfere
export PGHOST="$BACKUPS_POSTGRES_HOST"
export PGPORT="$BACKUPS_POSTGRES_PORT"
export PGUSER="$POSTGRES_USER"
export PGPASSWORD="$POSTGRES_PASSWORD"

dropdb "$POSTGRES_NAME"
createdb "$POSTGRES_NAME"


# Un-compress file and apply the postgres dump
echo "Restoring backup file $backup_file for $db_uri..."s
gunzip -c "$backup_file" | psql --dbname="$db_uri"

echo "Successfully restored backup $backup_file"
