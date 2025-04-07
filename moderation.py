import discord
from discord import app_commands
from discord.ext import commands
import logging
import datetime
import json
import asyncio

class ModerationCog(commands.Cog):
    """Cog for moderation commands like ban, mute, kick, and warn."""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('moderation')
        self.log_channel_id = None
        self.load_settings()
        
        # Track active mutes
        self.active_mutes = {}
        self.active_warns = {}
        
        # Load active mutes/warns from file
        self.load_active_moderation_actions()
        
        # We'll start the check loop when the bot is ready
        self.expired_actions_task = None
        
        # Register on_ready event listener
        self.bot.add_listener(self.on_ready, 'on_ready')
    
    def load_settings(self):
        """Load moderation settings from settings.json."""
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
                self.log_channel_id = settings.get('moderation_log_channel_id')
        except Exception as e:
            self.logger.error(f"Failed to load moderation settings: {e}")
    
    def save_settings(self):
        """Save moderation settings to settings.json."""
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
            
            settings['moderation_log_channel_id'] = self.log_channel_id
            
            with open('settings.json', 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to save moderation settings: {e}")
    
    def load_active_moderation_actions(self):
        """Load active mutes and warns from file."""
        try:
            with open('data/moderation_actions.json', 'r') as f:
                data = json.load(f)
                self.active_mutes = data.get('mutes', {})
                self.active_warns = data.get('warns', {})
        except FileNotFoundError:
            self.logger.info("No active moderation actions found. Creating new file.")
            self.save_active_moderation_actions()
        except Exception as e:
            self.logger.error(f"Failed to load active moderation actions: {e}")
    
    def save_active_moderation_actions(self):
        """Save active mutes and warns to file."""
        try:
            # Ensure the directory exists
            import os
            os.makedirs('data', exist_ok=True)
            
            data = {
                'mutes': self.active_mutes,
                'warns': self.active_warns
            }
            
            with open('data/moderation_actions.json', 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to save active moderation actions: {e}")
    
    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        # Save active moderation actions
        self.save_active_moderation_actions()
        
        # Cancel the task if it exists
        if self.expired_actions_task:
            self.expired_actions_task.cancel()
            
    async def on_ready(self):
        """Start checking for expired actions when the bot is ready."""
        if self.expired_actions_task is None or self.expired_actions_task.done():
            # Start the check loop
            self.expired_actions_task = self.bot.loop.create_task(self.check_expired_actions_loop())
            self.logger.info("Started expired actions check loop")
    
    async def log_moderation_action(self, action_type, moderator, user, reason, duration=None):
        """Log a moderation action to the log channel."""
        if not self.log_channel_id:
            self.logger.warning("No log channel set for moderation actions")
            return
        
        try:
            channel = self.bot.get_channel(int(self.log_channel_id))
            if not channel:
                self.logger.error(f"Could not find log channel with ID {self.log_channel_id}")
                return
            
            embed = discord.Embed(
                title=f"{action_type} Action",
                description=f"{user.mention} ({user.name}) has been {action_type.lower()}ed",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            
            embed.add_field(name="Moderator", value=f"{moderator.mention} ({moderator.name})", inline=False)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            if duration:
                embed.add_field(name="Duration", value=duration, inline=False)
            
            embed.set_footer(text=f"User ID: {user.id}")
            
            await channel.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Failed to log moderation action: {e}")
    
    async def dm_user(self, user, action_type, reason, duration=None, guild_name=None):
        """Send a DM to a user about a moderation action."""
        try:
            embed = discord.Embed(
                title=f"You have been {action_type}ed",
                description=f"You have been {action_type}ed in {guild_name or 'the server'}",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            
            embed.add_field(name="Reason", value=reason, inline=False)
            
            if duration:
                embed.add_field(name="Duration", value=duration, inline=False)
            
            await user.send(embed=embed)
            return True
        except Exception as e:
            self.logger.error(f"Failed to DM user {user.id} about {action_type} action: {e}")
            return False
    
    def parse_duration(self, duration_str):
        """Parse a duration string (e.g. '1d', '2h', '30m') into seconds."""
        if duration_str.lower() == 'permanent' or duration_str.lower() == 'perm':
            return None  # None indicates permanent
        
        try:
            # Parse the duration (e.g. "1d" = 1 day, "2h" = 2 hours)
            time_value = int(duration_str[:-1])
            time_unit = duration_str[-1].lower()
            
            if time_unit == 's':
                return time_value
            elif time_unit == 'm':
                return time_value * 60
            elif time_unit == 'h':
                return time_value * 3600
            elif time_unit == 'd':
                return time_value * 86400
            elif time_unit == 'w':
                return time_value * 604800
            else:
                return 3600  # Default to 1 hour if unit not recognized
        except:
            return 3600  # Default to 1 hour if parsing fails
    
    def format_duration(self, seconds):
        """Format seconds into a human-readable duration string."""
        if seconds is None:
            return "Permanent"
        
        if seconds < 60:
            return f"{seconds} seconds"
        elif seconds < 3600:
            return f"{seconds // 60} minutes"
        elif seconds < 86400:
            return f"{seconds // 3600} hours"
        elif seconds < 604800:
            return f"{seconds // 86400} days"
        else:
            return f"{seconds // 604800} weeks"
    
    def calculate_expiry(self, duration_seconds):
        """Calculate the expiry timestamp for a duration in seconds."""
        if duration_seconds is None:
            return None  # None indicates permanent
        
        return datetime.datetime.now().timestamp() + duration_seconds
    
    async def check_expired_actions_loop(self):
        """Loop to check for and remove expired mutes and warns every minute."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await self.check_expired_actions()
            await asyncio.sleep(60)
            
    async def check_expired_actions(self):
        """Check for and remove expired mutes and warns."""
        current_time = datetime.datetime.now().timestamp()
        
        # Check mutes
        expired_mutes = []
        for user_id, mute_data in self.active_mutes.items():
            if mute_data.get('expiry') and mute_data['expiry'] <= current_time:
                expired_mutes.append(user_id)
        
        # Remove expired mutes
        for user_id in expired_mutes:
            await self.unmute_user(user_id)
        
        # Check warns
        expired_warns = []
        for user_id, warns_data in self.active_warns.items():
            expired_for_user = []
            for warn_id, warn_data in warns_data.items():
                if warn_data.get('expiry') and warn_data['expiry'] <= current_time:
                    expired_for_user.append(warn_id)
            
            if expired_for_user:
                new_warns = {k: v for k, v in warns_data.items() if k not in expired_for_user}
                if new_warns:
                    self.active_warns[user_id] = new_warns
                else:
                    expired_warns.append(user_id)
        
        # Remove users with no active warns
        for user_id in expired_warns:
            if user_id in self.active_warns:
                del self.active_warns[user_id]
        
        # Save changes if any actions expired
        if expired_mutes or expired_warns:
            self.save_active_moderation_actions()
    
    # Function no longer needed as we have this logic in check_expired_actions_loop
    
    async def unmute_user(self, user_id):
        """Remove a mute from a user."""
        try:
            user_id = str(user_id)
            if user_id not in self.active_mutes:
                return
            
            # Get the guild and user
            guild_id = self.active_mutes[user_id].get('guild_id')
            if not guild_id:
                del self.active_mutes[user_id]
                self.save_active_moderation_actions()
                return
            
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                del self.active_mutes[user_id]
                self.save_active_moderation_actions()
                return
            
            member = guild.get_member(int(user_id))
            if not member:
                del self.active_mutes[user_id]
                self.save_active_moderation_actions()
                return
            
            # Remove the muted role
            muted_role_id = self.active_mutes[user_id].get('role_id')
            if muted_role_id:
                role = guild.get_role(int(muted_role_id))
                if role and role in member.roles:
                    await member.remove_roles(role, reason="Mute duration expired")
            
            # Log the unmute
            log_channel_id = self.log_channel_id
            if log_channel_id:
                channel = self.bot.get_channel(int(log_channel_id))
                if channel:
                    embed = discord.Embed(
                        title="Unmute Action",
                        description=f"{member.mention} ({member.name}) has been automatically unmuted",
                        color=discord.Color.green(),
                        timestamp=datetime.datetime.now()
                    )
                    embed.add_field(name="Reason", value="Mute duration expired", inline=False)
                    embed.set_footer(text=f"User ID: {member.id}")
                    await channel.send(embed=embed)
            
            # Try to DM the user
            try:
                await member.send(f"You have been automatically unmuted in {guild.name}. Your mute duration has expired.")
            except:
                pass
            
            # Remove the mute from active mutes
            del self.active_mutes[user_id]
            self.save_active_moderation_actions()
        except Exception as e:
            self.logger.error(f"Failed to unmute user {user_id}: {e}")
    
    @app_commands.command(name="ban", description="Ban a user from the server")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, user: discord.User, reason: str, duration: str = "permanent"):
        """Ban a user from the server.
        
        Args:
            interaction: The interaction that triggered this command
            user: The user to ban
            reason: The reason for the ban
            duration: The duration of the ban (e.g. 1d, 2h, 30m, permanent)
        """
        # Check if we can ban this user
        if not interaction.guild.me.guild_permissions.ban_members:
            await interaction.response.send_message("I don't have permission to ban members.", ephemeral=True)
            return
        
        # Check if the target is a member of the guild
        member = interaction.guild.get_member(user.id)
        if member:
            # Check if the bot can ban this member (hierarchy check)
            if interaction.guild.me.top_role <= member.top_role:
                await interaction.response.send_message(
                    "I cannot ban this user as their highest role is above or equal to mine.",
                    ephemeral=True
                )
                return
            
            # Check if the command user can ban this member (hierarchy check)
            if interaction.user.top_role <= member.top_role:
                await interaction.response.send_message(
                    "You cannot ban this user as their highest role is above or equal to yours.",
                    ephemeral=True
                )
                return
        
        # Parse the duration
        duration_seconds = self.parse_duration(duration)
        duration_text = self.format_duration(duration_seconds)
        
        # DM the user before banning
        dm_sent = await self.dm_user(
            user, 
            "ban", 
            reason, 
            duration_text,
            interaction.guild.name
        )
        
        try:
            # Perform the ban
            await interaction.guild.ban(
                user, 
                reason=f"Banned by {interaction.user.name}: {reason}",
                delete_message_days=1
            )
            
            # Log the ban
            await self.log_moderation_action(
                "Ban",
                interaction.user,
                user,
                reason,
                duration_text
            )
            
            # Send confirmation
            await interaction.response.send_message(
                f"{user.mention} has been banned.\nReason: {reason}\nDuration: {duration_text}\nDM Notification: {'Sent' if dm_sent else 'Failed'}", 
                ephemeral=True
            )
            
            # If temporary ban, schedule unban
            if duration_seconds is not None:
                # Schedule an unban after the duration
                async def unban_later():
                    await asyncio.sleep(duration_seconds)
                    try:
                        await interaction.guild.unban(user, reason=f"Temporary ban duration expired ({duration_text})")
                        # Log the unban
                        if self.log_channel_id:
                            channel = self.bot.get_channel(int(self.log_channel_id))
                            if channel:
                                embed = discord.Embed(
                                    title="Unban Action",
                                    description=f"{user.mention} ({user.name}) has been automatically unbanned",
                                    color=discord.Color.green(),
                                    timestamp=datetime.datetime.now()
                                )
                                embed.add_field(name="Reason", value="Temporary ban duration expired", inline=False)
                                embed.set_footer(text=f"User ID: {user.id}")
                                await channel.send(embed=embed)
                    except Exception as e:
                        self.logger.error(f"Failed to unban user {user.id}: {e}")
                
                # Start the task to unban later
                self.bot.loop.create_task(unban_later())
        
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to ban that user.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"Failed to ban user: {e}", ephemeral=True)
    
    @app_commands.command(name="kick", description="Kick a user from the server")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        """Kick a user from the server.
        
        Args:
            interaction: The interaction that triggered this command
            user: The user to kick
            reason: The reason for the kick
        """
        await interaction.response.defer(ephemeral=True)
        
        # Check if we can kick this user
        if not interaction.guild.me.guild_permissions.kick_members:
            await interaction.followup.send("I don't have permission to kick members.", ephemeral=True)
            return
        
        # Check if the bot can kick this member (hierarchy check)
        if interaction.guild.me.top_role <= user.top_role:
            await interaction.followup.send(
                "I cannot kick this user as their highest role is above or equal to mine.",
                ephemeral=True
            )
            return
        
        # Check if the command user can kick this member (hierarchy check)
        if interaction.user.top_role <= user.top_role:
            await interaction.followup.send(
                "You cannot kick this user as their highest role is above or equal to yours.",
                ephemeral=True
            )
            return
        
        # Update the user's profile standing
        try:
            # Import ProfileManager to update standing
            from profile_system import ProfileManager
            profile_manager = ProfileManager(self.bot)
            
            # Set standing to "Kicked"
            profile_manager.set_standing_level(str(user.id), "Kicked")
        except Exception as e:
            self.logger.error(f"Failed to update user standing for kick: {e}")
        
        # DM the user before kicking
        dm_sent = await self.dm_user(
            user, 
            "kick", 
            reason,
            guild_name=interaction.guild.name
        )
        
        try:
            # Perform the kick
            await user.kick(reason=f"Kicked by {interaction.user.name}: {reason}")
            
            # Log the kick
            await self.log_moderation_action(
                "Kick",
                interaction.user,
                user,
                reason
            )
            
            # Send confirmation
            await interaction.followup.send(
                f"{user.mention} has been kicked.\nReason: {reason}\nDM Notification: {'Sent' if dm_sent else 'Failed'}\nProfile standing updated to 'Kicked'", 
                ephemeral=True
            )
        
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to kick that user.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"Failed to kick user: {e}", ephemeral=True)
    
    @app_commands.command(name="mute", description="Mute a user in the server using timeout")
    @app_commands.default_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, user: discord.Member, duration: str, reason: str):
        """Mute a user in the server by applying a timeout.
        
        Args:
            interaction: The interaction that triggered this command
            user: The user to mute
            duration: The duration of the mute (e.g. 1d, 2h, 30m)
            reason: The reason for the mute
        """
        await interaction.response.defer(ephemeral=True)
        
        # Check if the bot can timeout this member (permission check)
        if not interaction.guild.me.guild_permissions.moderate_members:
            await interaction.followup.send("I don't have permission to timeout members.", ephemeral=True)
            return
        
        # Check if the bot can mute this member (hierarchy check)
        if interaction.guild.me.top_role <= user.top_role:
            await interaction.followup.send(
                "I cannot mute this user as their highest role is above or equal to mine.",
                ephemeral=True
            )
            return
        
        # Check if the command user can mute this member (hierarchy check)
        if interaction.user.top_role <= user.top_role:
            await interaction.followup.send(
                "You cannot mute this user as their highest role is above or equal to yours.",
                ephemeral=True
            )
            return
        
        # Update the user's profile standing
        try:
            # Import ProfileManager to update standing
            from profile_system import ProfileManager
            profile_manager = ProfileManager(self.bot)
            
            # Get user ID as string
            user_id = str(user.id)
            
            # Log current standing before changes
            current_standing = profile_manager.get_standing_level(user_id)
            self.logger.info(f"Current standing for user {user_id} before mute: {current_standing}")
            
            # Set standing to "Muted"
            self.logger.info(f"Setting standing for user {user_id} to Muted")
            profile_manager.set_standing_level(user_id, "Muted")
            
            # Verify it was updated
            updated_standing = profile_manager.get_standing_level(user_id)
            self.logger.info(f"Updated standing for user {user_id}: {updated_standing}")
        except Exception as e:
            self.logger.error(f"Failed to update user standing for mute: {e}")
        
        # Get or create the muted role
        muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
        if not muted_role:
            try:
                # Create muted role
                muted_role = await interaction.guild.create_role(
                    name="Muted",
                    reason="Creating muted role for moderation"
                )
                
                # Set permissions for the muted role in all text channels
                for channel in interaction.guild.channels:
                    if isinstance(channel, discord.TextChannel):
                        await channel.set_permissions(
                            muted_role,
                            send_messages=False,
                            add_reactions=False
                        )
                    elif isinstance(channel, discord.VoiceChannel):
                        await channel.set_permissions(
                            muted_role,
                            speak=False
                        )
            except Exception as e:
                await interaction.followup.send(
                    f"Failed to create or configure the Muted role: {e}",
                    ephemeral=True
                )
                return
        
        # Parse the duration
        duration_seconds = self.parse_duration(duration)
        if duration_seconds is None:
            # Discord's timeout has a maximum of 28 days
            duration_seconds = 28 * 86400  # 28 days in seconds
        
        duration_text = self.format_duration(duration_seconds)
        
        # Convert seconds to timedelta for Discord timeout
        timedelta_duration = datetime.timedelta(seconds=duration_seconds)
        timeout_until = datetime.datetime.now() + timedelta_duration
        
        # First try to use Discord's timeout feature
        timeout_success = False
        timeout_error = None
        
        try:
            self.logger.info(f"Attempting to apply Discord timeout to user {user.id} until {timeout_until}")
            
            # Check if user is already timed out
            if user.is_timed_out():
                await interaction.followup.send(
                    f"{user.mention} is already timed out. To adjust the timeout, you must wait for it to expire.",
                    ephemeral=True
                )
                return
                
            # Apply timeout - Discord.py expects timeout as positional arg
            await user.timeout(
                timeout_until,
                reason=f"Muted by {interaction.user.name}: {reason}"
            )
            
            # If we got here, timeout was successful
            timeout_success = True
            self.logger.info(f"Successfully applied Discord timeout to user {user.id}")
        except Exception as e:
            timeout_error = str(e)
            self.logger.error(f"Failed to apply Discord timeout: {e}", exc_info=True)
            # We'll fall back to role-based mute
        
        # If timeout failed, check if we need to use role-based approach
        if not timeout_success:
            self.logger.info(f"Falling back to role-based mute for user {user.id}")
            
            # Check if the user is already muted with the role
            if muted_role in user.roles:
                await interaction.followup.send(
                    f"{user.mention} is already muted with the Muted role. To adjust the mute, you must unmute them first.",
                    ephemeral=True
                )
                return
            
            try:
                # Apply the muted role
                await user.add_roles(muted_role, reason=f"Muted by {interaction.user.name}: {reason}")
            except Exception as e:
                await interaction.followup.send(
                    f"Failed to mute user with both timeout and role methods. Error: {e}",
                    ephemeral=True
                )
                return
        
        # DM the user about the mute
        dm_sent = await self.dm_user(
            user, 
            "mute", 
            reason, 
            duration_text,
            interaction.guild.name
        )
        
        # Calculate expiry timestamp
        expiry = self.calculate_expiry(duration_seconds)
        
        # Store the mute information
        self.active_mutes[str(user.id)] = {
            'guild_id': str(interaction.guild.id),
            'role_id': None if timeout_success else str(muted_role.id),
            'moderator_id': str(interaction.user.id),
            'reason': reason,
            'expiry': expiry,
            'duration': duration_text,
            'is_timeout': timeout_success
        }
        
        # Save active mutes
        self.save_active_moderation_actions()
        
        # Log the mute
        await self.log_moderation_action(
            "Timeout" if timeout_success else "Mute",
            interaction.user,
            user,
            reason,
            duration_text
        )
        
        # Send confirmation
        mute_method = "Discord's timeout feature" if timeout_success else "the Muted role"
        await interaction.followup.send(
            f"{user.mention} has been muted using {mute_method}.\nReason: {reason}\nDuration: {duration_text}\nDM Notification: {'Sent' if dm_sent else 'Failed'}\nProfile standing updated to 'Muted'", 
            ephemeral=True
        )
        
        # If timeout failed but we want to let the mod know why
        if not timeout_success and timeout_error:
            await interaction.followup.send(
                f"Note: Discord timeout couldn't be applied (error: {timeout_error}), so a role-based mute was used instead.",
                ephemeral=True
            )
    
    @app_commands.command(name="unmute", description="Unmute a user in the server")
    @app_commands.default_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Manually unmuted"):
        """Unmute a user in the server.
        
        Args:
            interaction: The interaction that triggered this command
            user: The user to unmute
            reason: The reason for the unmute
        """
        await interaction.response.defer(ephemeral=True)
        
        # Check permissions
        if not interaction.guild.me.guild_permissions.moderate_members:
            await interaction.followup.send("I don't have permission to moderate members.", ephemeral=True)
            return
            
        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.followup.send("I don't have permission to manage roles.", ephemeral=True)
            return
        
        # Get user ID as string
        user_id = str(user.id)
        
        # Check if the user is timed out (Discord timeout)
        timeout_removed = False
        if user.is_timed_out():
            try:
                # Remove timeout by setting it to None - fix positional arg
                await user.timeout(
                    None,  # Positional argument instead of keyword
                    reason=f"Timeout removed by {interaction.user.name}: {reason}"
                )
                timeout_removed = True
                self.logger.info(f"Removed timeout for user {user_id}")
            except Exception as e:
                self.logger.error(f"Failed to remove timeout: {e}", exc_info=True)
                await interaction.followup.send(f"Failed to remove timeout: {e}", ephemeral=True)
        
        # Check for role-based mute
        role_mute_removed = False
        muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
        if muted_role and muted_role in user.roles:
            try:
                # Remove the muted role
                await user.remove_roles(muted_role, reason=f"Unmuted by {interaction.user.name}: {reason}")
                role_mute_removed = True
                self.logger.info(f"Removed muted role from user {user_id}")
            except Exception as e:
                self.logger.error(f"Failed to remove muted role: {e}", exc_info=True)
                if not timeout_removed:
                    await interaction.followup.send(f"Failed to remove muted role: {e}", ephemeral=True)
        
        # If neither type of mute was removed
        if not timeout_removed and not role_mute_removed:
            await interaction.followup.send(f"{user.mention} is not muted or timed out.", ephemeral=True)
            return
        
        # Update the user's profile standing
        try:
            # Import ProfileManager to update standing
            from profile_system import ProfileManager
            profile_manager = ProfileManager(self.bot)
            
            # Log current standing before changes
            current_standing = profile_manager.get_standing_level(user_id)
            self.logger.info(f"Current standing for user {user_id} before unmute: {current_standing}")
            
            # Reset standing to "Clear" if it was negative
            if current_standing in ["Muted", "Flagged", "Monitored", "Warned"]:
                self.logger.info(f"Resetting standing for user {user_id} to Clear after unmute")
                profile_manager.set_standing_level(user_id, "Clear")
                
                # Verify it was updated
                updated_standing = profile_manager.get_standing_level(user_id)
                self.logger.info(f"Updated standing for user {user_id}: {updated_standing}")
        except Exception as e:
            self.logger.error(f"Failed to update user standing for unmute: {e}", exc_info=True)
        
        # Remove from active mutes
        if user_id in self.active_mutes:
            del self.active_mutes[user_id]
            self.save_active_moderation_actions()
        
        # Log the unmute
        await self.log_moderation_action(
            "Unmute",
            interaction.user,
            user,
            reason
        )
        
        # Try to DM the user
        dm_sent = False
        try:
            await user.send(f"You have been unmuted in {interaction.guild.name}.\nReason: {reason}")
            dm_sent = True
        except:
            pass
        
        # Send confirmation based on what was removed
        unmute_type = ""
        if timeout_removed and role_mute_removed:
            unmute_type = "timeout and muted role"
        elif timeout_removed:
            unmute_type = "timeout"
        else:
            unmute_type = "muted role"
            
        await interaction.followup.send(
            f"{user.mention} has been unmuted ({unmute_type} removed).\nReason: {reason}\nDM Notification: {'Sent' if dm_sent else 'Failed'}\nProfile standing reset to 'Clear'", 
            ephemeral=True
        )
    
    @app_commands.command(name="warn", description="Warn a user in the server")
    @app_commands.default_permissions(manage_messages=True)
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str, duration: str = "30d"):
        """Warn a user in the server.
        
        Args:
            interaction: The interaction that triggered this command
            user: The user to warn
            reason: The reason for the warning
            duration: How long the warning stays on record (e.g. 30d)
        """
        await interaction.response.defer(ephemeral=True)
        
        # Parse the duration
        duration_seconds = self.parse_duration(duration)
        duration_text = self.format_duration(duration_seconds)
        
        # Calculate expiry timestamp
        expiry = self.calculate_expiry(duration_seconds)
        
        # Generate a unique warn ID
        warn_id = f"{datetime.datetime.now().timestamp()}"
        
        # Create or update the user's warnings
        user_id = str(user.id)
        if user_id not in self.active_warns:
            self.active_warns[user_id] = {}
        
        # Add the new warning
        self.active_warns[user_id][warn_id] = {
            'guild_id': str(interaction.guild.id),
            'moderator_id': str(interaction.user.id),
            'reason': reason,
            'timestamp': datetime.datetime.now().timestamp(),
            'expiry': expiry,
            'duration': duration_text
        }
        
        # Save active warnings
        self.save_active_moderation_actions()
        
        # Count the user's active warnings
        warning_count = len(self.active_warns[user_id])
        
        # Update user's profile standing based on warning count
        try:
            # Import ProfileManager to update standing
            from profile_system import ProfileManager
            profile_manager = ProfileManager(self.bot)
            
            # Log current standing before changes
            current_standing = profile_manager.get_standing_level(user_id)
            self.logger.info(f"Current standing for user {user_id} before warning: {current_standing}")
            
            # Update standing based on warning count
            new_standing = None
            if warning_count >= 4:
                new_standing = "Warned"
            elif warning_count >= 3:
                new_standing = "Monitored"
            elif warning_count >= 2:
                new_standing = "Flagged"
                
            # Only update if we're setting a new standing level
            if new_standing:
                self.logger.info(f"Setting standing for user {user_id} from {current_standing} to {new_standing}")
                profile_manager.set_standing_level(user_id, new_standing)
                
                # Let's verify it was updated
                updated_standing = profile_manager.get_standing_level(user_id)
                self.logger.info(f"Updated standing for user {user_id}: {updated_standing}")
        except Exception as e:
            self.logger.error(f"Failed to update user standing: {e}", exc_info=True)
        
        # Automatic punishments based on warning count
        applied_punishment = None
        
        if warning_count >= 4:
            # 4+ warnings = ban
            try:
                await interaction.guild.ban(
                    user, 
                    reason=f"Automatic ban after 4 warnings. Last warning by {interaction.user.name}: {reason}",
                    delete_message_days=1
                )
                applied_punishment = "🔨 User has been automatically **banned** for reaching 4 warnings"
                
                # Log the automatic ban
                await self.log_moderation_action(
                    "Ban (Automatic)",
                    interaction.guild.me,  # Bot as the moderator for automatic action
                    user,
                    f"Automatic ban after reaching 4 warnings. Last warning reason: {reason}"
                )
            except Exception as e:
                self.logger.error(f"Failed to auto-ban user after 4 warnings: {e}")
                applied_punishment = "⚠️ Attempted to auto-ban for 4 warnings but failed: " + str(e)
                
        elif warning_count >= 3:
            # 3 warnings = 1 day mute
            try:
                self.logger.info(f"Applying automatic 1-day timeout to user {user_id} after 3 warnings")
                
                # First try using Discord's timeout feature (preferred method)
                timeout_success = False
                try:
                    # Calculate the timeout end time (1 day from now)
                    one_day = datetime.timedelta(days=1)
                    timeout_until = datetime.datetime.now() + one_day
                    
                    # Apply the timeout - fix for positional argument
                    self.logger.info(f"Attempting to apply Discord timeout to user {user_id} until {timeout_until}")
                    await user.timeout(
                        timeout_until, 
                        reason=f"Automatic timeout after 3 warnings. Last warning by {interaction.user.name}: {reason}"
                    )
                    
                    # If we get here, the timeout was applied successfully
                    timeout_success = True
                    self.logger.info(f"Successfully applied Discord timeout to user {user_id}")
                    
                    applied_punishment = "🔇 User has been automatically **timed out for 1 day** for reaching 3 warnings"
                except Exception as e:
                    self.logger.error(f"Failed to apply Discord timeout: {e}", exc_info=True)
                    # We'll fall back to the role-based mute
                
                # If timeout failed, fall back to role-based mute
                if not timeout_success:
                    self.logger.info(f"Falling back to role-based mute for user {user_id}")
                    # Get or create muted role
                    muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
                    if not muted_role:
                        # Create the muted role if it doesn't exist
                        try:
                            muted_role = await interaction.guild.create_role(name="Muted", reason="Auto-created for mute command")
                            
                            # Set permissions for the muted role
                            for channel in interaction.guild.channels:
                                try:
                                    await channel.set_permissions(muted_role, send_messages=False, add_reactions=False, speak=False)
                                except:
                                    continue
                        except Exception as e:
                            self.logger.error(f"Failed to create muted role: {e}")
                            applied_punishment = f"⚠️ Could not create muted role: {e}"
                    
                    if muted_role:
                        # Apply the muted role
                        await user.add_roles(muted_role, reason=f"Automatic mute after 3 warnings. Last warning by {interaction.user.name}: {reason}")
                        
                        # Add to active mutes with 1 day duration
                        one_day_seconds = 86400
                        expiry_time = datetime.datetime.now().timestamp() + one_day_seconds
                        
                        self.active_mutes[user_id] = {
                            'guild_id': str(interaction.guild.id),
                            'role_id': str(muted_role.id),
                            'moderator_id': str(interaction.guild.me.id),
                            'reason': f"Automatic mute after 3 warnings. Last warning: {reason}",
                            'timestamp': datetime.datetime.now().timestamp(),
                            'expiry': expiry_time
                        }
                        
                        self.save_active_moderation_actions()
                        
                        applied_punishment = "🔇 User has been automatically **muted for 1 day** for reaching 3 warnings"
                
                # Set profile standing to "Muted" regardless of the method used
                try:
                    # We already imported ProfileManager at the top of the warning handling
                    self.logger.info(f"Setting standing for user {user_id} to Muted due to automatic mute/timeout")
                    profile_manager.set_standing_level(user_id, "Muted")
                    
                    # Verify it was updated
                    updated_standing = profile_manager.get_standing_level(user_id)
                    self.logger.info(f"Updated standing for user {user_id}: {updated_standing}")
                except Exception as e:
                    self.logger.error(f"Failed to update user standing for auto-mute: {e}", exc_info=True)
                
                # Log the automatic mute
                await self.log_moderation_action(
                    "Mute/Timeout (Automatic)",
                    interaction.guild.me,  # Bot as the moderator for automatic action
                    user,
                    f"Automatic 1-day {'timeout' if timeout_success else 'mute'} after reaching 3 warnings. Last warning reason: {reason}",
                    "1 day"
                )
            except Exception as e:
                self.logger.error(f"Failed to auto-mute/timeout user after 3 warnings: {e}", exc_info=True)
                applied_punishment = "⚠️ Attempted to auto-mute/timeout for 3 warnings but failed: " + str(e)
        
        # DM the user about the warning
        dm_sent = await self.dm_user(
            user, 
            "warn", 
            reason, 
            duration_text,
            interaction.guild.name
        )
        
        # Log the warning
        await self.log_moderation_action(
            "Warning",
            interaction.user,
            user,
            reason,
            duration_text
        )
        
        # Update profile standing in the profile system
        try:
            from profile_system import ProfileManager
            profile_manager = ProfileManager(self.bot)
            # Update infractions count in profile
            profile_manager.update_infraction(str(user.id), "warnings", 1)
            self.logger.info(f"Updated warning count in profile for user {user.id}")
        except Exception as e:
            self.logger.error(f"Failed to update profile standings for warning: {e}", exc_info=True)
            
        # Send confirmation with automatic punishment info if applicable
        response = f"{user.mention} has been warned.\nReason: {reason}\nWarning will expire: {duration_text}\nCurrent Warning Count: {warning_count}\nDM Notification: {'Sent' if dm_sent else 'Failed'}\nProfile standing updated to show warnings."
        
        if applied_punishment:
            response += f"\n\n{applied_punishment}"
            
        await interaction.followup.send(response, ephemeral=True)
    
    @app_commands.command(name="warnings", description="Show warnings for a user")
    @app_commands.default_permissions(manage_messages=True)
    async def warnings(self, interaction: discord.Interaction, user: discord.Member):
        """Show warnings for a user.
        
        Args:
            interaction: The interaction that triggered this command
            user: The user to show warnings for
        """
        user_id = str(user.id)
        
        if user_id not in self.active_warns or not self.active_warns[user_id]:
            await interaction.response.send_message(
                f"{user.mention} has no active warnings.",
                ephemeral=True
            )
            return
        
        # Create an embed to display warnings
        embed = discord.Embed(
            title=f"Warnings for {user.name}",
            description=f"{user.mention} has {len(self.active_warns[user_id])} active warnings.",
            color=discord.Color.gold(),
            timestamp=datetime.datetime.now()
        )
        
        # Add each warning to the embed
        for i, (warn_id, warning) in enumerate(self.active_warns[user_id].items(), 1):
            moderator = interaction.guild.get_member(int(warning.get('moderator_id', 0)))
            moderator_name = moderator.name if moderator else "Unknown Moderator"
            
            timestamp_str = datetime.datetime.fromtimestamp(warning.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S')
            
            warning_text = f"**Reason:** {warning.get('reason', 'No reason provided')}\n"
            warning_text += f"**Moderator:** {moderator_name}\n"
            warning_text += f"**Date:** {timestamp_str}\n"
            
            if warning.get('expiry'):
                expiry_str = datetime.datetime.fromtimestamp(warning['expiry']).strftime('%Y-%m-%d %H:%M:%S')
                warning_text += f"**Expires:** {expiry_str}\n"
            else:
                warning_text += "**Expires:** Never\n"
            
            embed.add_field(name=f"Warning #{i}", value=warning_text, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="clearwarnings", description="Clear all warnings for a user")
    @app_commands.default_permissions(administrator=True)
    async def clearwarnings(self, interaction: discord.Interaction, user: discord.Member):
        """Clear all warnings for a user.
        
        Args:
            interaction: The interaction that triggered this command
            user: The user to clear warnings for
        """
        await interaction.response.defer(ephemeral=True)
        
        user_id = str(user.id)
        
        if user_id not in self.active_warns or not self.active_warns[user_id]:
            await interaction.followup.send(
                f"{user.mention} has no active warnings to clear.",
                ephemeral=True
            )
            return
        
        # Count how many warnings were cleared
        warning_count = len(self.active_warns[user_id])
        
        # Clear the warnings
        del self.active_warns[user_id]
        self.save_active_moderation_actions()
        
        # Reset the user's profile standing and infractions in profile system
        try:
            # Import ProfileManager to update standing
            from profile_system import ProfileManager
            profile_manager = ProfileManager(self.bot)
            
            # Reset the warning count to 0 in the profile system
            profile_manager.set_infraction_count(user_id, "warnings", 0)
            self.logger.info(f"Reset warning count to 0 in profile for user {user_id}")
            
            # Reset standing to "Clear" since all warnings are cleared
            current_standing = profile_manager.get_standing_level(user_id)
            self.logger.info(f"Current standing for user {user_id} before clearwarnings: {current_standing}")
            
            # Always set to Clear when warnings are cleared
            self.logger.info(f"Resetting standing for user {user_id} to Clear")
            profile_manager.set_standing_level(user_id, "Clear")
            
            # Verify it was updated
            updated_standing = profile_manager.get_standing_level(user_id)
            self.logger.info(f"Updated standing for user {user_id}: {updated_standing}")
        except Exception as e:
            self.logger.error(f"Failed to update user standing for clearwarnings: {e}", exc_info=True)
        
        # Log the action
        await self.log_moderation_action(
            "Clear Warnings",
            interaction.user,
            user,
            f"Cleared {warning_count} warnings"
        )
        
        # Send confirmation
        await interaction.followup.send(
            f"Cleared {warning_count} warnings for {user.mention}.\nProfile standing has been reset to 'Clear'.",
            ephemeral=True
        )
    
    # purge command removed
    
    @app_commands.command(name="channellock", description="Lock a channel to prevent users from sending messages")
    @app_commands.default_permissions(manage_channels=True)
    async def channellock(self, interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = "No reason provided"):
        """Lock a channel to prevent users from sending messages.
        
        Args:
            interaction: The interaction that triggered this command
            channel: The channel to lock (defaults to current channel)
            reason: The reason for locking the channel
        """
        # Use the current channel if none specified
        if not channel:
            channel = interaction.channel
        
        # Check permissions
        if not interaction.guild.me.guild_permissions.manage_channels:
            await interaction.response.send_message("I don't have permission to manage channels.", ephemeral=True)
            return
        
        try:
            # Get the default role (@everyone)
            default_role = interaction.guild.default_role
            
            # Update permissions to deny sending messages
            await channel.set_permissions(
                default_role,
                send_messages=False,
                reason=f"Channel locked by {interaction.user.name}: {reason}"
            )
            
            # Send confirmation
            await interaction.response.send_message(f"🔒 {channel.mention} has been locked.", ephemeral=True)
            
            # Send a message in the locked channel
            await channel.send(f"🔒 This channel has been locked by {interaction.user.mention}.\nReason: {reason}")
            
            # Log the action
            await self.log_moderation_action(
                "Channel Lock",
                interaction.user,
                None,
                f"Locked {channel.mention}: {reason}"
            )
        
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to lock that channel.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"Failed to lock channel: {e}", ephemeral=True)
    
    @app_commands.command(name="channelunlock", description="Unlock a previously locked channel")
    @app_commands.default_permissions(manage_channels=True)
    async def channelunlock(self, interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = "No reason provided"):
        """Unlock a previously locked channel.
        
        Args:
            interaction: The interaction that triggered this command
            channel: The channel to unlock (defaults to current channel)
            reason: The reason for unlocking the channel
        """
        # Use the current channel if none specified
        if not channel:
            channel = interaction.channel
        
        # Check permissions
        if not interaction.guild.me.guild_permissions.manage_channels:
            await interaction.response.send_message("I don't have permission to manage channels.", ephemeral=True)
            return
        
        try:
            # Get the default role (@everyone)
            default_role = interaction.guild.default_role
            
            # Update permissions to allow sending messages
            await channel.set_permissions(
                default_role,
                send_messages=None,  # Reset to default
                reason=f"Channel unlocked by {interaction.user.name}: {reason}"
            )
            
            # Send confirmation
            await interaction.response.send_message(f"🔓 {channel.mention} has been unlocked.", ephemeral=True)
            
            # Send a message in the unlocked channel
            await channel.send(f"🔓 This channel has been unlocked by {interaction.user.mention}.\nReason: {reason}")
            
            # Log the action
            await self.log_moderation_action(
                "Channel Unlock",
                interaction.user,
                None,
                f"Unlocked {channel.mention}: {reason}"
            )
        
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to unlock that channel.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"Failed to unlock channel: {e}", ephemeral=True)
    
    @app_commands.command(name="setlogchannel", description="Set the channel for moderation logs (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the channel for moderation logs.
        
        Args:
            interaction: The interaction that triggered this command
            channel: The channel to set as the log channel
        """
        self.log_channel_id = channel.id
        self.save_settings()
        
        await interaction.response.send_message(
            f"Moderation log channel set to {channel.mention}.",
            ephemeral=True
        )
    
    @app_commands.command(name="givepermission", description="Give a role permission to use moderation commands (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def give_permission(self, interaction: discord.Interaction, role: discord.Role, permission_level: str):
        """Give a role permission to use moderation commands.
        
        Args:
            interaction: The interaction that triggered this command
            role: The role to give permission to
            permission_level: The permission level (helper, mod, admin)
        """
        # Validate permission level
        valid_levels = ["helper", "mod", "admin"]
        if permission_level.lower() not in valid_levels:
            await interaction.response.send_message(
                f"Invalid permission level. Choose from: {', '.join(valid_levels)}",
                ephemeral=True
            )
            return
        
        # Update permissions in settings.json
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
            
            # Initialize the roles dictionary if it doesn't exist
            if 'permission_roles' not in settings:
                settings['permission_roles'] = {}
            
            # Initialize the permission level array if it doesn't exist
            if permission_level not in settings['permission_roles']:
                settings['permission_roles'][permission_level] = []
            
            # Add the role ID if it's not already in the list
            role_id = str(role.id)
            if role_id not in settings['permission_roles'][permission_level]:
                settings['permission_roles'][permission_level].append(role_id)
            
            # Save the updated settings
            with open('settings.json', 'w') as f:
                json.dump(settings, f, indent=4)
            
            await interaction.response.send_message(
                f"The role {role.mention} has been given {permission_level} permissions.",
                ephemeral=True
            )
        except Exception as e:
            self.logger.error(f"Failed to update permission roles: {e}")
            await interaction.response.send_message(
                f"Failed to update permission roles: {e}",
                ephemeral=True
            )


async def setup(bot):
    """Add the moderation cog to the bot."""
    moderation_cog = ModerationCog(bot)
    await bot.add_cog(moderation_cog)
    return moderation_cog