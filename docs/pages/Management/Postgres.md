# Postgres Management

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
