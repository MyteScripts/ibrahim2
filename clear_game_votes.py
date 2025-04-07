import sqlite3
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('clear_game_votes')

DB_PATH = 'data/leveling.db'

def clear_active_game_votes():
    """Clear all active game votes from the database."""
    try:
        # Verify the database exists
        if not os.path.exists(DB_PATH):
            logger.error(f"Database file {DB_PATH} does not exist")
            return False
            
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if the game_votes table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='game_votes'")
        if not cursor.fetchone():
            logger.error("game_votes table does not exist in the database")
            conn.close()
            return False
        
        # Get current active votes
        cursor.execute("SELECT id, channel_id, message_id FROM game_votes WHERE is_active = 1")
        active_votes = cursor.fetchall()
        
        if not active_votes:
            logger.info("No active game votes found in database")
            conn.close()
            return True
        
        # Update all active votes to inactive
        cursor.execute("UPDATE game_votes SET is_active = 0 WHERE is_active = 1")
        conn.commit()
        
        logger.info(f"Successfully deactivated {len(active_votes)} game votes")
        
        # Print details of deactivated votes
        for vote_id, channel_id, message_id in active_votes:
            logger.info(f"Deactivated vote ID: {vote_id}, Channel: {channel_id}, Message: {message_id}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error clearing active game votes: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting to clear active game votes...")
    success = clear_active_game_votes()
    
    if success:
        logger.info("Successfully cleared all active game votes")
    else:
        logger.error("Failed to clear active game votes")