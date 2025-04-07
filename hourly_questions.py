import discord
from discord.ext import commands, tasks
import random
import asyncio
import logging
import re
import os
import json
from datetime import datetime, timedelta
import traceback
from logger import setup_logger

logger = setup_logger('hourly_questions')

# List of questions for the bot to ask
QUESTIONS = [
    "If you could invent a new dessert, what would it be and what would it taste like?",
    "If your pet could talk, what's the first thing you think it would say?",
    "What would your dream video game look like if you designed it?",
    "If you could teleport anywhere right now, where would you go and why?",
    "What would your magical power be if you had one for 24 hours?",
    "If you had a theme song that played every time you entered a room, what would it be?",
    "What flavor would a rainbow actually be if it was edible?",
    "If you lived in a fantasy world, what creature would you want as a companion?",
    "If you could rename the moon, what would you call it?",
    "If your room could transform into anything overnight, what would you want it to become?",
    "If clouds were made of something other than water, what would you want them made of?",
    "What's the weirdest food combo you secretly enjoy?",
    "If you had to wear only one color for the rest of your life, what would it be?",
    "If dreams were a place you could visit, what would yours look like?",
    "What would a holiday made just for you include?",
    "If you had a robot assistant, what would you name it and what would it do?",
    "If you could be any age forever, what age would you choose?",
    "What would a soda invented by you taste like?",
    "If animals had jobs, what job would fit your favorite animal?",
    "If your personality were an ice cream flavor, what would it be?",
    "What would a plant that grows something other than fruit grow instead?",
    "If your life was a game, what would be your special ability?",
    "What would a perfume based on your vibe smell like?",
    "If you could mix two animals to make a new one, which would you choose?",
    "If a mirror showed your true form, what would it reflect?",
    "What would you name a star if one was discovered just for you?",
    "If your laugh had a color, what would it be?",
    "What kind of house would you build if gravity didn't exist?",
    "If you had a personal island, what would you call it?",
    "What song would play every time you wake up in the morning?",
    "If you could be invisible for one hour, what would you do?",
    "What would a movie about your dreams be called?",
    "What snack should totally exist but doesn't (yet)?",
    "If you could bottle a feeling, which one would you choose?",
    "What animal should be able to talk, and why?",
    "What would your ideal futuristic gadget do?",
    "If time travel was safe, where (and when) would you go?",
    "If you could replace traffic lights with anything, what would you pick?",
    "What would a video game based on your day look like?",
    "If you had a signature spell, what would it do?",
    "If you could design your own constellation, what shape would it be?",
    "What would be the weirdest but coolest superpower?",
    "If your shadow had a personality, what would it be like?",
    "What flavor would lightning be if you could taste it?",
    "What would your ideal dream pet be (real or imaginary)?",
    "If the sky wasn't blue, what color should it be?",
    "If your thoughts had a sound effect, what would it be?",
    "What would a dream job in space look like?",
    "If you could mix two holidays together, which ones would you pick?",
    "If your voice could trigger anything, what would it control?"
]

