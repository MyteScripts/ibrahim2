import asyncio
import os
import sys
from minimal_bot import initialize_bot
from logger import setup_logger

logger = setup_logger('main')

if __name__ == "__main__":
    try:
        # Check for DATABASE_URL for database sync, but proceed even if it's missing
        if not os.environ.get('DATABASE_URL'):
            logger.warning("DATABASE_URL environment variable not found! Database sync features will be disabled.")
            logger.warning("The bot will still function normally, but automated database synchronization will not be available.")
            logger.warning("To enable database sync, please set up the DATABASE_URL environment variable.")
        
        # Run the bot
        logger.info("Starting Discord bot...")
        asyncio.run(initialize_bot())
    except Exception as e:
        logger.critical(f"Fatal error occurred: {e}")
        sys.exit(1)