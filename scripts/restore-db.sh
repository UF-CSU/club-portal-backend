#!/bin/bash

set -e

# Utils
function show-help {
  cat <<EOH
Usage: $0 <backup_name> [options]

Restore a local backup from the 'backups/' directory.

Options:
  -h,--help     Show this help message
  -l,--list     Only list available backups, without restoring any

Examples:
  $0 backup_testdb_2025-10-20_14-16-42
  $0 backup_testdb_2025-10-20_14-16-42.sql.gz
  $0 --list
EOH
}

function log {
  if [[ "$1" == "green" ]]; then
    printf "\033[32m$2\033[0m\n"
  elif [[ "$1" == "red" ]]; then
    printf "\033[31m$2\033[0m\n"
  elif [[ "$1" == "check" ]]; then
    printf "\033[31m\xE2\x9C\x93\033[0m $2\n"
  elif [[ "$1" == "circle" ]]; then
    printf "\033[37m\xE2\x8A\x99\033[0m $2\n"
  else
    echo -e "$@"
  fi
}

# Vars
db_uri="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$BACKUPS_POSTGRES_HOST:$BACKUPS_POSTGRES_PORT/$POSTGRES_NAME"
backup_dir="/var/backups"
backup_file_name=""
list_mode=0

# Process CLI Arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  
  case "$key" in
    -h | --help)
      show-help
      exit 0
      ;;
    -l | --list)
      list_mode=1
      shift
      ;;
    *)
      # Unknown Option
      if [[ -n "$backup_file_name" ]]; then
        log red "Unknown argument: $1"
        exit 1
      else
        backup_file_name="$1"
        shift
      fi
      ;;
  esac
done

# Handle list option
if [[ "$list_mode" == "1" ]]; then
  # echo "listing backups:"
  # ls $backup_dir
  # read -r -a backups_list <<< $(ls "$backup_dir")
  backups_list=($(ls "$backup_dir"))
  backups_count="${#backups_list[@]}"
  
  if [[ "$backups_count" -eq 0 ]]; then
    log "Backups directory is empty."
  elif [[ "$backups_count" -eq 1 ]]; then
    log "Found 1 backup:"
  else
    log "Found $backups_count backups:"
  fi
  
  for backup in "${backups_list[@]}"; do
    log " - $backup"
  done
  
  exit 0
fi


# Make sure user provided correct input for backup file name
if [ -z "$backup_file_name" ]; then
  # User provided no input
  log red "Error: No backup file provided.\n"
  show-help
  exit 2
elif [[ "$backup_file_name" == *"/"* ]]; then
  # User provided directory path
  log red "Error: Only provide backup file name, not directory.\n"
  exit 3
elif [[ "$backup_file_name" != *".sql.gz" ]]; then
  # User didn't provided file extension
  backup_file_name="${backup_file_name}.sql.gz"
fi

backup_file="$backup_dir/$backup_file_name"
timestamp="$(date +%Y-%m-%d_%H-%M-%S)"
new_backup_file_name="pre_restore_${POSTGRES_NAME}_${timestamp}"
new_backup_file="${backup_dir}/${new_backup_file_name}.sql.gz"

# Ensure backup file exists
if [ ! -f "$backup_file" ]; then
  log red "Error: Backup file $backup_file_name does not exist in backups directory.\n"
  exit 4
fi

log circle "Checking for db connection..."
export PGHOST="$BACKUPS_POSTGRES_HOST"
export PGPORT="$BACKUPS_POSTGRES_PORT"
export PGUSER="$POSTGRES_USER"
export PGPASSWORD="$POSTGRES_PASSWORD"
export PGNAME="$POSTGRES_NAME"

until pg_isready; do
  echo "$POSTGRES_NAME is unavailable, trying again..."
  sleep 1
done

# Get user confirmation

log $(cat <<EOC
Will perform the following:
  - Backup current state to '$new_backup_file_name'
  - Restore backup '$backup_file_name' to database '$PGNAME'

Type "yes" to proceed:
EOC
)

read ack

if [[ "$ack" != "yes" ]]; then
  log red "\nCanceling..."
  exit 5
else
  log green "\nProceeding...\n"
fi

# Create new backup with the current data
pg_dump --dbname="$db_uri" | gzip > "$new_backup_file"
log check "Created backup of current data: $new_backup_file_name"

# Drop and recreate database so the backup data doesn't interfere
dropdb "$POSTGRES_NAME"
createdb "$POSTGRES_NAME"

log check "Dropped and recreated database '$POSTGRES_NAME'"

# Un-compress file and apply the postgres dump
log circle "Restoring backup file $backup_file for $db_uri..."
gunzip -c "$backup_file" | psql --dbname="$db_uri"
log check "\\rRestored backup file $backup_file for $db_uri"

log green "\nSuccessfully restored backup $backup_file"