# Color-related responses for common colors
COLOR_RESPONSES = {
    "red": [
        "Red is such a powerful choice! It represents passion, energy, and determination - just like you! 🔥",
        "Red is fascinating - it can symbolize both love and anger. Which aspect of red speaks to you the most? ❤️",
        "Red is the color of courage and strength! It's the first color babies can see - you've chosen something truly primal and powerful. 🌹"
    ],
    "blue": [
        "Blue is so calming and peaceful - like looking at the ocean on a clear day. Your choice reflects a serene soul! 🌊",
        "Blue represents trust, loyalty, and wisdom. It's no wonder it's the world's favorite color - excellent choice! 💙",
        "Blue is the color of the vast sky and deep oceans - it reminds us that possibilities are endless, just like your imagination! ✨"
    ],
    "green": [
        "Green is the perfect balance between warm and cool colors, just as nature creates perfect harmony. Beautiful choice! 🌿",
        "Green represents growth, renewal, and abundance. Your choice suggests you value progress and new beginnings! 🌱",
        "The human eye can distinguish more shades of green than any other color - perhaps because it's the color of life itself. What a thoughtful selection! 🌳"
    ],
    "yellow": [
        "Yellow radiates happiness and optimism! It's the most visible color from a distance - your positivity shines just as brightly! ☀️",
        "Yellow stimulates mental activity and generates muscle energy - no wonder it makes people feel so alive and energetic! Fantastic pick! 🌻",
        "Yellow symbolizes joy and intellectual energy. Fun fact: yellow is often used in places where important decisions are made. Your choice reveals your bright mind! ✨"
    ],
    "purple": [
        "Purple combines the stability of blue and the energy of red - creating a perfect magical balance. It's long been associated with royalty and wisdom! 👑",
        "Purple is relatively rare in nature, making it historically precious. Your choice reveals an appreciation for the extraordinary! 💜",
        "Purple stimulates imagination and spirituality - it's the color of dreamers and visionaries. Your creative spirit shines through! 🔮"
    ],
    "black": [
        "Black absorbs all light in the color spectrum, making it powerful and mysterious. It represents elegance and sophistication - excellent choice! 🖤",
        "Black creates a perception of weight and seriousness. It's timeless and versatile - just like your thoughtful perspective! ✨",
        "Black symbolizes power, elegance, and formality. In many cultures, it represents protection from evil - your choice reveals depth! 🌑"
    ],
    "white": [
        "White reflects all the colors of the visible spectrum, symbolizing purity and perfection. Your choice suggests a clarity of thought! ✨",
        "White creates a sense of space and possibility - it's the color of new beginnings and fresh starts. What a positive outlook! 🕊️",
        "White represents simplicity and cleanliness. In many Eastern cultures, it symbolizes mourning - your choice reveals cultural awareness! 🤍"
    ],
    "orange": [
        "Orange combines the energy of red and the happiness of yellow - it represents enthusiasm and creativity! Your vibrant spirit shows! 🧡",
        "Orange increases oxygen supply to the brain and stimulates mental activity - it's the color of motivation and optimism! Great choice! 🍊",
        "Orange is associated with joy, sunshine, and the tropics - it's warm and inviting, just like your personality seems to be! 🌅"
    ],
    "pink": [
        "Pink represents kindness, nurturing, and compassion. It has a calming effect that suppresses aggression - your gentle soul shines through! 💗",
        "Pink is universally associated with sweetness and romance. Studies show it can even temporarily sap strength! Your choice reveals sensitivity! 🌸",
        "Pink symbolizes love and charm. It was actually considered a masculine color until the mid-20th century! Your choice challenges conventions! 💕"
    ],
    "brown": [
        "Brown represents reliability, stability, and grounding - it's the color of earth and trees, connecting us to nature's dependability! 🌰",
        "Brown creates a sense of wholesomeness, warmth, and honesty. Your choice suggests you value authenticity above all! 🍂",
        "Brown symbolizes resilience and dependability. It's comforting and nurturing - your choice reveals your practical yet caring nature! 🪵"
    ],
    "gold": [
        "Gold symbolizes achievement, success, and triumph - it's associated with prosperity and abundance. Your aspirations shine brightly! ✨",
        "Gold represents wisdom, wealth, and prosperity. It's been valued by virtually every civilization throughout history! Excellent choice! 🌟",
        "Gold is connected to generosity, compassion, and wisdom. Its warm tone evokes feelings of prestige and accomplishment! Your taste is refined! 👑"
    ],
    "silver": [
        "Silver symbolizes reflection, clarity, and focus. It's associated with the moon and feminine energy - your choice reveals intuition! 🌙",
        "Silver represents technological advancement and modernity. It's sleek, sophisticated, and precisely balanced - just like your thinking! ✨",
        "Silver is connected to grace, elegance, and sophistication. It symbolizes illumination of the soul - your choice reveals depth! 💫"
    ]
}

