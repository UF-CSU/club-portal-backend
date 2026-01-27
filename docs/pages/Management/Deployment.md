# Deployment Steps

The following steps take place inside of the club portal directory.

1. Create new system backup:

   ```sh
   docker compose -f docker-compose.prod.yml run --rm app sh -c "backup-db.sh"
   ```

2. Note the current GIT SHA (in case you need to revert back to the previous version of the code):

   ```sh
   git rev-parse HEAD
   ```

3. Pull changes from remote branch:

   ```sh
   git pull origin production
   ```

4. Restart server:

   ```sh
   docker-compose -f docker-compose.prod.yml build
   docker-compose -f docker-compose.prod.yml up -d --force-recreate
   ```
