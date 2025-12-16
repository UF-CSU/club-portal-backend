# Postgres Management

## Backups

To create a system backup (deleted after 14 days):

```sh
docker compose -f docker-compose.prod.yml run --rm app sh -c "backup-db.sh"
# Example file: ./backups/AUTO_backup_devdatabase_2025-12-13_21-10-01.sql.gz
```

To create manual backup (never deleted):

```sh
docker compose -f docker-compose.prod.yml run --rm app sh -c "backup-db.sh test-backup"
# Example file: ./backups/test-backup.sql.gz
```

To restore from backup (leave out the `.sql.gz` extension):

```sh
docker compose -f docker-compose.prod.yml run --rm app sh -c "restore-db.sh AUTO_backup_<dbname>_<date>"
# Example command: restore-db.sh AUTO_backup_devdatabase_2025-12-13_21-10-01
```

To list all backups older than 14 days:

```sh
docker compose -f docker-compose.prod.yml run --rm app sh -c "clear-old-backups.sh -l"
# Example output:
# Found 2 backups older than 14 days:
# /var/backups/AUTO_backup_devdatabase_2025-12-12_19-42-11.sql.gz
# /var/backups/AUTO_backup_devdatabase_2025-12-13_19-42-11.sql.gz
```

To delete all backups older than 14 days:

```sh
docker compose -f docker-compose.prod.yml run --rm app sh -c "clear-old-backups.sh -l"
# Example output:
# Found 2 backups older than 14 days, deleting:
# /var/backups/AUTO_backup_devdatabase_2025-12-12_19-42-11.sql.gz
# /var/backups/AUTO_backup_devdatabase_2025-12-13_19-42-11.sql.gz
#
# Successfully deleted 2 backups
```

## Cron Jobs

1. Daily backups (every 6 hours):

   ```text
   0 0,12 * * * docker compose -f docker-compose.prod.yml run --rm sh -c "backup-db.sh" >> /etc/logs/crontab/backup-db.log 2>&1
   ```

2. Clear backups older than 14 days (midnight on sundays):

   ```text
   0 0 * * 0 docker compose -f docker-compose.prod.yml run --rm sh -c "clear-old-backups.sh" >> /etc/logs/crontab/clear-old-backups.log 2>&1
   ```

## Bumping Version

When bumping a new postgres version, we essentially have to create a new (empty) data directory for postgres and transfer our old data to that new data directory. This ensures the old data files do not interfere with the new ones, while allowing all of the data to stay the same. This requires approximately 5 minutes of downtime.

1. Create new backup

   ```sh
   docker compose -f docker-compose.prod.yml run app sh -c "backup-db.sh"
   ```

2. Stop all containers

   ```sh
   docker compose -f docker-compose.prod.yml down
   ```

3. Change name of postgres volume to include new version name
4. Set postgres image/tag
5. Spin up postgres image only

   ```sh
   docker compose -f docker-compose.prod.yml up postgres -d
   ```

6. Restore backup created in step 1 (replace dbname and date with appropriate values, should match name of backup created in `backups/`)

   ```sh
   docker compose -f docker-compose.prod.yml run app sh -c "restore-db.sh AUTO_backup_<dbname>_<date>"
   ```

7. Start all containers

   ```sh
   docker compose -f docker-compose.prod.yml up -d
   ```