# Word category detection for more contextual responses
FOOD_WORDS = ["food", "eat", "taste", "flavor", "delicious", "sweet", "sour", "bitter", "spicy", "savory", 
              "chocolate", "vanilla", "strawberry", "pizza", "burger", "ice cream", "cookie", "cake",
              "bacon", "cheese", "snack", "breakfast", "lunch", "dinner", "dessert", "fruit", "vegetable"]

ANIMAL_WORDS = ["animal", "pet", "dog", "cat", "bird", "fish", "tiger", "lion", "elephant", "giraffe", 
                "zebra", "panda", "bear", "wolf", "fox", "rabbit", "bunny", "puppy", "kitten", "horse", 
                "unicorn", "dragon", "creature", "monkey", "gorilla", "eagle", "hawk", "owl"]

PLACE_WORDS = ["place", "country", "city", "town", "beach", "mountain", "forest", "jungle", "desert", 
               "island", "ocean", "sea", "lake", "river", "park", "home", "house", "building", "paris", 
               "london", "tokyo", "new york", "space", "moon", "mars", "planet"]

FANTASY_WORDS = ["magic", "wizard", "witch", "dragon", "fairy", "elf", "dwarf", "unicorn", "spell", 
                "potion", "wand", "enchanted", "mythical", "legend", "fantasy", "magical", "supernatural", 
                "superpower", "superhero", "invisible", "teleport", "fly", "power", "ability"]

# Themed response templates for different topics
FOOD_RESPONSES = [
    "Mmm, that sounds absolutely delicious! I can almost taste the flavors you're describing. Have you always enjoyed that kind of food? 🍽️",
    "What a mouthwatering choice! Food really connects to our emotions and memories. Is there a special reason you chose that particular flavor? 🍰",
    "That's a culinary masterpiece in the making! Your taste buds must be doing a happy dance just thinking about it. What inspired this delectable creation? 🧁"
]

ANIMAL_RESPONSES = [
    "What a magnificent creature choice! Animals bring such joy and wonder to our lives. What qualities do you admire most about that particular animal? 🦊",
    "That's such a fascinating animal! Nature's diversity is truly incredible. What do you think life would be like if you could communicate with them? 🐘",
    "What an amazing pick! Did you know that animals can teach us so much about loyalty, instinct, and living in the moment? What lessons do you think your chosen animal could teach us? 🦁"
]

PLACE_RESPONSES = [
    "That location sounds absolutely breathtaking! Places hold such powerful memories and feelings. What draws you most to this particular spot? 🏝️",
    "What a wonderful destination choice! Sometimes places call to our souls in unexplainable ways. What kind of adventures would you have there? 🗻",
    "That's such a fascinating place! Our environment shapes so much of who we become. Would you visit just once or could you see yourself living there? 🌆"
]

FANTASY_RESPONSES = [
    "Your imagination is absolutely magical! Fantasy allows us to explore possibilities beyond our reality. What adventures would you embark on with that power? ✨",
    "What an enchanting idea! The realm of fantasy helps us process our real-world experiences in creative ways. How would that magical element change your daily life? 🧙‍♂️",
    "That's brilliantly creative! Fantasy and imagination are the seeds of innovation. What inspired this magical concept? 🔮"
]

