import discord
from discord import app_commands
from discord.ext import commands
import json
import datetime
import logging
import os
import asyncio
from permissions import get_valid_roles

logger = logging.getLogger(__name__)

# Constants for moderation actions
MUTE_OPTIONS = [
    ("5 Minutes", 5),
    ("15 Minutes", 15),
    ("30 Minutes", 30),
    ("1 Hour", 60),
    ("3 Hours", 180),
    ("6 Hours", 360),
    ("12 Hours", 720),
    ("1 Day", 1440),
    ("3 Days", 4320),
    ("1 Week", 10080)
]

class ActionDropdown(discord.ui.Select):
    """Dropdown for selecting moderation actions"""
    
    def __init__(self, report_cog, report_id, reported_user_id):
        self.report_cog = report_cog
        self.report_id = report_id
        self.reported_user_id = reported_user_id
        
        options = [
            discord.SelectOption(label="Warn User", value="warn", emoji="⚠️", description="Send a warning to the user"),
            discord.SelectOption(label="Mute User", value="mute", emoji="🔇", description="Temporarily mute the user"),
            discord.SelectOption(label="Kick User", value="kick", emoji="👢", description="Remove the user from the server")
        ]
        
        super().__init__(placeholder="Select action to take...", min_values=1, max_values=1, options=options)
        
    async def callback(self, interaction: discord.Interaction):
        action = self.values[0]
        
        if action == "warn":
            # Create modal for warning
            await interaction.response.send_modal(WarningModal(self.report_cog, self.report_id, self.reported_user_id))
        
        elif action == "mute":
            # Create view with mute durations
            view = MuteDurationView(self.report_cog, self.report_id, self.reported_user_id)
            await interaction.response.send_message("Select mute duration:", view=view, ephemeral=True)
        
        elif action == "kick":
            # Create modal for kick reason
            await interaction.response.send_modal(KickModal(self.report_cog, self.report_id, self.reported_user_id))

class WarningModal(discord.ui.Modal, title="Send Warning"):
    """Modal for sending a warning to a user"""
    
    warning_text = discord.ui.TextInput(
        label="Warning Message",
        placeholder="Enter the warning message to send to the user",
        required=True,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, report_cog, report_id, reported_user_id):
        super().__init__()
        self.report_cog = report_cog
        self.report_id = report_id
        self.reported_user_id = reported_user_id
    
    async def on_submit(self, interaction: discord.Interaction):
        warning = self.warning_text.value
        
        try:
            # Get the user from the ID
            user = await interaction.client.fetch_user(int(self.reported_user_id))
            
            # Send warning to user
            try:
                warning_embed = discord.Embed(
                    title="⚠️ Warning from Moderators",
                    description=warning,
                    color=discord.Color.yellow()
                )
                warning_embed.set_footer(text=f"Server: {interaction.guild.name}")
                
                await user.send(embed=warning_embed)
                dm_sent = True
            except:
                dm_sent = False
            
            # Update report status
            self.report_cog.update_report_status(
                self.report_id, 
                "resolved", 
                f"Warning issued by {interaction.user.name} ({interaction.user.id})",
                {"action": "warn", "warning": warning, "dm_sent": dm_sent}
            )
            
            # Inform moderator
            await interaction.response.send_message(
                f"✅ Warning sent to {user.name}. " + ("" if dm_sent else "Note: User has DMs disabled, they did not receive the warning message."),
                ephemeral=True
            )
            
            # Update the original report message
            await self.report_cog.update_report_message(self.report_id, interaction.user)
            
        except Exception as e:
            logger.error(f"Error sending warning: {e}", exc_info=True)
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class KickModal(discord.ui.Modal, title="Kick User"):
    """Modal for kicking a user"""
    
    kick_reason = discord.ui.TextInput(
        label="Kick Reason",
        placeholder="Enter the reason for kicking this user",
        required=True,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, report_cog, report_id, reported_user_id):
        super().__init__()
        self.report_cog = report_cog
        self.report_id = report_id
        self.reported_user_id = reported_user_id
    
    async def on_submit(self, interaction: discord.Interaction):
        reason = self.kick_reason.value
        
        try:
            # Get the member from the ID
            member = interaction.guild.get_member(int(self.reported_user_id))
            
            if not member:
                await interaction.response.send_message("❌ User is no longer in the server", ephemeral=True)
                return
            
            # Send notification to user before kicking
            try:
                kick_embed = discord.Embed(
                    title="👢 You've Been Kicked",
                    description=f"You have been kicked from {interaction.guild.name}.\n\n**Reason:** {reason}",
                    color=discord.Color.orange()
                )
                await member.send(embed=kick_embed)
            except:
                pass  # DMs disabled
            
            # Kick the user
            await member.kick(reason=f"Kicked by {interaction.user.name}: {reason}")
            
            # Update report status
            self.report_cog.update_report_status(
                self.report_id, 
                "resolved", 
                f"User kicked by {interaction.user.name} ({interaction.user.id})",
                {"action": "kick", "reason": reason}
            )
            
            # Inform moderator
            await interaction.response.send_message(f"✅ {member.name} has been kicked from the server.", ephemeral=True)
            
            # Update the original report message
            await self.report_cog.update_report_message(self.report_id, interaction.user)
            
        except Exception as e:
            logger.error(f"Error kicking user: {e}", exc_info=True)
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class MuteDurationView(discord.ui.View):
    """View for selecting mute duration"""
    
    def __init__(self, report_cog, report_id, reported_user_id):
        super().__init__()
        self.report_cog = report_cog
        self.report_id = report_id
        self.reported_user_id = reported_user_id
        
        # Add buttons for each mute duration
        for label, minutes in MUTE_OPTIONS:
            self.add_item(MuteDurationButton(label, minutes))
    
