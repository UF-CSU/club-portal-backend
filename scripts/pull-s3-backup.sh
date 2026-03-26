#!/bin/bash

set -e

# Utils
function show-help {
  cat <<EOH
Usage: $0 <backup_name> [options]

Pull a database backup from S3.

Options:
  -h,--help               Show this help message
  -l,--list               List backups available in S3 without pulling any
  -d,--destination PATH   Where to put the downloaded backup

Examples:
  $0 test-backup.sql.gz
  $0 test-backup.sql.gz --destination ./backups
  $0 --list
EOH
}

function log {
  if [[ "$1" == "green" ]]; then
    printf "\033[32m$2\033[0m\n"
  elif [[ "$1" == "red" ]]; then
    printf "\033[31m$2\033[0m\n"
  else
    echo -e "$@"
  fi
}

# Vars
script_dir=$(dirname $0)
list_mode=0
destination="./"
target_backup=""

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
    -d | --destination)
      destination="$2"
      shift
      shift
      ;;
    *)
      # Unknown Option
      if [[ -n "$target_backup" ]]; then
        log red "Unknown argument: $1"
        exit 1
      else
        target_backup="$1"
        shift
      fi
      ;;
  esac
done

# Setup AWS
if [[ -z "$BACKUPS_AWS_ACCESS_KEY_ID" || -z "$BACKUPS_AWS_SECRET_ACCESS_KEY" || -z "$BACKUPS_BUCKET_NAME" ]]; then
  log red "Couldn't find one of the following env vars: BACKUPS_AWS_ACCESS_KEY_ID, BACKUPS_AWS_SECRET_ACCESS_KEY, BACKUPS_BUCKET_NAME"
  exit 2
else
  bucket="$BACKUPS_BUCKET_NAME"
  
  # Authenticate with AWS
  export AWS_ACCESS_KEY_ID="$BACKUPS_AWS_ACCESS_KEY_ID"
  export AWS_SECRET_ACCESS_KEY="$BACKUPS_AWS_SECRET_ACCESS_KEY"
fi

# Process request
if [[ "$list_mode" == 0 && -n "$target_backup" ]]; then
  # Download mode, with backup name
  aws s3 cp "s3://$bucket/$target_backup" "$destination"
  log green "\nSuccessfully downloaded backup '$target_backup' to $destination"
elif [[ "$list_mode" == 0 ]]; then
  # Download mode, with empty backup name
  log red "Must specify a backup name to continue! Use --help for more info."
  exit 3
else
  # List mode
  backups=$(aws s3api list-objects --bucket "$bucket" --query 'Contents[].Key' --output text)
  read -ra backups_list <<< "$backups"
  backups_count="${#backups_list[@]}"
  
  if [[ "$backups_count" -eq 0 ]]; then
    log "No backups found."
  elif [[ "$backups_count" -eq 1 ]]; then
    log "Found 1 backup:"
  else
    log "Found ${#backups_list[@]} backups:"
  fi
  
  for backup in "${backups_list[@]}"; do
    log " - $backup"
  done
fi
  




