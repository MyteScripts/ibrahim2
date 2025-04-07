# Hourly Questions System

## Overview

The Hourly Questions system automatically sends engaging questions to a designated channel every hour, pinging a specified role to encourage community interaction. Questions are designed to spark fun, creative conversations among server members.

## Features

- Automatically posts a random question every hour
- Pings a specified role to notify users
- AI-powered conversation responses using OpenAI API
- Natural, contextual follow-up conversations with users
- Conversation memory to provide coherent multi-turn dialogue
- Fallback to intelligent templates when API is unavailable
- Manual question triggering with admin command
- Configurable schedule with persistence across bot restarts

## Configuration

- Target channel: Set in the `HourlyQuestionsCog` initialization
- Role to ping: Set in the `HourlyQuestionsCog` initialization
- Question database: Defined in `QUESTIONS` array
- Timing: Automatically schedules the next question after each post

## AI Conversation Integration

The hourly questions system is integrated with an AI-powered conversation system that:

1. Responds to user replies with natural, contextual messages
2. Maintains conversation memory for follow-up responses
3. Adds typing indicators for a more natural feel
4. Uses OpenAI's GPT-4o model (with intelligent fallback)
5. Adapts to topics in user messages for more relevant responses

## Commands

- `/ask_question`: Manually trigger a random question (Admin only)
- `/hourlyquestion`: Send a custom question of your choice (Admin only)

## Files

- `hourly_questions.py`: Main implementation
- `ai_conversation.py`: AI response generation
- `data/hourly_questions_timer.json`: Persistent timer data
- `data/conversation_history.json`: Stored conversation context

## Implementation Details

- Questions are embedded with a distinctive format
- Users reply directly to question messages
- Bot detects replies and uses AI to respond contextually
- Conversation flows continue naturally with follow-up exchanges
- System gracefully handles API failures with fallback responses

## Required Environment Variables

- `OPENAI_API_KEY`: For AI-powered responses (falls back gracefully if missing)

See also: [AI_CONVERSATION.md](./AI_CONVERSATION.md) for more details on the AI conversation system.