# General thoughtful responses as fallbacks
GENERAL_RESPONSES = [
    "That's a really creative answer! Your unique perspective adds so much to our community. What inspired this wonderful idea? 🌟",
    "Wow, I never thought of that! It's perspectives like yours that help us all see the world differently. Could you share more about your thinking process? 🤔",
    "That's fascinating! Your answer reveals such depth of imagination. Have you always had such creative ideas or is this a recent development? 💭",
    "What a brilliant response! It's clear you've given this some thought. Does this reflect something you're passionate about in your daily life? 😄",
    "That's such a unique perspective! The way you approach questions reveals a truly original mind. What other creative ideas do you have brewing? 🔮",
    "I love how you think outside the conventional boundaries! Your response creates a whole new way of looking at things. What inspires your creativity? 💡",
    "That's not just a great idea - it's revolutionary! Your perspective could change how we all think about this topic. Have you shared this insight before? ✨",
    "What an intriguing choice! The best answers often raise even more interesting questions. What led you to this particular conclusion? 🧐",
    "That's so cool and unexpected! It's answers like yours that make conversations truly memorable. How long have you been interested in this subject? 🚀",
    "I can totally see the thought process behind your answer! It reveals both logic and imagination working together perfectly. Is this how you approach most questions? 👀",
    "That's exactly the kind of creativity we need more of in the world! Your answer bridges concepts that don't usually connect. Do you often make these kinds of mental connections? 🎨",
    "Your imagination is truly spectacular! The way you've constructed this answer shows both emotional intelligence and creative flair. What other creative outlets do you enjoy? 🌈",
    "That's such a thought-provoking response! It's making me reconsider my own perspective on the question. Has your thinking on this evolved over time? 🎉",
    "I'm genuinely curious to hear more about how you arrived at this answer! It suggests both intuition and careful consideration. Do you usually trust your first instinct? 📝",
    "You've got a wonderful way of looking at things that combines practicality with imagination! Your answer reveals a multi-dimensional thinker. How do you nurture your creativity? 🌍"
]

