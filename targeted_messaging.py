import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import logging
import datetime
from typing import Optional

# Set up logging
logger = logging.getLogger('targeted_messaging')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.FileHandler(filename='logs/bot.log', encoding='utf-8', mode='a')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

class TargetedMessagingCog(commands.Cog):
    """Cog for sending targeted messages to specific members."""
    
    def __init__(self, bot):
        self.bot = bot
        self.allowed_user_id = 1308527904497340467  # Only this user can use the sendtoall2 command
        logger.info("Targeted Messaging cog initialized")
    
    @app_commands.command(
        name="sendtoall2",
        description="Send an embedded message to a specific member multiple times"
    )
    async def sendtoall2(self, interaction: discord.Interaction):
        """
        Send an embedded message to a specific member multiple times.
        This command is only available to the owner (user ID: 1308527904497340467).
        """
        # Check if the user is allowed to use this command
        if interaction.user.id != self.allowed_user_id:
            await interaction.response.send_message(
                "You don't have permission to use this command.", 
                ephemeral=True
            )
            logger.warning(f"Unauthorized user {interaction.user.id} attempted to use sendtoall2")
            return
        
        # Create the initial embed for the command
        embed = discord.Embed(
            title="Targeted Message Sender",
            description="Use this tool to send an embed message to a specific member multiple times.",
            color=discord.Color.blue()
        )
        
        # Add instructions
        embed.add_field(
            name="How to use",
            value="1. Click 'Create Message' to set up your embed message\n"
                  "2. Specify the target member and message count\n"
                  "3. Send the messages",
            inline=False
        )
        
        # Create view with buttons
        view = TargetedMessageView(self)
        
        # Send the initial message
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        logger.info(f"User {interaction.user.id} opened the targeted message creator")

    async def send_targeted_messages(self, interaction, target_id, message_count, embed):
        """Send multiple messages to a targeted user."""
        try:
            # Get the target member
            target_member = await interaction.guild.fetch_member(target_id)
            if not target_member:
                await interaction.followup.send(f"Could not find member with ID {target_id}", ephemeral=True)
                return False
            
            # Send the messages
            success_count = 0
            
            for i in range(message_count):
                try:
                    await target_member.send(embed=embed)
                    success_count += 1
                    await asyncio.sleep(1)  # Small delay between messages to avoid rate limits
                except Exception as e:
                    logger.error(f"Error sending message {i+1} to {target_id}: {e}")
            
            # Send a confirmation message
            await interaction.followup.send(
                f"Successfully sent {success_count}/{message_count} messages to {target_member.display_name}",
                ephemeral=True
            )
            logger.info(f"User {interaction.user.id} sent {success_count}/{message_count} messages to {target_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error in send_targeted_messages: {e}")
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)
            return False


class TargetedMessageView(discord.ui.View):
    """View with buttons for the targeted message creator."""
    
    def __init__(self, cog):
        super().__init__(timeout=600)  # 10 minute timeout
        self.cog = cog
    
    @discord.ui.button(label="Create Message", style=discord.ButtonStyle.primary)
    async def create_message_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open modal to create the message and specify target."""
        await interaction.response.send_modal(TargetedMessageModal(self.cog))


class TargetedMessageModal(discord.ui.Modal, title="Create Targeted Message"):
    """Modal for creating a targeted message and specifying recipient and count."""
    
    title_input = discord.ui.TextInput(
        label="Message Title",
        placeholder="Enter the title for your embed message",
        required=True,
        max_length=100
    )
    
    description_input = discord.ui.TextInput(
        label="Message Description",
        placeholder="Enter the description for your embed message",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=1000
    )
    
    target_id_input = discord.ui.TextInput(
        label="Target Member ID",
        placeholder="Enter the Discord ID of the target member",
        required=True,
        max_length=20
    )
    
    count_input = discord.ui.TextInput(
        label="Message Count",
        placeholder="Enter the number of times to send the message (1-10)",
        required=True,
        max_length=2
    )
    
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle the modal submission."""
        # Validate the message count
        try:
            message_count = int(self.count_input.value)
            if message_count < 1 or message_count > 10:
                await interaction.response.send_message(
                    "Message count must be between 1 and 10.",
                    ephemeral=True
                )
                return
        except ValueError:
            await interaction.response.send_message(
                "Message count must be a valid number.",
                ephemeral=True
            )
            return
        
        # Validate the target ID
        try:
            target_id = int(self.target_id_input.value)
        except ValueError:
            await interaction.response.send_message(
                "Target ID must be a valid Discord user ID.",
                ephemeral=True
            )
            return
        
        # Create the embed
        embed = discord.Embed(
            title=self.title_input.value,
            description=self.description_input.value,
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        # Set footer with sender info
        embed.set_footer(text=f"Sent by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        
        # Show a preview and confirmation
        preview_embed = discord.Embed(
            title="Message Preview",
            description=f"You're about to send this message to user ID `{target_id}` **{message_count}** times.",
            color=discord.Color.gold()
        )
        
        preview_embed.add_field(
            name="Target Member ID",
            value=f"`{target_id}`",
            inline=True
        )
        
        preview_embed.add_field(
            name="Message Count",
            value=str(message_count),
            inline=True
        )
        
        # Create confirmation view
        view = TargetedMessageConfirmView(self.cog, target_id, message_count, embed)
        
        await interaction.response.send_message(
            content="**Here's a preview of your message:**",
            embeds=[preview_embed, embed],
            view=view,
            ephemeral=True
        )


class TargetedMessageConfirmView(discord.ui.View):
    """View with confirm/cancel buttons for the targeted message."""
    
    def __init__(self, cog, target_id, message_count, embed):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.target_id = target_id
        self.message_count = message_count
        self.embed = embed
    
    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm and send the messages."""
        await interaction.response.defer(ephemeral=True)
        await self.cog.send_targeted_messages(interaction, self.target_id, self.message_count, self.embed)
        self.disable_all_buttons()
        await interaction.edit_original_response(view=self)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel sending the messages."""
        await interaction.response.edit_message(
            content="Message sending canceled.",
            embeds=[],
            view=None
        )
    
    def disable_all_buttons(self):
        """Disable all buttons in the view."""
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True


async def setup(bot):
    """Add the targeted messaging cog to the bot."""
    await bot.add_cog(TargetedMessagingCog(bot))
    logger.info("Targeted Messaging cog loaded")