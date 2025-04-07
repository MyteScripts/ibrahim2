import os
import sys
from dotenv import load_dotenv
from ai_conversation import get_ai_response, is_follow_up_message

# Load environment variables
load_dotenv()

def test_ai_response():
    """Test the AI conversation system with a simple user message."""
    
    # Check if the OpenAI API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not found.")
        print("Please set the OPENAI_API_KEY environment variable and try again.")
        sys.exit(1)
    
    # Test user information
    user_id = "12345"
    username = "TestUser"
    
    # Sample hourly question
    question = "If you could invent a new dessert, what would it be and what would it taste like?"
    
    # Sample user response
    user_message = "I'd make a cloud cake that tastes like cotton candy but melts into vanilla ice cream when you eat it."
    
    print(f"Testing AI conversation with:\nUser: {username}\nQuestion: {question}\nUser message: {user_message}\n")
    
    # First message (not a follow-up)
    print("First response (not a follow-up):")
    response1 = get_ai_response(user_id, username, question, user_message, is_follow_up=False)
    print(f"AI: {response1}\n")
    
    # Check if this user is now in conversation history
    is_follow_up = is_follow_up_message(user_id)
    print(f"Is follow-up message check: {is_follow_up}")
    
    # Follow-up message
    if is_follow_up:
        follow_up_message = "Yes, and I'd make it change colors based on the temperature too!"
        print(f"\nFollow-up message: {follow_up_message}")
        
        response2 = get_ai_response(user_id, username, question, follow_up_message, is_follow_up=True)
        print(f"AI follow-up response: {response2}")

if __name__ == "__main__":
    test_ai_response()