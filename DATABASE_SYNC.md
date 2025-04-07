# Database Synchronization System

This system ensures that your bot's data is synchronized between Railway and Replit hosting platforms, preventing data loss when switching between environments.

## How It Works

1. **Automatic Synchronization**: The system syncs data between platforms every 15 minutes using JSON files:
   - When running on Railway, the bot exports all data to a JSON file
   - When running on Replit, the bot imports this JSON data and merges it with any new data
   - This ensures complete data continuity regardless of platform

2. **Data Flow**:
   - Railway → Replit: JSON export from Railway database
   - Replit → Railway: JSON export from Replit database
   - The JSON format ensures compatibility across platforms

3. **Automatic Backups**: The system creates backups every 6 hours, keeping the 10 most recent ones.

## Commands

The database sync system provides several admin commands:

- `/dbrailwaysync`: Manually trigger a database sync
- `/dblastsynctime`: Check when the last sync occurred
- `/dbbackupsync`: Create a manual backup of all database data
- `/dbrestoresync`: Restore data from a previous backup

## Environment Variables

The system requires the `DATABASE_URL` environment variable to be set:

```
DATABASE_URL=postgres://username:password@hostname:port/database_name
```

If this environment variable is missing:
- Database sync features will be disabled
- A warning message will be logged
- The bot will still function normally without sync capabilities

## Switching Platforms

When switching from Railway to Replit (or vice versa):

1. Run the bot on the first platform
2. Use `/dbrailwaysync` to ensure latest data is exported
3. Stop the bot on first platform
4. Start the bot on second platform
5. The data will be automatically imported

## File Structure

- `/data/railway_sync.json`: Main sync file between platforms
- `/data/last_rank_data.json`: Special file for rank data compatibility
- `/backups/db_backup_YYYYMMDD_HHMMSS.json`: Backup files

## Error Handling

The system is designed to fail gracefully if database connection issues occur:
- If `DATABASE_URL` is missing, sync features are disabled but bot continues to operate
- Database errors are logged but won't crash the bot
- Commands that require database access will display appropriate error messages

## Troubleshooting

1. **Database sync not working**:
   - Check if `DATABASE_URL` is correctly set
   - Verify database connection using `/dbrailwaysync`
   - Check logs for specific error messages

2. **Missing data after platform switch**:
   - Run `/dbrailwaysync` on both platforms
   - Verify that the sync file was created properly
   - Check if the sync file is being properly read

3. **Sync command errors**:
   - Ensure PostgreSQL database is accessible
   - Check for proper permissions on database tables
   - Verify all required tables exist in the database