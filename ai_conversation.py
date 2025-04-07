import os
import json
import logging
from openai import OpenAI
from datetime import datetime
from logger import setup_logger

logger = setup_logger('ai_conversation')

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Path to store conversation history
CONVERSATION_HISTORY_PATH = "data/conversation_history.json"

# Ensure the directory exists
os.makedirs(os.path.dirname(CONVERSATION_HISTORY_PATH), exist_ok=True)

# Dictionary to track ongoing conversations
conversation_history = {}

def load_conversation_history():
    """Load conversation history from JSON file."""
    global conversation_history
    try:
        if os.path.exists(CONVERSATION_HISTORY_PATH):
            with open(CONVERSATION_HISTORY_PATH, 'r') as f:
                conversation_history = json.load(f)
                logger.info(f"Loaded {len(conversation_history)} conversation histories")
        else:
            conversation_history = {}
            logger.info("No conversation history file found, starting fresh")
    except Exception as e:
        logger.error(f"Error loading conversation history: {e}")
        conversation_history = {}

def save_conversation_history():
    """Save conversation history to JSON file."""
    try:
        # Create a copy of the history that excludes any conversations older than 24 hours
        current_time = datetime.now()
        
        # Limit history size to prevent file growth
        pruned_history = {}
        for user_id, convo in conversation_history.items():
            # Only keep recent messages (last 5) to prevent context size issues
            if "messages" in convo and len(convo["messages"]) > 5:
                convo["messages"] = convo["messages"][-5:]
            pruned_history[user_id] = convo
            
        with open(CONVERSATION_HISTORY_PATH, 'w') as f:
            json.dump(pruned_history, f, indent=2)
            
        logger.info(f"Saved {len(pruned_history)} conversation histories")
    except Exception as e:
        logger.error(f"Error saving conversation history: {e}")

