import os
import json
import time
import asyncio
import logging
import psycopg2
from psycopg2 import sql
from psycopg2.extras import DictCursor
import discord
from discord import app_commands
from discord.ext import commands, tasks
from pg_database import PGDatabase
from logger import setup_logger

logger = setup_logger('db_railway_sync')

class DBRailwaySync(commands.Cog):
    """
    Cog for synchronizing PostgreSQL databases between Railway and Replit.
    
    This ensures seamless operation when switching between hosting platforms with
    no data loss for users in terms of levels, XP, coins, etc.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = "1308527904497340467"  # Bot owner ID
        self.last_sync_time = 0
        self.sync_interval = 15 * 60  # 15 minutes in seconds
        self.backup_interval = 6 * 60 * 60  # 6 hours in seconds
        self.data_directory = "data"
        self.backup_directory = "backups"
        self.pg_db = None
        
        # Create directories if they don't exist
        os.makedirs(self.data_directory, exist_ok=True)
        os.makedirs(self.backup_directory, exist_ok=True)
        
        # Try to initialize the database
        try:
            # Check if DATABASE_URL environment variable exists
            if not os.environ.get('DATABASE_URL'):
                logger.warning("DATABASE_URL environment variable not found! Database sync will be limited.")
                self.db_available = False
            else:
                self.pg_db = PGDatabase()
                self.db_available = True
                
                # Start the sync tasks only if database is available
                self.auto_sync.start()
                self.auto_backup.start()
                logger.info("DB Railway Sync cog initialized with full functionality")
        except Exception as e:
            logger.error(f"Error initializing database connection: {e}")
            self.db_available = False
            logger.info("DB Railway Sync cog initialized with limited functionality")
    
    def cog_unload(self):
        """Cancel scheduled tasks when the cog is unloaded"""
        if self.db_available:
            self.auto_sync.cancel()
            self.auto_backup.cancel()
    
    @tasks.loop(minutes=15)
    async def auto_sync(self):
        """Automatically sync databases every 15 minutes"""
        try:
            # Check if enough time has passed since the last sync
            if time.time() - self.last_sync_time < self.sync_interval:
                return
                
            logger.info("Starting automatic database sync...")
            
            # Export local database to JSON
            await self._export_to_json()
            
            # Import any existing JSON data
            await self._import_from_json()
            
            self.last_sync_time = time.time()
            logger.info(f"Auto sync completed successfully at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
            
        except Exception as e:
            logger.error(f"Error in auto sync: {e}", exc_info=True)
    
    @auto_sync.before_loop
    async def before_auto_sync(self):
        """Wait until the bot is ready before starting the sync loop"""
        await self.bot.wait_until_ready()
        # Wait 5 minutes after startup before first sync
        await asyncio.sleep(300)
        
    @tasks.loop(hours=6)
    async def auto_backup(self):
        """Create regular database backups every 6 hours"""
        try:
            logger.info("Starting automatic database backup...")
            
            timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            backup_file = f"{self.backup_directory}/db_backup_{timestamp}.json"
            
            # Export local database to backup JSON
            await self._export_to_json(backup_file)
            
            # Keep only the 10 most recent backups
            await self._prune_backups()
            
            logger.info(f"Auto backup completed successfully to {backup_file}")
            
        except Exception as e:
            logger.error(f"Error in auto backup: {e}", exc_info=True)
    
    @auto_backup.before_loop
    async def before_auto_backup(self):
        """Wait until the bot is ready before starting the backup loop"""
        await self.bot.wait_until_ready()
        # Wait 30 minutes after startup before first backup
        await asyncio.sleep(1800)
    
    async def _export_to_json(self, output_file=None):
        """Export the current PostgreSQL database to a JSON file"""
        if not self.db_available:
            logger.warning("Database not available for export, skipping")
            return False
            
        if output_file is None:
            output_file = f"{self.data_directory}/railway_sync.json"
            
        # Connect to database and fetch all data
        self.pg_db.ensure_connection()
        
        data = {
            "users": [],
            "settings": {},
            "invites": [],
            "mining_stats": [],
            "mining_resources": [],
            "mining_items": [],
            "profiles": [],
            "last_rank_data": {},
            "sync_time": int(time.time())
        }
        
        try:
            with self.pg_db.conn.cursor(cursor_factory=DictCursor) as cursor:
                # Export settings
                cursor.execute("SELECT * FROM settings WHERE setting_id = 1")
                settings = cursor.fetchone()
                if settings:
                    data["settings"] = dict(settings)
                
                # Export users
                cursor.execute("SELECT * FROM users")
                users = cursor.fetchall()
                for user in users:
                    data["users"].append(dict(user))
                
                # Export invites
                cursor.execute("SELECT * FROM invites")
                invites = cursor.fetchall()
                for invite in invites:
                    data["invites"].append(dict(invite))
                
                # Export mining_stats
                cursor.execute("SELECT * FROM mining_stats")
                mining_stats = cursor.fetchall()
                for stat in mining_stats:
                    data["mining_stats"].append(dict(stat))
                
                # Export mining_resources
                cursor.execute("SELECT * FROM mining_resources")
                mining_resources = cursor.fetchall()
                for resource in mining_resources:
                    data["mining_resources"].append(dict(resource))
                
                # Export mining_items
                cursor.execute("SELECT * FROM mining_items")
                mining_items = cursor.fetchall()
                for item in mining_items:
                    data["mining_items"].append(dict(item))
                
                # Export profiles
                cursor.execute("SELECT * FROM profiles")
                profiles = cursor.fetchall()
                for profile in profiles:
                    data["profiles"].append(dict(profile))
                
                # Export last_rank_data (if exists)
                try:
                    cursor.execute("SELECT * FROM last_rank_data")
                    last_rank_data = cursor.fetchall()
                    for rank_data in last_rank_data:
                        data["last_rank_data"][str(rank_data["user_id"])] = {
                            "level": rank_data["level"],
                            "xp": rank_data["xp"],
                            "coins": rank_data["coins"],
                            "timestamp": rank_data["timestamp"]
                        }
                except Exception as e:
                    # If table doesn't exist, load from file
                    logger.warning(f"Error exporting last_rank_data: {e}")
                    try:
                        last_rank_file = f"{self.data_directory}/last_rank_data.json"
                        if os.path.exists(last_rank_file):
                            with open(last_rank_file, 'r') as f:
                                data["last_rank_data"] = json.load(f)
                    except Exception as e2:
                        logger.error(f"Error loading last_rank_data from file: {e2}")
            
            # Save to JSON file
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=4, default=str)
            
            logger.info(f"Successfully exported database to {output_file}")
            return True
        
        except Exception as e:
            logger.error(f"Error exporting database: {e}", exc_info=True)
            return False
    
    async def _import_from_json(self, input_file=None):
        """Import data from a JSON file into the PostgreSQL database"""
        if not self.db_available:
            logger.warning("Database not available for import, skipping")
            return False
            
        if input_file is None:
            input_file = f"{self.data_directory}/railway_sync.json"
        
        if not os.path.exists(input_file):
            logger.warning(f"Sync file {input_file} does not exist, skipping import")
            return False
        
        try:
            # Load JSON data
            with open(input_file, 'r') as f:
                data = json.load(f)
            
            # Check if data is too old (more than 24 hours)
            if "sync_time" in data:
                sync_time = int(data["sync_time"])
                if time.time() - sync_time > 86400:  # 24 hours in seconds
                    logger.warning(f"Sync data is more than 24 hours old ({time.ctime(sync_time)}), skipping import")
                    return False
            
            # Connect to database
            self.pg_db.ensure_connection()
            
            # Start transaction
            with self.pg_db.conn:
                with self.pg_db.conn.cursor() as cursor:
                    # Import settings
                    if "settings" in data and data["settings"]:
                        settings = data["settings"]
                        settings_columns = [k for k in settings.keys() if k != "setting_id"]
                        settings_values = [settings[k] for k in settings_columns]
                        
                        update_query = sql.SQL("UPDATE settings SET {} WHERE setting_id = 1").format(
                            sql.SQL(', ').join(
                                sql.SQL("{} = %s").format(sql.Identifier(col)) 
                                for col in settings_columns
                            )
                        )
                        cursor.execute(update_query, settings_values)
                    
                    # Import users
                    if "users" in data:
                        for user_data in data["users"]:
                            user_id = user_data["user_id"]
                            
                            # Check if user exists
                            cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
                            exists = cursor.fetchone()
                            
                            if exists:
                                # Update existing user
                                user_columns = [k for k in user_data.keys() if k != "user_id"]
                                user_values = [user_data[k] for k in user_columns]
                                user_values.append(user_id)
                                
                                update_query = sql.SQL("UPDATE users SET {} WHERE user_id = %s").format(
                                    sql.SQL(', ').join(
                                        sql.SQL("{} = %s").format(sql.Identifier(col)) 
                                        for col in user_columns
                                    )
                                )
                                cursor.execute(update_query, user_values)
                            else:
                                # Insert new user
                                columns = user_data.keys()
                                values = [user_data[col] for col in columns]
                                
                                insert_query = sql.SQL("INSERT INTO users ({}) VALUES ({})").format(
                                    sql.SQL(', ').join(sql.Identifier(col) for col in columns),
                                    sql.SQL(', ').join(sql.Placeholder() for _ in columns)
                                )
                                cursor.execute(insert_query, values)
                    
                    # Import invites
                    if "invites" in data:
                        for invite_data in data["invites"]:
                            user_id = invite_data["user_id"]
                            
                            # Check if invite exists
                            cursor.execute("SELECT user_id FROM invites WHERE user_id = %s", (user_id,))
                            exists = cursor.fetchone()
                            
                            if exists:
                                # Update existing invite
                                invite_columns = [k for k in invite_data.keys() if k != "user_id"]
                                invite_values = [invite_data[k] for k in invite_columns]
                                invite_values.append(user_id)
                                
                                update_query = sql.SQL("UPDATE invites SET {} WHERE user_id = %s").format(
                                    sql.SQL(', ').join(
                                        sql.SQL("{} = %s").format(sql.Identifier(col)) 
                                        for col in invite_columns
                                    )
                                )
                                cursor.execute(update_query, invite_values)
                            else:
                                # Insert new invite
                                columns = invite_data.keys()
                                values = [invite_data[col] for col in columns]
                                
                                insert_query = sql.SQL("INSERT INTO invites ({}) VALUES ({})").format(
                                    sql.SQL(', ').join(sql.Identifier(col) for col in columns),
                                    sql.SQL(', ').join(sql.Placeholder() for _ in columns)
                                )
                                cursor.execute(insert_query, values)
                    
                    # Import mining_stats
                    if "mining_stats" in data:
                        for mining_data in data["mining_stats"]:
                            user_id = mining_data["user_id"]
                            
                            # Check if stats exist
                            cursor.execute("SELECT user_id FROM mining_stats WHERE user_id = %s", (user_id,))
                            exists = cursor.fetchone()
                            
                            if exists:
                                # Update existing stats
                                mining_columns = [k for k in mining_data.keys() if k != "user_id"]
                                mining_values = [mining_data[k] for k in mining_columns]
                                mining_values.append(user_id)
                                
                                update_query = sql.SQL("UPDATE mining_stats SET {} WHERE user_id = %s").format(
                                    sql.SQL(', ').join(
                                        sql.SQL("{} = %s").format(sql.Identifier(col)) 
                                        for col in mining_columns
                                    )
                                )
                                cursor.execute(update_query, mining_values)
                            else:
                                # Insert new stats
                                columns = mining_data.keys()
                                values = [mining_data[col] for col in columns]
                                
                                insert_query = sql.SQL("INSERT INTO mining_stats ({}) VALUES ({})").format(
                                    sql.SQL(', ').join(sql.Identifier(col) for col in columns),
                                    sql.SQL(', ').join(sql.Placeholder() for _ in columns)
                                )
                                cursor.execute(insert_query, values)
                    
                    # Import mining_resources with upsert
                    if "mining_resources" in data:
                        for resource_data in data["mining_resources"]:
                            user_id = resource_data["user_id"]
                            resource_name = resource_data["resource_name"]
                            amount = resource_data["amount"]
                            
                            cursor.execute("""
                                INSERT INTO mining_resources (user_id, resource_name, amount)
                                VALUES (%s, %s, %s)
                                ON CONFLICT (user_id, resource_name) 
                                DO UPDATE SET amount = EXCLUDED.amount
                            """, (user_id, resource_name, amount))
                    
                    # Import mining_items with upsert
                    if "mining_items" in data:
                        for item_data in data["mining_items"]:
                            user_id = item_data["user_id"]
                            item_name = item_data["item_name"]
                            amount = item_data["amount"]
                            
                            cursor.execute("""
                                INSERT INTO mining_items (user_id, item_name, amount)
                                VALUES (%s, %s, %s)
                                ON CONFLICT (user_id, item_name) 
                                DO UPDATE SET amount = EXCLUDED.amount
                            """, (user_id, item_name, amount))
                    
                    # Import profiles
                    if "profiles" in data:
                        for profile_data in data["profiles"]:
                            user_id = profile_data["user_id"]
                            
                            # Check if profile exists
                            cursor.execute("SELECT user_id FROM profiles WHERE user_id = %s", (user_id,))
                            exists = cursor.fetchone()
                            
                            if exists:
                                # Update existing profile
                                profile_columns = [k for k in profile_data.keys() if k != "user_id"]
                                profile_values = [profile_data[k] for k in profile_columns]
                                profile_values.append(user_id)
                                
                                update_query = sql.SQL("UPDATE profiles SET {} WHERE user_id = %s").format(
                                    sql.SQL(', ').join(
                                        sql.SQL("{} = %s").format(sql.Identifier(col)) 
                                        for col in profile_columns
                                    )
                                )
                                cursor.execute(update_query, profile_values)
                            else:
                                # Insert new profile
                                columns = profile_data.keys()
                                values = [profile_data[col] for col in columns]
                                
                                insert_query = sql.SQL("INSERT INTO profiles ({}) VALUES ({})").format(
                                    sql.SQL(', ').join(sql.Identifier(col) for col in columns),
                                    sql.SQL(', ').join(sql.Placeholder() for _ in columns)
                                )
                                cursor.execute(insert_query, values)
                    
                    # Import last_rank_data
                    if "last_rank_data" in data:
                        # First check if table exists
                        cursor.execute("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_name = 'last_rank_data'
                            )
                        """)
                        table_exists = cursor.fetchone()[0]
                        
                        if not table_exists:
                            # Create the table if it doesn't exist
                            cursor.execute("""
                                CREATE TABLE last_rank_data (
                                    user_id BIGINT PRIMARY KEY,
                                    level INTEGER,
                                    xp INTEGER,
                                    coins REAL,
                                    timestamp BIGINT
                                )
                            """)
                        
                        # Update or insert last_rank_data
                        for user_id, rank_data in data["last_rank_data"].items():
                            cursor.execute("""
                                INSERT INTO last_rank_data (user_id, level, xp, coins, timestamp)
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT (user_id) 
                                DO UPDATE SET 
                                    level = EXCLUDED.level,
                                    xp = EXCLUDED.xp,
                                    coins = EXCLUDED.coins,
                                    timestamp = EXCLUDED.timestamp
                            """, (
                                int(user_id), 
                                rank_data["level"], 
                                rank_data["xp"], 
                                rank_data["coins"], 
                                rank_data["timestamp"]
                            ))
                
                # Also save last_rank_data to file for backward compatibility
                with open(f"{self.data_directory}/last_rank_data.json", 'w') as f:
                    json.dump(data["last_rank_data"], f, indent=4)
            
            logger.info(f"Successfully imported data from {input_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing database: {e}", exc_info=True)
            return False
    
    async def _prune_backups(self, keep=10):
        """Keep only the specified number of most recent backups"""
        try:
            # Get all backup files
            backup_files = [f for f in os.listdir(self.backup_directory) if f.startswith("db_backup_") and f.endswith(".json")]
            
            # Sort by name (which includes timestamp)
            backup_files.sort(reverse=True)
            
            # Remove old backups
            if len(backup_files) > keep:
                for old_file in backup_files[keep:]:
                    file_path = os.path.join(self.backup_directory, old_file)
                    os.remove(file_path)
                    logger.info(f"Removed old backup: {old_file}")
        
        except Exception as e:
            logger.error(f"Error pruning backups: {e}", exc_info=True)
    
    @app_commands.command(
        name="dbrailwaysync", 
        description="Sync database with Railway (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def cmd_railway_sync(self, interaction: discord.Interaction):
        """
        Manually trigger a database sync with Railway.
        This command will export current data and import any existing sync data.
        """
        if str(interaction.user.id) != self.owner_id:
            await interaction.response.send_message(
                "⚠️ This command can only be used by the bot owner.", 
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        if not self.db_available:
            await interaction.followup.send(
                "⚠️ Database connection is not available. Please check your DATABASE_URL environment variable.",
                ephemeral=True
            )
            return
            
        try:
            # Export current data
            export_success = await self._export_to_json()
            if not export_success:
                await interaction.followup.send(
                    "❌ Failed to export database. Check logs for details.", 
                    ephemeral=True
                )
                return
            
            # Import any existing data
            import_success = await self._import_from_json()
            if not import_success:
                await interaction.followup.send(
                    "❌ Failed to import database. Check logs for details.", 
                    ephemeral=True
                )
                return
            
            self.last_sync_time = time.time()
            
            await interaction.followup.send(
                "✅ Database sync with Railway completed successfully!", 
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error in railway sync command: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ An error occurred during database sync: {str(e)}", 
                ephemeral=True
            )
    
    @app_commands.command(
        name="dblastsynctime", 
        description="Show when the last database sync occurred (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def cmd_last_sync_time(self, interaction: discord.Interaction):
        """Show when the last database sync occurred."""
        if str(interaction.user.id) != self.owner_id:
            await interaction.response.send_message(
                "⚠️ This command can only be used by the bot owner.", 
                ephemeral=True
            )
            return
        
        if self.last_sync_time == 0:
            await interaction.response.send_message(
                "No database sync has occurred since the bot started.", 
                ephemeral=True
            )
            return
        
        last_sync = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.last_sync_time))
        seconds_ago = int(time.time() - self.last_sync_time)
        
        await interaction.response.send_message(
            f"📊 **Last Database Sync**\n"
            f"• Time: {last_sync}\n"
            f"• {self._format_time_ago(seconds_ago)} ago\n"
            f"• Next auto-sync: {self._format_time_until(self.sync_interval - seconds_ago)}", 
            ephemeral=True
        )
    
    @app_commands.command(
        name="dbforceimport", 
        description="Force import from a Railway sync file (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def cmd_force_import(self, interaction: discord.Interaction):
        """Force import from a Railway sync file"""
        if str(interaction.user.id) != self.owner_id:
            await interaction.response.send_message(
                "⚠️ This command can only be used by the bot owner.", 
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        if not self.db_available:
            await interaction.followup.send(
                "⚠️ Database connection is not available. Please check your DATABASE_URL environment variable.",
                ephemeral=True
            )
            return
            
        try:
            import_file = f"{self.data_directory}/railway_sync.json"
            
            if not os.path.exists(import_file):
                await interaction.followup.send(
                    f"❌ Sync file not found at {import_file}", 
                    ephemeral=True
                )
                return
            
            # Get file info
            file_size = os.path.getsize(import_file) / 1024  # Size in KB
            file_time = os.path.getmtime(import_file)
            file_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(file_time))
            
            # Import the data
            import_success = await self._import_from_json(import_file)
            
            if import_success:
                self.last_sync_time = time.time()
                
                await interaction.followup.send(
                    f"✅ Successfully imported database from {import_file}\n"
                    f"• File size: {file_size:.2f} KB\n"
                    f"• File date: {file_time_str}", 
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ Failed to import database from {import_file}. Check logs for details.", 
                    ephemeral=True
                )
            
        except Exception as e:
            logger.error(f"Error in force import command: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ An error occurred during force import: {str(e)}", 
                ephemeral=True
            )
    
    @app_commands.command(
        name="dbbackupsync", 
        description="Create a backup of the current database (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def cmd_backup(self, interaction: discord.Interaction):
        """Create a backup of the current database"""
        if str(interaction.user.id) != self.owner_id:
            await interaction.response.send_message(
                "⚠️ This command can only be used by the bot owner.", 
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        if not self.db_available:
            await interaction.followup.send(
                "⚠️ Database connection is not available. Please check your DATABASE_URL environment variable.",
                ephemeral=True
            )
            return
            
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            backup_file = f"{self.backup_directory}/db_backup_{timestamp}.json"
            
            export_success = await self._export_to_json(backup_file)
            
            if export_success:
                file_size = os.path.getsize(backup_file) / 1024  # Size in KB
                
                await interaction.followup.send(
                    f"✅ Successfully created database backup at {backup_file}\n"
                    f"• File size: {file_size:.2f} KB\n"
                    f"• Timestamp: {timestamp}\n\n"
                    f"Use `/dbrestoresync` to restore from this backup if needed.", 
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Failed to create database backup. Check logs for details.", 
                    ephemeral=True
                )
            
        except Exception as e:
            logger.error(f"Error in backup command: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ An error occurred during backup: {str(e)}", 
                ephemeral=True
            )
    
    @app_commands.command(
        name="dbrestoresync", 
        description="Restore database from a backup (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def cmd_restore(self, interaction: discord.Interaction):
        """Restore database from a backup"""
        if str(interaction.user.id) != self.owner_id:
            await interaction.response.send_message(
                "⚠️ This command can only be used by the bot owner.", 
                ephemeral=True
            )
            return
            
        if not self.db_available:
            await interaction.response.send_message(
                "⚠️ Database connection is not available. Please check your DATABASE_URL environment variable.",
                ephemeral=True
            )
            return
        
        # First show available backups
        backup_files = [f for f in os.listdir(self.backup_directory) if f.startswith("db_backup_") and f.endswith(".json")]
        backup_files.sort(reverse=True)
        
        if not backup_files:
            await interaction.response.send_message(
                "❌ No backup files found in the backup directory.", 
                ephemeral=True
            )
            return
        
        # Create a message with available backups
        backup_list = "\n".join([f"• {idx+1}. {file}" for idx, file in enumerate(backup_files[:10])])
        
        await interaction.response.send_message(
            f"📂 **Available Backups**\n{backup_list}\n\n"
            f"Reply with the number of the backup you want to restore, or 'cancel' to abort.", 
            ephemeral=False
        )
        
        def check(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
        
        try:
            reply_msg = await self.bot.wait_for('message', check=check, timeout=120)
            
            if reply_msg.content.lower() == 'cancel':
                await interaction.followup.send("Restore operation cancelled.", ephemeral=True)
                return
            
            try:
                selection = int(reply_msg.content.strip())
                if selection < 1 or selection > len(backup_files[:10]):
                    await interaction.followup.send(
                        f"Invalid selection. Please choose a number between 1 and {min(len(backup_files), 10)}.", 
                        ephemeral=True
                    )
                    return
                
                selected_file = backup_files[selection - 1]
                backup_path = os.path.join(self.backup_directory, selected_file)
                
                # Confirm restore
                await interaction.followup.send(
                    f"⚠️ **WARNING: You are about to restore the database from {selected_file}**\n"
                    f"This will overwrite current data. Are you sure?\n\n"
                    f"Reply with 'confirm' to proceed or anything else to cancel.", 
                    ephemeral=False
                )
                
                confirm_msg = await self.bot.wait_for('message', check=check, timeout=60)
                
                if confirm_msg.content.lower() != 'confirm':
                    await interaction.followup.send("Restore operation cancelled.", ephemeral=True)
                    return
                
                # Perform the restore
                await interaction.followup.send("⏳ Restoring database from backup...", ephemeral=False)
                
                import_success = await self._import_from_json(backup_path)
                
                if import_success:
                    self.last_sync_time = time.time()
                    
                    await interaction.followup.send(
                        f"✅ Successfully restored database from {selected_file}", 
                        ephemeral=False
                    )
                else:
                    await interaction.followup.send(
                        f"❌ Failed to restore database from {selected_file}. Check logs for details.", 
                        ephemeral=False
                    )
                
            except ValueError:
                await interaction.followup.send("Invalid input. Please enter a number.", ephemeral=True)
                
        except asyncio.TimeoutError:
            await interaction.followup.send("Restore operation timed out.", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in restore command: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ An error occurred during restore: {str(e)}", 
                ephemeral=True
            )
    
    def _format_time_ago(self, seconds):
        """Format a time duration in seconds to a human-readable string"""
        if seconds < 60:
            return f"{seconds} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''}"
        else:
            days = seconds // 86400
            return f"{days} day{'s' if days != 1 else ''}"
    
    def _format_time_until(self, seconds):
        """Format a time until in seconds to a human-readable string"""
        if seconds <= 0:
            return "soon"
        else:
            return self._format_time_ago(seconds)

async def setup(bot):
    """Add the Railway database sync cog to the bot."""
    await bot.add_cog(DBRailwaySync(bot))