# AI Conversation System

## Overview

The AI conversation system enhances the Hourly Questions feature by providing natural, contextual responses to users who reply to the bot's questions. This creates a more engaging and interactive experience than template-based responses.

## Features

- Uses OpenAI's GPT-4o model for generating contextual responses
- Maintains conversation history to provide context-aware replies
- Graceful fallback to template-based responses when API is unavailable
- Context-aware fallback responses based on message content
- Separate response patterns for initial replies and follow-up messages
- Regular pruning of conversation history to manage storage

## How It Works

1. When a user replies to an hourly question, the system checks if it's an initial reply or a follow-up message
2. User messages and bot responses are stored in conversation history
3. When generating a response, the system:
   - Tries to use the OpenAI API first with appropriate context
   - Falls back to intelligent template responses if API is unavailable
   - Uses keywords in the user's message to provide contextual responses
   - Stores the interaction in conversation history regardless of API success

## Files Involved

- `ai_conversation.py`: Main implementation of the AI conversation system
- `hourly_questions.py`: Integration with the hourly questions feature
- `data/conversation_history.json`: Storage for conversation histories

## Environment Requirements

- `OPENAI_API_KEY`: Required environment variable for API access

## Fallback Mechanism

The system includes a sophisticated fallback mechanism that:

1. Detects common topics (food, colors, animals, places, etc.)
2. Provides appropriate contextual responses for those topics
3. Uses different response patterns for initial vs. follow-up messages
4. Always encourages further conversation with engaging questions

## Usage Considerations

- API usage is kept efficient through:
  - Limiting token count to 150 for responses
  - Pruning conversation history to only recent messages
  - Using a temperature of 0.7 for balanced creativity and coherence

## Testing

Use `test_ai_conversation.py` to test the system functionality:

```
python test_ai_conversation.py
```

This script demonstrates:
- Initial response generation
- Follow-up response handling
- Conversation history tracking
- Fallback response patterns
