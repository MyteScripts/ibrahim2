import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import logging
import requests
import sqlite3
import time
from datetime import datetime
from logger import setup_logger

# Set up logger
logger = setup_logger('brawl_stars')

# Brawl Stars API URLs
BASE_URL = "https://api.brawlstars.com/v1"
PLAYER_URL = f"{BASE_URL}/players"
RANKINGS_URL = f"{BASE_URL}/rankings"

class BrawlStars(commands.Cog):
    """Commands for retrieving Brawl Stars player statistics and rankings."""
    
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.environ.get("BRAWL_STARS_API_KEY", "")
        self.db_path = "data/brawl_stars.db"
        self._setup_database()
    
    def _setup_database(self):
        """Set up the SQLite database for storing linked player tags."""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create table for linked player tags
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS linked_players (
                discord_id TEXT PRIMARY KEY,
                player_tag TEXT NOT NULL,
                username TEXT,
                linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Brawl Stars database initialized")
        except Exception as e:
            logger.error(f"Error setting up Brawl Stars database: {e}")
    
    def _get_headers(self):
        """Get headers for Brawl Stars API requests."""
        if not self.api_key:
            logger.error("Brawl Stars API key not found")
            return None
            
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
    
    def _format_player_tag(self, tag):
        """Format a player tag to ensure it starts with # if not already."""
        if not tag.startswith('#'):
            tag = f"#{tag}"
        return tag
    
    def _fetch_player_data(self, player_tag):
        """Fetch player data from the Brawl Stars API."""
        headers = self._get_headers()
        if not headers:
            return None
            
        try:
            formatted_tag = self._format_player_tag(player_tag)
            # URL encode the # to %23
            encoded_tag = formatted_tag.replace('#', '%23')
            url = f"{PLAYER_URL}/{encoded_tag}"
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"Player {player_tag} not found")
                return {"error": "Player not found"}
            elif response.status_code == 403:
                logger.error("API key invalid or unauthorized")
                return {"error": "API key invalid or unauthorized"}
            else:
                logger.error(f"Error fetching player data: {response.status_code}")
                return {"error": f"API error: {response.status_code}"}
        except Exception as e:
            logger.error(f"Exception while fetching player data: {e}")
            return {"error": f"Error: {str(e)}"}
    
    def _fetch_player_ranking(self, player_tag):
        """Fetch player global and local ranking data."""
        player_data = self._fetch_player_data(player_tag)
        if not player_data or "error" in player_data:
            return None
        
        # Extract ranking data if available
        ranking_data = {
            "global": player_data.get("globalRank", "Unranked"),
            "name": player_data.get("name", "Unknown"),
            "trophies": player_data.get("trophies", 0),
            "highest_trophies": player_data.get("highestTrophies", 0),
            "country_code": player_data.get("club", {}).get("countryCode", "global")
        }
        
        # Try to get country ranking
        if ranking_data["country_code"] != "global":
            try:
                headers = self._get_headers()
                if headers:
                    url = f"{RANKINGS_URL}/players?limit=200&countryCode={ranking_data['country_code']}"
                    response = requests.get(url, headers=headers)
                    
                    if response.status_code == 200:
                        players = response.json().get("items", [])
                        formatted_tag = self._format_player_tag(player_tag)
                        
                        # Search for player in country rankings
                        for index, p in enumerate(players, 1):
                            if p.get("tag") == formatted_tag:
                                ranking_data["country_rank"] = index
                                break
                        
                        if "country_rank" not in ranking_data:
                            ranking_data["country_rank"] = "Unranked in top 200"
            except Exception as e:
                logger.error(f"Error fetching country ranking: {e}")
                ranking_data["country_rank"] = "Error retrieving"
        else:
            ranking_data["country_rank"] = "No country set"
        
        return ranking_data
    
    def _link_player(self, discord_id, player_tag, username=None):
        """Link a Discord user to a Brawl Stars player tag."""
        try:
            # First check if the player tag is valid
            player_data = self._fetch_player_data(player_tag)
            if not player_data or "error" in player_data:
                return False, player_data.get("error", "Unknown error") if player_data else "Could not fetch player data"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Extract username from player data if not provided
            if not username and player_data:
                username = player_data.get("name", "Unknown")
            
            formatted_tag = self._format_player_tag(player_tag)
            
            # Check if user already has a linked account
            cursor.execute("SELECT player_tag FROM linked_players WHERE discord_id = ?", (str(discord_id),))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute(
                    "UPDATE linked_players SET player_tag = ?, username = ?, linked_at = CURRENT_TIMESTAMP WHERE discord_id = ?",
                    (formatted_tag, username, str(discord_id))
                )
                result = True, "Updated"
            else:
                cursor.execute(
                    "INSERT INTO linked_players (discord_id, player_tag, username) VALUES (?, ?, ?)",
                    (str(discord_id), formatted_tag, username)
                )
                result = True, "Linked"
            
            conn.commit()
            conn.close()
            return result
        except Exception as e:
            logger.error(f"Error linking player: {e}")
            return False, f"Error: {str(e)}"
    
    def _get_linked_tag(self, discord_id):
        """Get the linked Brawl Stars player tag for a Discord user."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT player_tag FROM linked_players WHERE discord_id = ?", (str(discord_id),))
            result = cursor.fetchone()
            
            conn.close()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting linked tag: {e}")
            return None
    
    def _create_stats_embed(self, player_data, user=None):
        """Create an embed with player statistics."""
        if not player_data or "error" in player_data:
            error_msg = player_data.get("error", "Unknown error") if player_data else "Could not fetch player data"
            embed = discord.Embed(
                title="❌ Error",
                description=f"Could not retrieve player stats: {error_msg}",
                color=discord.Color.red()
            )
            return embed
        
        # Create embed with player stats
        embed = discord.Embed(
            title=f"🏆 {player_data.get('name', 'Unknown')} Stats",
            description=f"Player Tag: `{player_data.get('tag', 'Unknown')}`",
            color=discord.Color.blue()
        )
        
        if user:
            embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        
        # Basic stats
        embed.add_field(
            name="📊 Basic Stats",
            value=(
                f"🎮 **Level:** {player_data.get('expLevel', 0)}\n"
                f"🏆 **Trophies:** {player_data.get('trophies', 0)}\n"
                f"🔝 **Highest Trophies:** {player_data.get('highestTrophies', 0)}\n"
                f"🎯 **Solo Victories:** {player_data.get('soloVictories', 0)}\n"
                f"👥 **Duo Victories:** {player_data.get('duoVictories', 0)}\n"
                f"🤝 **3v3 Victories:** {player_data.get('3vs3Victories', 0)}"
            ),
            inline=True
        )
        
        # Brawlers stats
        brawlers = player_data.get("brawlers", [])
        brawler_count = len(brawlers)
        max_power_count = sum(1 for b in brawlers if b.get("power") == 11)
        max_trophy_brawler = max(brawlers, key=lambda b: b.get("trophies", 0)) if brawlers else {}
        
        embed.add_field(
            name="🦸‍♂️ Brawlers",
            value=(
                f"🧩 **Unlocked:** {brawler_count}\n"
                f"⚡ **Maxed:** {max_power_count}\n"
                f"🥇 **Highest:** {max_trophy_brawler.get('name', 'None')} "
                f"({max_trophy_brawler.get('trophies', 0)} 🏆)"
            ),
            inline=True
        )
        
        # Club info
        club = player_data.get("club", {})
        if club:
            embed.add_field(
                name="🏰 Club",
                value=(
                    f"🔖 **Name:** {club.get('name', 'Not in a club')}\n"
                    f"🪪 **Tag:** {club.get('tag', 'N/A')}\n"
                    f"📊 **Role:** {club.get('role', 'N/A')}"
                ),
                inline=False
            )
        else:
            embed.add_field(
                name="🏰 Club",
                value="Not in a club",
                inline=False
            )
        
        # Add footer with timestamp
        embed.set_footer(text=f"Data fetched • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return embed
    
    def _create_rank_embed(self, rank_data, user=None):
        """Create an embed with player ranking information."""
        if not rank_data:
            embed = discord.Embed(
                title="❌ Error",
                description="Could not retrieve player ranking",
                color=discord.Color.red()
            )
            return embed
        
        # Create embed with player ranking
        embed = discord.Embed(
            title=f"🏆 {rank_data.get('name', 'Unknown')} Ranking",
            color=discord.Color.gold()
        )
        
        if user:
            embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        
        # Add rank fields
        embed.add_field(
            name="🌎 Global Rank",
            value=f"#{rank_data.get('global', 'Unranked')}",
            inline=True
        )
        
        embed.add_field(
            name="🏳️ Country Rank",
            value=f"#{rank_data.get('country_rank', 'Unranked')}",
            inline=True
        )
        
        # Add trophy information
        embed.add_field(
            name="🏆 Trophies",
            value=(
                f"**Current:** {rank_data.get('trophies', 0)}\n"
                f"**Highest:** {rank_data.get('highest_trophies', 0)}"
            ),
            inline=False
        )
        
        # Add footer with timestamp
        embed.set_footer(text=f"Data fetched • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return embed
    
    @app_commands.command(name="linkbrawl", description="Link your Discord account to your Brawl Stars player tag")
    @app_commands.describe(player_tag="Your Brawl Stars player tag (with or without #)")
    async def link_brawl(self, interaction: discord.Interaction, player_tag: str):
        """Link your Discord account to your Brawl Stars player tag."""
        await interaction.response.defer(ephemeral=True)
        
        success, message = self._link_player(interaction.user.id, player_tag, interaction.user.display_name)
        
        if success:
            player_data = self._fetch_player_data(player_tag)
            player_name = player_data.get("name", "Unknown") if player_data and "error" not in player_data else "Unknown"
            
            embed = discord.Embed(
                title="✅ Account Linked",
                description=f"Your Discord account is now linked to Brawl Stars player `{player_name}` with tag `{self._format_player_tag(player_tag)}`",
                color=discord.Color.green()
            )
            embed.set_footer(text="You can now use /brawlstats and /brawlrank without specifying a player tag")
        else:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to link account: {message}",
                color=discord.Color.red()
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="brawlstats", description="View Brawl Stars player statistics")
    @app_commands.describe(player_tag="Brawl Stars player tag (with or without #) - leave empty to use your linked account")
    async def brawl_stats(self, interaction: discord.Interaction, player_tag: str = None):
        """View Brawl Stars player statistics."""
        await interaction.response.defer()
        
        # If no player tag provided, check for linked account
        if not player_tag:
            player_tag = self._get_linked_tag(interaction.user.id)
            if not player_tag:
                embed = discord.Embed(
                    title="❌ No Account Linked",
                    description="You don't have a linked Brawl Stars account. Please either provide a player tag or link your account with `/linkbrawl`.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
        
        # Fetch player data
        player_data = self._fetch_player_data(player_tag)
        embed = self._create_stats_embed(player_data, interaction.user)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="brawlrank", description="View Brawl Stars player ranking")
    @app_commands.describe(player_tag="Brawl Stars player tag (with or without #) - leave empty to use your linked account")
    async def brawl_rank(self, interaction: discord.Interaction, player_tag: str = None):
        """View Brawl Stars player ranking."""
        await interaction.response.defer()
        
        # If no player tag provided, check for linked account
        if not player_tag:
            player_tag = self._get_linked_tag(interaction.user.id)
            if not player_tag:
                embed = discord.Embed(
                    title="❌ No Account Linked",
                    description="You don't have a linked Brawl Stars account. Please either provide a player tag or link your account with `/linkbrawl`.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
        
        # Fetch player ranking
        rank_data = self._fetch_player_ranking(player_tag)
        embed = self._create_rank_embed(rank_data, interaction.user)
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    """Add the Brawl Stars cog to the bot."""
    cog = BrawlStars(bot)
    await bot.add_cog(cog)
    # Add the commands to the 'rank' permissions
    from permissions import add_command_to_public
    add_command_to_public("linkbrawl")
    add_command_to_public("brawlstats")
    add_command_to_public("brawlrank")
    logger.info("Brawl Stars cog loaded")