def get_ai_response(user_id, username, question, user_message, is_follow_up=False):
    """
    Get a response from the AI based on the user's message.
    
    Args:
        user_id: The Discord user ID
        username: The Discord username
        question: The original question that was asked (hourly question)
        user_message: The user's message content
        is_follow_up: Whether this is a follow-up message in a conversation
        
    Returns:
        str: The AI's response
    """
    try:
        # Initialize conversation history for this user if it doesn't exist
        if str(user_id) not in conversation_history:
            conversation_history[str(user_id)] = {
                "username": username,
                "last_interaction": datetime.now().isoformat(),
                "messages": []
            }
        
        # Update last interaction time
        conversation_history[str(user_id)]["last_interaction"] = datetime.now().isoformat()
        
        # Store this message in history even if API call fails
        if "messages" not in conversation_history[str(user_id)]:
            conversation_history[str(user_id)]["messages"] = []
            
        # Add the current user message to history
        user_message_obj = {"role": "user", "content": user_message}
        conversation_history[str(user_id)]["messages"].append(user_message_obj)
        
        # Try using the OpenAI API, with graceful fallback
        try:
            # Prepare messages for the AI
            messages = []
            
            # System message to guide the AI's behavior
            system_message = {
                "role": "system", 
                "content": (
                    "You are a friendly, conversational Discord bot that engages with users in a server. "
                    "You respond to users' answers to hourly questions in a way that feels natural and encourages further conversation. "
                    "Keep your responses medium length (2-3 sentences) - not too short, not too long. "
                    "Be positive, supportive, and relate to the user's answer when possible. "
                    "Ask a follow-up question at the end to encourage continued conversation. "
                    "Add an appropriate emoji or two to make your messages feel friendly. "
                    "Never say you're an AI or that you're using GPT/OpenAI."
                )
            }
            messages.append(system_message)
            
            # Add context about the question being answered
            context_message = {
                "role": "system",
                "content": f"The hourly question that was asked was: '{question}'"
            }
            messages.append(context_message)
            
            # Add conversation history for this user if it exists
            if is_follow_up and "messages" in conversation_history[str(user_id)]:
                # Only include the last few messages to avoid hitting token limits
                history = conversation_history[str(user_id)]["messages"][-4:]  # Last 4 messages (2 exchanges)
                messages.extend(history)
            
            # Add the current user message
            messages.append(user_message_obj)
            
            # Check if OpenAI API key is not set or empty
            if not os.environ.get("OPENAI_API_KEY"):
                logger.error("OpenAI API key is missing. Using fallback response.")
                raise ValueError("OpenAI API key is not configured")
            
            # Call the OpenAI API
            response = client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
                messages=messages,
                max_tokens=150,  # Limit token length for medium responses
                temperature=0.7,  # Somewhat creative but still focused
            )
            
            # Extract the response
            ai_response = response.choices[0].message.content
            
        except Exception as api_error:
            # Log the API error but don't fail the whole function
            error_message = str(api_error)
            logger.error(f"OpenAI API error: {error_message}")
            
            # Check for specific error types
            if "exceeded your current quota" in error_message or "insufficient_quota" in error_message:
                logger.error("API quota exceeded. The bot needs a new OpenAI API key with sufficient quota.")
                # Could add admin notification here if needed
            elif "invalid_api_key" in error_message or "API key not valid" in error_message:
                logger.error("Invalid API key. Please check the OPENAI_API_KEY environment variable.")
            elif "rate limit" in error_message or "rate_limit_exceeded" in error_message:
                logger.error("Rate limit exceeded. The bot is making too many requests too quickly.")
            
            # Create a reasonable fallback response based on the question and message content
            # Use our own logic to generate contextual responses
            ai_response = generate_fallback_response(question, user_message, is_follow_up)
        
        # Store the AI response in history
        assistant_message = {"role": "assistant", "content": ai_response}
        conversation_history[str(user_id)]["messages"].append(assistant_message)
        
        # Save the updated conversation history
        save_conversation_history()
        
        return ai_response
        
    except Exception as e:
        logger.error(f"Error in get_ai_response: {e}")
        # Create a more specific fallback that will work even if all other code fails
        
        # Extract key information from the user's message
        user_message_lower = user_message.lower()
        
        # For hourly questions, analyze message content and give a direct, logical response
        if user_message and len(user_message) > 0:
            # Extract key information from the message
            words = user_message_lower.split()
            
            # Check if the message contains "yes", "no", or numbers
            contains_yes = any(word in ["yes", "yeah", "yep", "sure", "definitely", "absolutely"] for word in words)
            contains_no = any(word in ["no", "nope", "nah", "never"] for word in words)
            contains_numbers = any(char.isdigit() for char in user_message)
            message_length = len(words)
            
            # Short answers get short, direct responses
            if message_length <= 3:
                if contains_yes:
                    return "Thanks for your answer! It's interesting to see different perspectives on this. Would you mind sharing more about why you feel that way? 🙂"
                elif contains_no:
                    return "Thanks for your candid response! Everyone has different views on this topic. Is there a particular reason you feel that way? 🤔"
                else:
                    return "Thanks for your brief response! I'd love to hear more about your thoughts on this if you'd like to share. 👍"
            
            # Numbers often indicate lists, rankings, or measurements
            elif contains_numbers:
                return "Thanks for those specific details! Numbers really help paint a clearer picture. What led you to this particular conclusion? 📊"
            
            # Medium-length answers (typical response)
            elif message_length <= 20:
                return "I appreciate your thoughtful response! Your perspective adds an interesting dimension to this discussion. Have you always held this view or has it evolved over time? 💡"
            
            # Detailed answers
            else:
                return "Thank you for such a detailed and insightful response! You've clearly given this considerable thought. I'm curious - what experiences helped shape your perspective on this? 🌟"
        
        # For hourly questions, try to identify the context and give a relevant response
        if question and question.lower():
            q_lower = question.lower()
            if "food" in q_lower or "taste" in q_lower or "eat" in q_lower:
                return "You have excellent taste in food! I appreciate how you explained your culinary preferences. Have you always enjoyed this type of cuisine? 🍽️"
            elif "color" in q_lower:
                return "I can see why you'd choose that color! It's interesting how colors can reflect our personalities. What other colors do you enjoy? 🎨"
            elif "animal" in q_lower or "pet" in q_lower:
                return "That's a fascinating choice of animal! They're known for their unique characteristics. What particular traits do you admire about them? 🦊"
            elif "place" in q_lower or "travel" in q_lower or "country" in q_lower:
                return "That destination sounds wonderful! I can see why you'd want to visit there. What activities would you enjoy most during your visit? 🏝️"
            elif "power" in q_lower or "magic" in q_lower or "ability" in q_lower:
                return "What a creative choice of power! It's fun to imagine having special abilities. How would this power be useful in everyday situations? ✨"
            elif "game" in q_lower or "play" in q_lower:
                return "You seem to have great taste in games! This one sounds particularly interesting. Do you enjoy other similar games as well? 🎮"
            elif "music" in q_lower or "song" in q_lower:
                return "Your music selection shows excellent taste! Music can be so personal and meaningful. What other artists or genres do you enjoy listening to? 🎵"
                
        # If we couldn't match anything specific, give a more concrete response
        return "Thanks for sharing your thoughts! I find what you've said quite interesting. I'd love to hear more about how you formed this opinion if you'd like to share. 🌟"

