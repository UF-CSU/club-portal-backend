#!/bin/bash

set -e

# Utils
function show-help {
  cat <<EOH
Usage: $0 (<path> [options])

Sync files from an S3 bucket to local storage volume. This should only be
done in the dev docker compose network, and not in production.

Options:
  -h,--help       Show this help message
  -l,--list       List backups available in S3 without pulling any
  -d,--dryrun     Dry-run syncing with AWS

Examples:
  $0
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
list_mode=0
dry_mode=0
media_root="/vol/web"
media_dir="$media_root/media/public"

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
    -d | --dryrun)
      dry_mode=1
      shift
      ;;
    *)
      # Unknown Option
      log red "Unknown argument: $1"
      exit 1
      ;;
  esac
done

# Check if in a docker container
if [[ ! -w "$media_root" || ! -x "$media_root" ]]; then
  log red "Media folder not found, or is not writable by current user. Make sure to run this in the development docker container."
else
  mkdir -p "$media_dir" # Ensure full directory path exists
fi

# Setup AWS
if [[ -z "$AWS_ACCESS_KEY_ID" || -z "$AWS_SECRET_ACCESS_KEY" || -z "$S3_STORAGE_BUCKET_NAME" ]]; then
  log red "Couldn't find one of the following env vars: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_STORAGE_BUCKET_NAME"
  exit 3
else
  bucket="s3://$S3_STORAGE_BUCKET_NAME"
fi

# Process request
if [[ "$list_mode" == 0 && "$dry_mode" == 1 ]]; then
  # Download mode, with backup name
  log "Running dry run sync for $bucket/public into local folder $media_dir"
  aws s3 sync "$bucket/public" "$media_dir" --dryrun
elif [[ "$list_mode" == 0 ]]; then
  aws s3 sync "$bucket/public" "$media_dir"
else
  # List mode
  aws s3api list-objects --bucket "$bucket" --query 'Contents[].Key'
fi
  




