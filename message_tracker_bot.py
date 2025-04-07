import os
import discord
import requests
import json
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
API_ENDPOINT = os.getenv('MESSAGE_TRACKER_API_ENDPOINT')
API_KEY = os.getenv('MESSAGE_TRACKER_API_KEY')

# Check if essential environment variables are set
if not TOKEN:
    print("Error: DISCORD_BOT_TOKEN environment variable is not set.")
if not API_ENDPOINT:
    print("Warning: MESSAGE_TRACKER_API_ENDPOINT environment variable is not set.")
    print("Example: https://your-replit-app.replit.app/api/update_message_count")
if not API_KEY:
    print("Warning: MESSAGE_TRACKER_API_KEY environment variable is not set.")

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Create bot instance
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    """Executes when the bot successfully connects to Discord."""
    print(f"Message Tracker Bot connected as {bot.user.name}")
    print(f"Bot ID: {bot.user.id}")
    print("------")
    
    # Print connected servers
    print("Connected to the following servers:")
    for guild in bot.guilds:
        print(f"- {guild.name} (ID: {guild.id})")
    
    print("------")
    print("Message tracking is now active.")
    
    if not API_ENDPOINT or not API_KEY:
        print("WARNING: API endpoint or API key not set. Message tracking will not work!")
        print("Set MESSAGE_TRACKER_API_ENDPOINT and MESSAGE_TRACKER_API_KEY in your .env file.")

@bot.event
async def on_message(message):
    """Executes whenever a message is sent in a server the bot is in."""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Process commands first
    await bot.process_commands(message)
    
    # Skip DMs
    if not isinstance(message.channel, discord.TextChannel):
        return
    
    # Skip if API endpoint or key is not set
    if not API_ENDPOINT or not API_KEY:
        return
    
    # Get message and user info
    server_id = str(message.guild.id)
    server_name = message.guild.name
    user_id = str(message.author.id)
    username = message.author.name if hasattr(message.author, 'name') else 'Unknown'
    if hasattr(message.author, 'discriminator') and message.author.discriminator != '0':
        username += f"#{message.author.discriminator}"
    
    # Prepare data for API
    data = {
        'server_id': server_id,
        'server_name': server_name,
        'discord_id': user_id,
        'username': username
    }
    
    headers = {
        'Content-Type': 'application/json',
        'API-Key': API_KEY
    }
    
    # Send data to API
    try:
        response = requests.post(API_ENDPOINT, headers=headers, json=data)
        
        if response.status_code == 200:
            # API call successful
            pass
        else:
            print(f"API Error: Status {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending data to API: {e}")

@bot.command(name='stats')
async def stats(ctx):
    """Show message count statistics for the server"""
    if not API_ENDPOINT:
        await ctx.send("❌ This bot is not properly configured for message tracking.")
        return
    
    # Get stats from the API
    server_id = str(ctx.guild.id)
    stats_url = f"{API_ENDPOINT.replace('update_message_count', 'server_stats')}/{server_id}"
    
    try:
        response = requests.get(stats_url)
        
        if response.status_code == 200:
            data = response.json()
            
            # Create embed
            embed = discord.Embed(
                title=f"Message Statistics for {ctx.guild.name}",
                color=discord.Color.blue()
            )
            
            # Add fields
            embed.add_field(name="Total Messages", value=str(data['total_messages']), inline=True)
            embed.add_field(name="Active Members", value=str(data['member_count']), inline=True)
            
            # Add top 5 users
            if data['members']:
                top_users = sorted(data['members'], key=lambda x: x['message_count'], reverse=True)[:5]
                top_users_text = "\n".join([f"{i+1}. {m['username']}: {m['message_count']} messages" 
                                            for i, m in enumerate(top_users)])
                embed.add_field(name="Top Active Members", value=top_users_text, inline=False)
            
            # Set footer
            embed.set_footer(text="Message tracking by Message Tracker Bot")
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Error retrieving statistics. Status code: {response.status_code}")
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command(name='mymsgs')
async def my_messages(ctx):
    """Show the message count for the command user"""
    if not API_ENDPOINT:
        await ctx.send("❌ This bot is not properly configured for message tracking.")
        return
    
    # Get stats from the API
    server_id = str(ctx.guild.id)
    stats_url = f"{API_ENDPOINT.replace('update_message_count', 'server_stats')}/{server_id}"
    
    try:
        response = requests.get(stats_url)
        
        if response.status_code == 200:
            data = response.json()
            user_id = str(ctx.author.id)
            
            # Find the user in the members list
            user_data = next((m for m in data['members'] if m['discord_id'] == user_id), None)
            
            if user_data:
                embed = discord.Embed(
                    title="Your Message Statistics",
                    description=f"Statistics for {ctx.author.mention} in {ctx.guild.name}",
                    color=discord.Color.green()
                )
                
                embed.add_field(name="Total Messages", value=str(user_data['message_count']), inline=True)
                
                # Calculate rank
                members_sorted = sorted(data['members'], key=lambda x: x['message_count'], reverse=True)
                rank = next((i+1 for i, m in enumerate(members_sorted) if m['discord_id'] == user_id), "Unknown")
                
                embed.add_field(name="Server Rank", value=f"#{rank} of {len(data['members'])}", inline=True)
                
                # Add last active time
                if user_data['last_active']:
                    embed.add_field(name="Last Active", value=user_data['last_active'], inline=True)
                
                embed.set_footer(text="Message tracking by Message Tracker Bot")
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ No message data found for you in this server.")
        else:
            await ctx.send(f"❌ Error retrieving statistics. Status code: {response.status_code}")
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

# Run the bot
if __name__ == "__main__":
    bot.run(TOKEN)