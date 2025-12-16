#!/bin/sh

set -e

OPTIND=1

ttl_days=14
backup_file_re=".*/AUTO_backup_.*_[0-9]{4}\-[0-9]{2}\-[0-9]{2}\_[0-9]{2}\-[0-9]{2}\-[0-9]{2}\.sql\.gz"
backup_dir="/var/backups"

files=$(find "$backup_dir" -type f -mtime "+$ttl_days" -regextype posix-extended -regex "$backup_file_re")
files_count=$(find "$backup_dir" -type f -mtime "+$ttl_days" -regextype posix-extended -regex "$backup_file_re" | wc -l)
backup_noun="backups"

if [ "$files_count" -eq 1 ]; then
  backup_noun="backup"
fi

# Parse input flags
DELETE=1

while getopts "l" opt; do
  case $opt in
    l)
      # -l, List Only
      DELETE=0
      ;;
    \?)
      # Invalid option
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done

# Check if there are files that match criteria
if [ -z "$files" ]; then
  echo "No $backup_noun found older than ${ttl_days} days."
  exit 0
elif [ "$DELETE" -eq 0 ]; then
  echo -e "Found $files_count $backup_noun older than ${ttl_days} days: \n${files}"
else
  echo -e "Found $files_count $backup_noun older than ${ttl_days} days, deleting: \n${files}"

  # Delete files that match time and regex criteria
  find "$backup_dir" -type f -mtime "+$ttl_days" -regextype posix-extended -regex "$backup_file_re" -delete
  
  echo -e "\nSuccessfully deleted $files_count $backup_noun"
fi