class HourlyQuestionsCog(commands.Cog):
    """Cog for sending hourly random questions in a specific channel."""
    
    def __init__(self, bot):
        self.bot = bot
        self.target_channel_id = 1339809561594298448  # The channel to send questions in
        self.role_to_ping_id = 1349698354145398826    # The role to ping with questions
        self.last_question_message_id = None          # Track the last question message
        self.active_questions = {}                    # Track active questions (message_id: question)
        self.timer_file = "data/hourly_questions_timer.json"
        self.next_question_time = None
        self.load_timer()
        self.hourly_questions.start()                 # Start the hourly task
        
    def cog_unload(self):
        self.save_timer()
        self.hourly_questions.cancel()
    
    def load_timer(self):
        """Load the next question time from the timer file."""
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(self.timer_file), exist_ok=True)
        
        try:
            if os.path.exists(self.timer_file):
                with open(self.timer_file, 'r') as f:
                    data = json.load(f)
                    next_time_str = data.get('next_question_time')
                    if next_time_str:
                        self.next_question_time = datetime.fromisoformat(next_time_str)
                        logger.info(f"Loaded next question time: {self.next_question_time}")
                    else:
                        self.next_question_time = None
            else:
                logger.info("No timer file found, will schedule next question for the start of the next hour")
                self.next_question_time = None
        except Exception as e:
            logger.error(f"Error loading timer file: {e}")
            self.next_question_time = None
    
    def save_timer(self):
        """Save the next question time to the timer file."""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(self.timer_file), exist_ok=True)
            
            data = {}
            if self.next_question_time:
                data['next_question_time'] = self.next_question_time.isoformat()
            
            with open(self.timer_file, 'w') as f:
                json.dump(data, f)
                
            logger.info(f"Saved next question time: {self.next_question_time}")
        except Exception as e:
            logger.error(f"Error saving timer file: {e}")
        
    # Don't auto-restart the task, we'll handle it manually
    @tasks.loop(count=1)
    async def hourly_questions(self):
        """Send a random question and schedule the next one."""
        try:
            # We're going to handle scheduling separately
            # Only start the process, it will schedule itself
            logger.info("Hourly questions task initialized")
            
        except Exception as e:
            logger.error(f"Error in hourly questions task: {e}")
            logger.error(traceback.format_exc())
    
    async def send_question(self):
        """Send a random question to the target channel."""
        try:
            channel = self.bot.get_channel(self.target_channel_id)
            if not channel:
                logger.error(f"Could not find channel with ID {self.target_channel_id}")
                return
                
            # Choose a random question
            question = random.choice(QUESTIONS)
            
            # Get the role mention text
            role_mention = f"<@&{self.role_to_ping_id}>"
            
            # Create a formatted embed for the question
            embed = discord.Embed(
                title="✨ Question of the Hour ✨",
                description=f"{question}",
                color=discord.Color.blue()
            )
            
            embed.set_footer(text=f"Reply to this message to answer! • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
            # Send the message with the role ping
            message = await channel.send(content=f"{role_mention} Here's a new question:", embed=embed)
            
            # Store the message ID for future reference
            self.last_question_message_id = message.id
            self.active_questions[message.id] = question
            
            logger.info(f"Sent hourly question: {question}")
            return True
        except Exception as e:
            logger.error(f"Error sending question: {e}")
            return False
            
    async def schedule_next_question(self):
        """Schedule the next question based on saved time."""
        try:
            # Calculate time until next question
            now = datetime.now()
            
            # If we have a saved next question time, use it
            if self.next_question_time:
                time_diff = (self.next_question_time - now).total_seconds()
                # If the saved time is in the past (by more than 5 seconds), schedule for the next hour
                if time_diff < -5:
                    logger.info("Saved next question time is in the past, scheduling for next hour")
                    seconds_until_next_hour = (60 - now.minute) * 60 - now.second
                    self.next_question_time = now + timedelta(seconds=seconds_until_next_hour)
                    time_diff = seconds_until_next_hour
                    self.save_timer()
            else:
                # Default: wait until the start of the next hour
                seconds_until_next_hour = (60 - now.minute) * 60 - now.second
                time_diff = seconds_until_next_hour
                self.next_question_time = now + timedelta(seconds=seconds_until_next_hour)
                self.save_timer()
            
            # Don't wait if it's very close
            if time_diff < 5:
                time_diff = 5
                
            # Log the wait time
            next_time = now + timedelta(seconds=time_diff)
            logger.info(f"Scheduling next question for {next_time.strftime('%Y-%m-%d %H:%M:%S')} (in {time_diff:.0f} seconds)")
            
            # Schedule the task
            self.bot.loop.create_task(self._wait_and_send_next_question(time_diff))
            
        except Exception as e:
            logger.error(f"Error scheduling next question: {e}")
            logger.error(traceback.format_exc())
            # Fallback: try again in 1 hour
            self.bot.loop.create_task(self._wait_and_send_next_question(3600))
    
    async def _wait_and_send_next_question(self, seconds):
        """Wait for the specified number of seconds and then send a question."""
        try:
            # Wait for the specified time
            await asyncio.sleep(seconds)
            
            # Send the question
            success = await self.send_question()
            
            if success:
                # Schedule the next question for an hour from now
                self.next_question_time = datetime.now() + timedelta(hours=1)
                self.save_timer()
                
                # Schedule the next question
                await self.schedule_next_question()
            else:
                # If sending failed, try again in 5 minutes
                logger.error("Failed to send question, will retry in 5 minutes")
                self.next_question_time = datetime.now() + timedelta(minutes=5)
                self.save_timer()
                await self.schedule_next_question()
                
        except Exception as e:
            logger.error(f"Error waiting to send next question: {e}")
            logger.error(traceback.format_exc())
            # Try again in 5 minutes if there was an error
            self.bot.loop.create_task(self._wait_and_send_next_question(300))
    
    @hourly_questions.before_loop
    async def before_hourly_questions(self):
        """Wait until the bot is ready before starting the task."""
        await self.bot.wait_until_ready()
        logger.info("Hourly questions task is ready to begin...")
        
        try:
            # Do not trigger a question immediately if there's a saved timer
            if self.next_question_time:
                # Just schedule based on saved time
                await self.schedule_next_question()
                logger.info(f"Resuming hourly questions from saved time: {self.next_question_time}")
            else:
                # Schedule the next question (first run only)
                await self.schedule_next_question()
                logger.info("Initial scheduling of hourly questions completed")
        except Exception as e:
            logger.error(f"Error in before_hourly_questions: {e}")
            logger.error(traceback.format_exc())
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for replies to the bot's questions with AI-powered conversation."""
        # Ignore messages from bots
        if message.author.bot:
            return
            
        # Check if this is a reply to one of our questions or a reply to our bot's response
        if message.reference and message.reference.message_id:
            try:
                # Try to get the message being replied to
                channel = message.channel
                referenced_message = await channel.fetch_message(message.reference.message_id)
                
                # Check if it's a reply to one of our active questions or to our response
                if referenced_message.author.id == self.bot.user.id:
                    # Check if this is a reply to an hourly question or a response to an hourly question
                    is_reply_to_question = referenced_message.id in self.active_questions
                    
                    # Only proceed if this is related to hourly questions
                    # First check if it's a direct reply to a question
                    if not is_reply_to_question:
                        # If it's not a direct reply, check if it might be a reply to our response
                        # (which would contain a reference to the question message ID)
                        is_related_to_hourly = False
                        for question_id in self.active_questions:
                            # Convert question_id to string before checking if it's in the content
                            if str(question_id) in str(referenced_message.content):
                                is_related_to_hourly = True
                                break
                                
                        if not is_related_to_hourly:
                            # Not related to hourly questions, so don't respond
                            return
                        
                    # Import AI conversation module (done here to avoid circular imports)
                    import ai_conversation
                    
                    # Check if this is a follow-up in an ongoing conversation
                    is_follow_up = ai_conversation.is_follow_up_message(message.author.id)
                    
                    # Get the original question if this is a reply to our question
                    original_question = ""
                    if is_reply_to_question:
                        original_question = self.active_questions.get(referenced_message.id, "")
                    
                    # Get user info
                    user_id = message.author.id
                    username = message.author.name
                    
                    # Get user's message
                    user_message = message.content
                    
                    # Generate response using AI
                    response = ai_conversation.get_ai_response(
                        user_id, 
                        username, 
                        original_question, 
                        user_message,
                        is_follow_up=is_follow_up
                    )
                    
                    # Add a typing indicator for a more natural feel
                    async with channel.typing():
                        # Simulate natural typing time (response length varies)
                        delay = min(len(response) * 0.05, 2.0)  # Cap at 2 seconds
                        await asyncio.sleep(delay)
                    
                    # Respond to the user
                    await message.reply(response, mention_author=True)
                    
                    # Log the interaction
                    logger.info(f"AI responded to {username} ({user_id}) who replied with: {user_message[:30]}...")
            
            except discord.NotFound:
                # Message might have been deleted
                pass
            except Exception as e:
                logger.error(f"Error handling question reply: {e}")
                logger.error(traceback.format_exc())
                # Fallback to a simple response if the AI fails
                await message.reply("That's an interesting perspective! Thanks for sharing. What made you think of that? 🌟", mention_author=True)
    
    @discord.app_commands.command(name="ask_question", description="Manually trigger a random question (Admin only)")
    async def ask_question(self, interaction: discord.Interaction):
        """Manually trigger a random question (Admin only)."""
        # Check permissions - only admins should be able to use this
        if not await self.check_permissions(interaction.user):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        # We need to use send_message instead of send_question to avoid triggering the automatic scheduling
        try:
            # Send a response to the user first
            await interaction.response.send_message("✅ Sending a random question now!", ephemeral=True)
            
            # Manually implement question sending logic
            channel = self.bot.get_channel(self.target_channel_id)
            if not channel:
                logger.error(f"Could not find channel with ID {self.target_channel_id}")
                return
                
            # Choose a random question
            question = random.choice(QUESTIONS)
            
            # Get the role mention text
            role_mention = f"<@&{self.role_to_ping_id}>"
            
            # Create a formatted embed for the question
            embed = discord.Embed(
                title="✨ Question of the Hour ✨",
                description=f"{question}",
                color=discord.Color.blue()
            )
            
            embed.set_footer(text=f"Reply to this message to answer! • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
            # Send the message with the role ping
            message = await channel.send(content=f"{role_mention} Here's a new question:", embed=embed)
            
            # Store the message ID for future reference
            self.last_question_message_id = message.id
            self.active_questions[message.id] = question
            
            # Update the next question time to one hour from now but don't reschedule
            # Just update the existing schedule
            self.next_question_time = datetime.now() + timedelta(hours=1)
            self.save_timer()
            
            logger.info(f"Manual random question triggered by {interaction.user.name}: {question}")
                
        except Exception as e:
            logger.error(f"Error in ask_question command: {e}")
            logger.error(traceback.format_exc())
            
    @discord.app_commands.command(name="hourlyquestion", description="Send a custom question (Admin only)")
    @discord.app_commands.describe(
        question="The custom question to ask",
        ping_role="Whether to ping the configured role (Default: True)"
    )
    async def hourlyquestion(self, interaction: discord.Interaction, question: str, ping_role: bool = True):
        """Send a custom question (Admin only)."""
        # Check permissions - only admins should be able to use this
        if not await self.check_permissions(interaction.user):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        try:
            # Send a response to the user first
            await interaction.response.send_message(f"✅ Sending your custom question now!", ephemeral=True)
            
            # Use the channel where the command was executed
            channel = interaction.channel
            
            # Get the role mention text if pinging is enabled
            role_content = ""
            if ping_role:
                role_mention = f"<@&{self.role_to_ping_id}>"
                role_content = f"{role_mention} Here's a new question:"
            else:
                role_content = "Here's a new question:"
            
            # Create a formatted embed for the question
            embed = discord.Embed(
                title="✨ Question of the Hour ✨",
                description=f"{question}",
                color=discord.Color.purple()  # Different color for custom questions
            )
            
            embed.set_footer(text=f"Reply to this message to answer! • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
            # Send the message with the role ping (if enabled)
            message = await channel.send(content=role_content, embed=embed)
            
            # Store the message ID for future reference
            self.last_question_message_id = message.id
            self.active_questions[message.id] = question
            
            # Update the next question time to one hour from now but don't reschedule
            # Just update the existing schedule
            self.next_question_time = datetime.now() + timedelta(hours=1)
            self.save_timer()
            
            logger.info(f"Custom question sent by {interaction.user.name} in channel {channel.name}: {question}")
                
        except Exception as e:
            logger.error(f"Error in hourlyquestion command: {e}")
            logger.error(traceback.format_exc())
            

    
    async def check_permissions(self, user):
        """Check if a user has admin permissions."""
        # Check owner permissions first
        if user.id == 1308527904497340467:  # Owner ID
            return True
            
        # Use the same permissions system as other admin commands
        admin_user_ids = ["1308527904497340467", "479711321399623681", "1063511383397892256"]
        if str(user.id) in admin_user_ids:
            return True
            
        # Check for admin role
        guild = user.guild
        if guild:
            member = guild.get_member(user.id)
            if member:
                admin_role_id = 1338482857974169683
                for role in member.roles:
                    if role.id == admin_role_id:
                        return True
                        
        return False

async def setup(bot):
    """Add the hourly questions cog to the bot."""
    logger.info("Setting up Hourly Questions cog...")
    try:
        # Check that we have a proper logger
        logger.info("Hourly Questions setup - Logger check passed")
        
        # Initialize the cog
        cog = HourlyQuestionsCog(bot)
        await bot.add_cog(cog)
        
        # Log success with detail
        logger.info(f"Hourly Questions cog loaded successfully - Target channel: {cog.target_channel_id}, Role to ping: {cog.role_to_ping_id}")
        print(f"✓ Hourly Questions cog loaded - Will ping role {cog.role_to_ping_id} in channel {cog.target_channel_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to load Hourly Questions cog: {e}")
        logger.error(traceback.format_exc())
        print(f"✗ Failed to load Hourly Questions cog: {e}")
        return False