class MuteDurationButton(discord.ui.Button):
    """Button for selecting a mute duration"""
    
    def __init__(self, label, minutes):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.minutes = minutes
    
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        report_cog = view.report_cog
        report_id = view.report_id
        reported_user_id = view.reported_user_id
        
        try:
            # Get the member from the ID
            member = interaction.guild.get_member(int(reported_user_id))
            
            if not member:
                await interaction.response.send_message("❌ User is no longer in the server", ephemeral=True)
                return
            
            # Find timeout role or use Discord's timeout feature
            timed_out_until = datetime.datetime.now() + datetime.timedelta(minutes=self.minutes)
            
            try:
                # Use Discord timeout feature
                await member.timeout(until=timed_out_until, reason=f"Timed out by {interaction.user.name} via report system")
                timeout_success = True
            except:
                timeout_success = False
            
            # Send notification to user 
            try:
                mute_embed = discord.Embed(
                    title="🔇 You've Been Muted",
                    description=f"You have been muted in {interaction.guild.name} for {self.label}.\n\nYour ability to send messages, react, join voice channels, and speak in voice channels has been temporarily revoked.",
                    color=discord.Color.orange()
                )
                mute_embed.add_field(
                    name="Duration", 
                    value=self.label,
                    inline=True
                )
                mute_embed.add_field(
                    name="Expires", 
                    value=f"<t:{int(timed_out_until.timestamp())}:R>",
                    inline=True
                )
                
                await member.send(embed=mute_embed)
            except:
                pass  # DMs disabled
            
            # Update report status
            report_cog.update_report_status(
                report_id, 
                "resolved", 
                f"User muted by {interaction.user.name} ({interaction.user.id}) for {self.label}",
                {"action": "mute", "duration_minutes": self.minutes, "timeout_success": timeout_success}
            )
            
            # Inform moderator
            await interaction.response.send_message(
                f"✅ {member.name} has been muted for {self.label}." + 
                ("" if timeout_success else " Note: Could not apply Discord timeout. A timeout role might have been used instead."),
                ephemeral=True
            )
            
            # Update the original report message
            await report_cog.update_report_message(report_id, interaction.user)
            
            # Schedule unmute if using a role
            if not timeout_success:
                # Let the moderator know they'll need to manually unmute
                await interaction.followup.send(
                    "⚠️ Discord's timeout feature could not be applied. You may need to manually remove any mute role later.",
                    ephemeral=True
                )
            
        except Exception as e:
            logger.error(f"Error muting user: {e}", exc_info=True)
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class ReportActionView(discord.ui.View):
    """View with buttons for report actions"""
    
    def __init__(self, report_cog, report_id, reported_user_id):
        super().__init__(timeout=None)  # No timeout for these buttons
        self.report_cog = report_cog
        self.report_id = report_id
        self.reported_user_id = reported_user_id
        
        # Add action dropdown
        self.add_item(ActionDropdown(report_cog, report_id, reported_user_id))
        
    @discord.ui.button(label="Ignore Report", style=discord.ButtonStyle.secondary, emoji="🚫", custom_id="ignore_report")
    async def ignore_report(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Ignore the report, marking it as invalid"""
        
        # Check if the user has permission
        user_id = interaction.user.id
        guild_id = interaction.guild_id
        
        has_permission = False
        
        # Get valid roles for using /rank command (same permissions)
        valid_roles = get_valid_roles("rank")
        
        # Check if user has any of the required roles
        if valid_roles == "everyone":
            has_permission = True
        elif valid_roles == "admin_only":
            # Check if user is admin
            member = await interaction.guild.fetch_member(user_id)
            has_permission = member.guild_permissions.administrator
        else:
            # Check if user has any of the required roles
            member = await interaction.guild.fetch_member(user_id)
            for role in member.roles:
                if str(role.id) in valid_roles:
                    has_permission = True
                    break
        
        if not has_permission:
            await interaction.response.send_message("❌ You don't have permission to use this button.", ephemeral=True)
            return
        
        # Update report status
        self.report_cog.update_report_status(
            self.report_id, 
            "rejected", 
            f"Report ignored by {interaction.user.name} ({interaction.user.id})"
        )
        
        # Update the message
        await interaction.response.edit_message(
            content=f"✅ Report #{self.report_id} has been marked as ignored by {interaction.user.mention}",
            view=None,  # Remove the buttons
            embed=interaction.message.embeds[0]  # Keep the original embed
        )
    
    @discord.ui.button(label="Take Action", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="take_action")
    async def take_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Take action against the reported user"""
        
        # Check if the user has permission
        user_id = interaction.user.id
        guild_id = interaction.guild_id
        
        has_permission = False
        
        # Get valid roles for using /rank command (same permissions)
        valid_roles = get_valid_roles("rank")
        
        # Check if user has any of the required roles
        if valid_roles == "everyone":
            has_permission = True
        elif valid_roles == "admin_only":
            # Check if user is admin
            member = await interaction.guild.fetch_member(user_id)
            has_permission = member.guild_permissions.administrator
        else:
            # Check if user has any of the required roles
            member = await interaction.guild.fetch_member(user_id)
            for role in member.roles:
                if str(role.id) in valid_roles:
                    has_permission = True
                    break
        
        if not has_permission:
            await interaction.response.send_message("❌ You don't have permission to use this button.", ephemeral=True)
            return
        
        # Update report status to being reviewed
        self.report_cog.update_report_status(
            self.report_id,
            "reviewing",
            f"Report being reviewed by {interaction.user.name} ({interaction.user.id})"
        )
        
        # Show action options
        await interaction.response.send_message(
            "Select an action to take against the reported user:",
            view=ModerationActionView(self.report_cog, self.report_id, self.reported_user_id),
            ephemeral=True
        )

class ModerationActionView(discord.ui.View):
    """View with options for moderation actions"""
    
    def __init__(self, report_cog, report_id, reported_user_id):
        super().__init__()
        self.report_cog = report_cog
        self.report_id = report_id
        self.reported_user_id = reported_user_id
        
        # Add action dropdown
        self.add_item(ActionDropdown(report_cog, report_id, reported_user_id))

class ReportingCog(commands.Cog):
    """Cog for handling user reports"""
    
    def __init__(self, bot):
        self.bot = bot
        self.report_channel_id = 1356731160704716991  # Channel ID for report logs
        self.reports_file = 'data/reports.json'
        self.reports = self.load_reports()
        logger.info(f"Report channel set to: {self.report_channel_id}")
        
    def load_reports(self):
        """Load reports from JSON file"""
        if not os.path.exists('data'):
            os.makedirs('data')
            
        if os.path.exists(self.reports_file):
            try:
                with open(self.reports_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading reports file: {e}")
                return {'reports': []}
        else:
            return {'reports': []}
        
    def save_reports(self):
        """Save reports to JSON file"""
        try:
            with open(self.reports_file, 'w') as f:
                json.dump(self.reports, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving reports file: {e}")
    
    def get_report_by_id(self, report_id):
        """Get a report by its ID"""
        for report in self.reports['reports']:
            if report['report_id'] == report_id:
                return report
        return None
        
    def update_report_status(self, report_id, status, note=None, action_details=None):
        """Update the status of a report"""
        report = self.get_report_by_id(report_id)
        if report:
            report['status'] = status
            if note:
                report['status_note'] = note
            if action_details:
                report['action_details'] = action_details
            report['updated_at'] = datetime.datetime.now().isoformat()
            self.save_reports()
            return True
        return False
    
    async def update_report_message(self, report_id, moderator=None):
        """Update the original report message to reflect new status"""
        report = self.get_report_by_id(report_id)
        if not report or 'message_id' not in report:
            return False
            
        try:
            # Get the report channel and message
            channel = self.bot.get_channel(self.report_channel_id)
            if not channel:
                return False
                
            try:
                message = await channel.fetch_message(int(report['message_id']))
            except:
                return False
                
            # Update the embed
            embed = message.embeds[0] if message.embeds else None
            if not embed:
                return False
                
            # Add status field or update existing one
            status_text = f"**{report['status'].upper()}**"
            if 'status_note' in report:
                status_text += f"\n{report['status_note']}"
                
            status_field_found = False
            for i, field in enumerate(embed.fields):
                if field.name == "Status":
                    embed.set_field_at(i, name="Status", value=status_text, inline=False)
                    status_field_found = True
                    break
                    
            if not status_field_found:
                embed.add_field(name="Status", value=status_text, inline=False)
                
            # Set new color based on status
            if report['status'] == 'rejected':
                embed.color = discord.Color.light_gray()
            elif report['status'] == 'resolved':
                embed.color = discord.Color.green()
            elif report['status'] == 'reviewing':
                embed.color = discord.Color.gold()
                
            # Update the message
            if report['status'] in ['rejected', 'resolved']:
                # No buttons needed anymore
                await message.edit(content=f"Report handled by {moderator.mention if moderator else 'a moderator'}", embed=embed, view=None)
            else:
                await message.edit(embed=embed)
                
            return True
        except Exception as e:
            logger.error(f"Error updating report message: {e}", exc_info=True)
            return False
    
    @app_commands.command(
        name="report",
        description="🚨 Report a user for breaking rules or inappropriate behavior"
    )
    @app_commands.describe(
        user="The user to report",
        reason="The reason for the report (be specific and include details)",
        image_url="Optional URL to an image/screenshot as proof (must be a direct link to an image)"
    )
    async def report_command(self, interaction: discord.Interaction, user: discord.Member, reason: str, image_url: str = None):
        """Report a user for inappropriate behavior"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Validate image URL if provided
            valid_image = False
            if image_url:
                try:
                    # Basic URL format validation
                    if not image_url.startswith(('http://', 'https://')):
                        await interaction.followup.send(
                            "⚠️ The image URL must start with http:// or https://",
                            ephemeral=True
                        )
                        return
                        
                    # More comprehensive validation for image URLs
                    if image_url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp')):
                        valid_image = True
                    else:
                        # If URL doesn't end with expected extension, check for query strings
                        for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']:
                            if f"{ext}?" in image_url.lower() or f"{ext}&" in image_url.lower():
                                valid_image = True
                                break
                        
                        # Additional check for common image hosting services that might use special URLs
                        image_hosts = ['imgur.com', 'i.imgur.com', 'prnt.sc', 'discord.com/attachments/', 
                                      'discordapp.com/attachments/', 'cdn.discordapp.com', 'media.discordapp.net']
                        
                        if not valid_image:
                            for host in image_hosts:
                                if host in image_url.lower():
                                    # Trust these hosts even without proper extension
                                    valid_image = True
                                    logger.info(f"Accepted image from trusted host: {host}")
                                    break
                    
                    if not valid_image:
                        await interaction.followup.send(
                            "⚠️ The image URL you provided doesn't appear to be a direct link to an image. "
                            "Make sure the URL ends with .png, .jpg, .jpeg, .gif, etc. and is a direct link, "
                            "or use an image from Discord, Imgur, or similar image hosting services.",
                            ephemeral=True
                        )
                        return
                except Exception as e:
                    logger.error(f"Error validating image URL: {e}")
                    image_url = None
                    valid_image = False
            
            # Create the report data
            report_data = {
                'report_id': len(self.reports['reports']) + 1,
                'reporter_id': str(interaction.user.id),
                'reporter_name': interaction.user.display_name,
                'reported_user_id': str(user.id),
                'reported_user_name': user.display_name,
                'reason': reason,
                'server_id': str(interaction.guild.id),
                'server_name': interaction.guild.name,
                'timestamp': datetime.datetime.now().isoformat(),
                'status': 'pending',  # pending, reviewing, resolved, rejected
                'image_url': image_url if valid_image else None
            }
            
            # Add to reports list
            self.reports['reports'].append(report_data)
            self.save_reports()
            
            # Send confirmation to the user
            await interaction.followup.send(
                f"✅ Thank you for your report about {user.mention}. Your report has been submitted to the moderation team.",
                ephemeral=True
            )
            
            # Create embed for report log
            embed = discord.Embed(
                title=f"🚨 New User Report #{report_data['report_id']}",
                description=f"**Reason:** {reason}",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            
            embed.add_field(
                name="Reported User",
                value=f"{user.mention} ({user.name}, ID: {user.id})",
                inline=False
            )
            
            embed.add_field(
                name="Reported By",
                value=f"{interaction.user.mention} ({interaction.user.name}, ID: {interaction.user.id})",
                inline=False
            )
            
            # Add image if provided
            if valid_image and image_url:
                try:
                    # Add field with link to image
                    embed.add_field(
                        name="Evidence",
                        value=f"[View Image/Screenshot]({image_url})",
                        inline=False
                    )
                    
                    # Only set the image if the URL is properly formatted
                    # Discord requires a properly formatted URL for embeds
                    if not image_url or not image_url.startswith(('http://', 'https://')):
                        logger.warning(f"Invalid image URL format: {image_url}")
                        # Don't set the image, just keep the link
                    else:
                        try:
                            embed.set_image(url=image_url)
                        except Exception as e:
                            logger.error(f"Error setting image in embed: {e}")
                            # If setting the image fails, at least we still have the link
                except Exception as e:
                    logger.error(f"Error adding image field to embed: {e}")
            
            embed.set_footer(text=f"Server: {interaction.guild.name}")
            
            # Get the report channel and send the log
            try:
                report_channel = self.bot.get_channel(self.report_channel_id)
                
                # If channel not found by ID, try to fetch it
                if not report_channel:
                    logger.warning(f"Channel not found by ID {self.report_channel_id}, attempting to fetch it directly...")
                    try:
                        # Try to fetch the channel directly as a fallback
                        report_channel = await self.bot.fetch_channel(self.report_channel_id)
                    except Exception as e:
                        logger.error(f"Failed to fetch channel: {e}")
                        report_channel = None
                
                if report_channel:
                    try:
                        # Create view with action buttons
                        view = ReportActionView(self, report_data['report_id'], user.id)
                        
                        # Send message with embed and buttons
                        report_message = await report_channel.send(embed=embed, view=view)
                        
                        # Save message ID to report data
                        report_data['message_id'] = str(report_message.id)
                        self.save_reports()
                        
                        logger.info(f"Successfully sent report #{report_data['report_id']} to channel {self.report_channel_id}")
                        
                    except Exception as e:
                        logger.error(f"Could not send report to channel: {e}")
                        await interaction.followup.send(
                            "⚠️ Your report was saved but could not be sent to the moderation team. A staff member will review it later.",
                            ephemeral=True
                        )
                else:
                    logger.error(f"Could not find report channel with ID {self.report_channel_id}")
                    # Still save the report even if we can't send it
                    await interaction.followup.send(
                        "⚠️ Your report was saved but the report channel could not be found. A staff member will review it later.",
                        ephemeral=True
                    )
            except Exception as e:
                logger.error(f"Error accessing report channel: {e}", exc_info=True)
                await interaction.followup.send(
                    "⚠️ Your report was saved but could not be sent to the moderation team due to a channel error. A staff member will review it later.",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error in report command: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ An error occurred while submitting your report. Please try again later or contact a staff member directly.",
                ephemeral=True
            )

async def setup(bot):
    """Add the reporting cog to the bot"""
    await bot.add_cog(ReportingCog(bot))
    print("Reporting system loaded!")