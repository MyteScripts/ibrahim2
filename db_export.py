import discord
import json
import os
import sqlite3
import logging
import datetime
from discord import app_commands
from discord.ext import commands
import io
import zipfile
import traceback

# Set up detailed logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DatabaseExportCog(commands.Cog):
    """Commands for exporting and backing up databases. The /dbsend command is restricted to admin ID: 1308527904497340467."""
    
    def __init__(self, bot):
        self.bot = bot
        self.owner_ids = [
            1308527904497340467,  # Admin's Discord user ID (only this ID can use /dbsend)
        ]
    
    @app_commands.command(
        name="dbsend",
        description="🗄️ Export and send all database files (Restricted to admin ID: 1308527904497340467)"
    )
    async def dbsend(self, interaction: discord.Interaction):
        """Export and send all database files to the requesting administrator. Restricted to admin ID: 1308527904497340467."""
        # Check if user is authorized (specific admin ID only)
        if interaction.user.id not in self.owner_ids:
            await interaction.response.send_message("⛔ This command is restricted to a specific administrator (ID: 1308527904497340467) only.", ephemeral=True)
            return
        
        # Defer the response with a loading state
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send("📦 Preparing database backup... Please wait, this may take a moment.", ephemeral=True)
        
        try:
            # Create timestamp for the backup filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"database_backup_{timestamp}.zip"
            
            # Create buffer for the ZIP file
            buffer = io.BytesIO()
            
            # Create the ZIP file in memory
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add SQLite database files
                for root, dirs, files in os.walk('./data'):
                    for file in files:
                        if file.endswith('.db') or file.endswith('.json'):
                            file_path = os.path.join(root, file)
                            try:
                                # Read file content
                                with open(file_path, 'rb') as f:
                                    content = f.read()
                                
                                # Add to ZIP
                                zipf.writestr(file, content)
                                logger.info(f"Added {file_path} to backup")
                            except Exception as e:
                                logger.error(f"Error adding {file_path}: {str(e)}")
                
                # Check for root web_dashboard.db
                if os.path.exists('./web_dashboard.db'):
                    try:
                        with open('./web_dashboard.db', 'rb') as f:
                            content = f.read()
                        zipf.writestr('root_web_dashboard.db', content)
                        logger.info(f"Added ./web_dashboard.db to backup")
                    except Exception as e:
                        logger.error(f"Error adding web_dashboard.db: {str(e)}")
                
                # Export PostgreSQL if available
                if os.environ.get("DATABASE_URL"):
                    try:
                        import psycopg2
                        
                        # Connect to PostgreSQL
                        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
                        cursor = conn.cursor()
                        
                        # Get all table names
                        cursor.execute("""
                            SELECT table_name FROM information_schema.tables
                            WHERE table_schema = 'public'
                        """)
                        tables = cursor.fetchall()
                        
                        # Export each table
                        pg_data = {}
                        for table in tables:
                            table_name = table[0]
                            
                            # Get column names
                            cursor.execute(f"""
                                SELECT column_name FROM information_schema.columns
                                WHERE table_schema = 'public' AND table_name = '{table_name}'
                            """)
                            columns = [col[0] for col in cursor.fetchall()]
                            
                            # Get table data
                            cursor.execute(f"SELECT * FROM {table_name}")
                            rows = cursor.fetchall()
                            
                            # Format as list of dictionaries
                            table_data = []
                            for row in rows:
                                row_dict = {}
                                for i, col in enumerate(columns):
                                    row_dict[col] = str(row[i])
                                table_data.append(row_dict)
                            
                            pg_data[table_name] = table_data
                        
                        # Add PostgreSQL data to ZIP
                        pg_json = json.dumps(pg_data, indent=2)
                        zipf.writestr('postgresql_data.json', pg_json)
                        logger.info("Successfully exported PostgreSQL data")
                        
                        # Close PostgreSQL connection
                        cursor.close()
                        conn.close()
                        
                    except Exception as e:
                        logger.error(f"Error exporting PostgreSQL data: {str(e)}")
                        zipf.writestr('postgres_export_error.txt', f"PostgreSQL Export Error:\n{str(e)}")
            
            # Prepare the buffer to be sent
            buffer.seek(0)
            
            # Create Discord file object
            discord_file = discord.File(buffer, filename=filename)
            
            # Send DM to user
            try:
                user = await self.bot.fetch_user(interaction.user.id)
                if user:
                    dm_channel = await user.create_dm()
                    await dm_channel.send(
                        "📤 Here's your database backup from your Discord bot. This contains all user data from both SQLite and PostgreSQL databases.",
                        file=discord_file
                    )
                    # Confirm in the original channel that DM was sent
                    await interaction.followup.send("✅ Database backup has been sent to your DMs!", ephemeral=True)
                    logger.info(f"Database backup sent to administrator's DM {interaction.user.id}")
                else:
                    raise Exception("Could not find user to send DM")
            except Exception as dm_error:
                logger.error(f"Failed to send DM: {str(dm_error)}")
                # If DM fails, send in channel as fallback
                await interaction.followup.send(
                    "⚠️ Could not send the file via DM. Sending here instead.",
                    file=discord_file,
                    ephemeral=True
                )
                logger.info(f"Database backup sent to channel as DM failed")
            
        except Exception as e:
            error_message = f"❌ Failed to create database backup: {str(e)}"
            logger.error(error_message)
            logger.error(traceback.format_exc())
            
            # Send error message
            await interaction.followup.send(error_message, ephemeral=True)

async def setup(bot):
    """Add the database export cog to the bot."""
    await bot.add_cog(DatabaseExportCog(bot))
    print("Database Export cog loaded!")