def generate_fallback_response(question, user_message, is_follow_up=False):
    """Generate a contextual fallback response when OpenAI API isn't available.
    
    Args:
        question: The original question from the bot
        user_message: The user's message content
        is_follow_up: Whether this is a follow-up in a conversation
        
    Returns:
        str: A contextual response that relates to the user's message
    """
    import random
    
    # Convert to lowercase for easier matching
    user_message_lower = user_message.lower()
    question_lower = question.lower() if question else ""
    
    # First, try to understand the original question context to make more relevant responses
    question_context = "general"
    
    # Identify question context
    if any(word in question_lower for word in ["food", "taste", "flavor", "eat", "dessert", "soda", "cake", "ice cream"]):
        question_context = "food"
    elif any(word in question_lower for word in ["color", "blue", "red", "green", "yellow"]):
        question_context = "color"
    elif any(word in question_lower for word in ["animal", "pet", "creature", "dog", "cat", "wild"]):
        question_context = "animal"
    elif any(word in question_lower for word in ["travel", "place", "country", "destination", "island", "location"]):
        question_context = "place"
    elif any(word in question_lower for word in ["magic", "power", "superpower", "ability", "fantasy", "spell"]):
        question_context = "fantasy"
    elif any(word in question_lower for word in ["invent", "create", "design", "build"]):
        question_context = "creation"
    elif any(word in question_lower for word in ["dream", "imagine", "fantasy", "wish"]):
        question_context = "imagination"
    elif any(word in question_lower for word in ["game", "play", "strategy", "video"]):
        question_context = "game"
    elif any(word in question_lower for word in ["music", "song", "theme", "sound"]):
        question_context = "music"
    
    # Now look at the user's response to detect themes
    user_themes = []
    
    # More comprehensive keyword lists for better context detection
    if any(word in user_message_lower for word in ["food", "taste", "flavor", "delicious", "eat", "sweet", "sour", "spicy", "cook", "bake", 
                                               "chocolate", "vanilla", "strawberry", "fruit", "vegetable", "dessert", "meal", "snack", 
                                               "breakfast", "lunch", "dinner", "recipe", "ingredient", "kitchen"]):
        user_themes.append("food")
    
    # Expanded color detection
    colors = ["red", "blue", "green", "yellow", "purple", "pink", "black", "white", "orange", "brown", 
              "teal", "turquoise", "magenta", "violet", "indigo", "gold", "silver", "bronze", "grey", "gray"]
    if any(color in user_message_lower for color in colors):
        user_themes.append("color")
        # Identify which specific color was mentioned
        for color in colors:
            if color in user_message_lower:
                user_themes.append(color)
    
    if any(word in user_message_lower for word in ["animal", "pet", "dog", "cat", "bird", "fish", "wild", "creature", "wolf", "fox", "lion", 
                                               "tiger", "bear", "elephant", "monkey", "gorilla", "rabbit", "snake", "lizard", "turtle", 
                                               "mammal", "reptile", "amphibian", "species", "zoo"]):
        user_themes.append("animal")
    
    if any(word in user_message_lower for word in ["travel", "place", "country", "beach", "mountain", "city", "town", "village", "island", 
                                               "continent", "europe", "asia", "africa", "america", "australia", "ocean", "sea", "lake", 
                                               "river", "forest", "jungle", "desert", "vacation", "holiday", "visit"]):
        user_themes.append("place")
    
    if any(word in user_message_lower for word in ["magic", "power", "superpower", "ability", "fantasy", "wizard", "witch", "fairy", "dragon", 
                                               "mythical", "legendary", "enchanted", "spell", "potion", "wand", "supernatural", "superhero", 
                                               "teleport", "invisible", "immortal", "transform", "telepathy", "telekinesis"]):
        user_themes.append("fantasy")
    
    if any(word in user_message_lower for word in ["music", "song", "melody", "rhythm", "beat", "tune", "instrument", "band", "artist", 
                                               "singer", "concert", "perform", "play", "guitar", "piano", "drums", "violin", "jazz", 
                                               "rock", "pop", "classical", "rap", "hip-hop"]):
        user_themes.append("music")
    
    if any(word in user_message_lower for word in ["game", "play", "fun", "video game", "board game", "console", "pc", "xbox", "playstation", 
                                               "nintendo", "mobile", "puzzle", "strategy", "rpg", "fps", "mmorpg", "competition", "score", 
                                               "level", "character", "player"]):
        user_themes.append("game")
    
    if any(word in user_message_lower for word in ["dream", "imagine", "wish", "hope", "future", "aspire", "goal", "vision", "creative", 
                                               "invent", "design", "build", "construct", "craft", "create", "imagination", "fantasy", 
                                               "daydream", "inspiration", "idea"]):
        user_themes.append("creative")
    
    # Follow-up specific responses - these are more generic but acknowledge continued conversation
    follow_up_responses = [
        "Thanks for sharing more! I appreciate how you're building on your previous thoughts. What else comes to mind about this topic? 🌟",
        "That adds such an interesting dimension to what you mentioned before! What influenced your thinking on this particular idea? ✨",
        "I love how you're developing these thoughts further! How do these ideas connect to your personal experiences? 💭",
        "That's a great follow-up to what you shared earlier! How has your perspective on this evolved over time? 🎨",
        "You've got me really thinking now! This conversation is getting more interesting with each exchange. What else do you think about this? 💫",
        "It's fascinating to see how your thoughts are unfolding! What other aspects of this topic interest you? 🌈",
        "The way you're approaching this conversation shows real depth of thought. What led you to explore this particular angle? 🧠",
        "I'm enjoying how this discussion is evolving! Your insights are quite thought-provoking. Have you always had these views? 💡",
        "This is turning into such an engaging conversation! I'm curious - what other perspectives have you considered on this topic? 🌱"
    ]
    
    # Theme-specific responses
    food_responses = [
        "That sounds absolutely delicious! I can almost taste the flavors you're describing. What inspired this culinary idea? 🍽️",
        "My taste buds are tingling just thinking about that! Is this something you've tried making yourself? 🥘",
        "What a mouthwatering description! Food really connects to our emotions and memories, doesn't it? What makes this particular food special to you? 🍰"
    ]
    
    color_responses = {
        "red": [
            "Red is such a powerful choice! It represents passion, energy, and determination. What aspects of red resonate with you most? ❤️",
            "Red is fascinating - it can symbolize both love and intensity. Does it hold any special meaning in your life? 🔥",
            "Red is the color of courage and strength! What draws you to this vibrant hue? 🌹"
        ],
        "blue": [
            "Blue is so calming and peaceful - like looking at the ocean on a clear day. What aspects of blue speak to you? 🌊",
            "Blue represents trust, loyalty, and wisdom. Does it have any particular significance to you? 💙",
            "Blue is the color of the vast sky and deep oceans - it reminds us that possibilities are endless. Why does this color stand out to you? ✨"
        ],
        "green": [
            "Green creates such perfect balance - just as nature creates harmony. What aspects of green do you connect with? 🌿",
            "Green represents growth, renewal, and abundance. Does this resonate with your personal philosophy? 🌱",
            "The human eye can distinguish more shades of green than any other color - perhaps because it's the color of life itself. What makes green special to you? 🌳"
        ],
        "yellow": [
            "Yellow radiates such happiness and optimism! What draws you to this bright color? ☀️",
            "Yellow stimulates mental activity and energy - it makes people feel so alive! What does yellow represent to you? 🌻",
            "Yellow symbolizes joy and intellectual energy. Does this reflect aspects of your personality? ✨"
        ],
        "purple": [
            "Purple creates such a magical balance between calm and energy. What aspects of purple appeal to you most? 👑",
            "Purple is relatively rare in nature, making it historically precious. What does this royal color mean to you? 💜",
            "Purple stimulates imagination and spirituality - it's the color of dreamers and visionaries. Does this resonate with your creative side? 🔮"
        ],
        "default": [
            "That color choice reveals something interesting about your personality! What draws you to that particular shade? 🎨",
            "Colors can reflect our inner emotional states so beautifully. What feelings does this color evoke for you? 🌈",
            "Your color preference is fascinating! Do you find yourself drawn to this color in other aspects of your life too? 🖌️"
        ]
    }
    
    animal_responses = [
        "What a fascinating creature choice! What qualities do you admire most about this animal? 🦊",
        "Nature's diversity is truly incredible, and that's such an interesting pick! What do you find most interesting about this animal? 🐘",
        "Animals can teach us so much about loyalty and adaptation. What lessons do you think we could learn from this animal? 🦁"
    ]
    
    place_responses = [
        "That location sounds absolutely breathtaking! What draws you most to this particular place? 🏝️",
        "What a wonderful destination choice! What kind of adventures would you have there? 🗻",
        "That's such a fascinating place! Would you visit just once or could you see yourself living there? 🌆"
    ]
    
    fantasy_responses = [
        "Your imagination is absolutely magical! What adventures would you embark on with that power? ✨",
        "What an enchanting idea! How would that magical element change your daily life? 🧙‍♂️",
        "That's brilliantly creative! What inspired this magical concept? 🔮"
    ]
    
    music_responses = [
        "Your musical taste is so interesting! What draws you to this particular sound? 🎵",
        "Music can be so deeply personal and meaningful. Does this music connect to specific memories for you? 🎸",
        "That's a fascinating musical choice! How did you discover this style? 🎧"
    ]
    
    game_responses = [
        "That sounds like such an engaging game concept! What aspects of gaming do you enjoy most? 🎮",
        "Your game idea shows real creativity! What unique mechanics would make this stand out? 🎲",
        "I love how you've thought about this game design! What inspired this concept? 🎯"
    ]
    
    creative_responses = [
        "Your creative thinking is truly impressive! What inspires your imagination? 💡",
        "That's such a unique and thoughtful creation! What process do you follow when developing ideas? 🎨",
        "Your imagination takes such interesting directions! What other creative outlets do you enjoy? ✨"
    ]
    
    # Generic responses as a fallback, but made more direct and ChatGPT-like
    general_responses = [
        "That's a really thoughtful answer! What inspired this perspective? 🌟",
        "I appreciate how unique your perspective is! What experiences shaped this outlook? ✨",
        "That's such an interesting way to look at it! What led you to this conclusion? 🌈",
        "I can tell you've given this real thought! How does this connect to your personal experiences? 💭",
        "Your perspective is so refreshing! What influences shaped this viewpoint? 💫",
        "That's such a compelling take on this! Have you always felt this way, or has your view evolved over time? 🌱",
        "I love the way you express your thoughts! What helped you develop such a clear perspective on this? 💫",
        "Your answer shows such depth of thought! Is this something you're particularly passionate about? 🔥",
        "That's an fascinating approach to the question! What factors influenced your thinking here? 🧠",
        "Your response is genuinely intriguing! Has this been something you've thought about before, or is it a new idea? 💡"
    ]
    
    # If it's a follow-up message, use the follow-up specific responses
    if is_follow_up:
        return random.choice(follow_up_responses)
    
    # If we identified the user mentioned a specific color, use the color-specific response
    for theme in user_themes:
        if theme in colors:
            color_key = theme if theme in color_responses else "default"
            return random.choice(color_responses[color_key])
    
    # If we identified a theme in the user's message, use a theme-specific response
    if "food" in user_themes:
        return random.choice(food_responses)
    elif "color" in user_themes:  # This is for general color talk, specific colors handled above
        return random.choice(color_responses["default"])
    elif "animal" in user_themes:
        return random.choice(animal_responses)
    elif "place" in user_themes:
        return random.choice(place_responses)
    elif "fantasy" in user_themes:
        return random.choice(fantasy_responses)
    elif "music" in user_themes:
        return random.choice(music_responses)
    elif "game" in user_themes:
        return random.choice(game_responses)
    elif "creative" in user_themes:
        return random.choice(creative_responses)
    
    # If we didn't identify a theme in the user's message, but we know the question context,
    # use a response related to the question's theme
    if question_context == "food":
        return random.choice(food_responses)
    elif question_context == "color":
        return random.choice(color_responses["default"])
    elif question_context == "animal":
        return random.choice(animal_responses)
    elif question_context == "place":
        return random.choice(place_responses)
    elif question_context == "fantasy":
        return random.choice(fantasy_responses)
    elif question_context == "creation" or question_context == "imagination":
        return random.choice(creative_responses)
    
    # If all else fails, use a general response
    return random.choice(general_responses)

def is_follow_up_message(user_id):
    """
    Check if this is a follow-up message from the user.
    
    Args:
        user_id: The Discord user ID
        
    Returns:
        bool: True if this is a follow-up message, False otherwise
    """
    return str(user_id) in conversation_history and "messages" in conversation_history[str(user_id)]

# Load conversation history on module import
load_conversation_history()