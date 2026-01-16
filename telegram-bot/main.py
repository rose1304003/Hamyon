"""
Hamyon - Main Entry Point
Runs both the Telegram Bot and REST API server
"""

import os
import sys
import logging
import threading
from database import init_database

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def run_bot():
    """Run the Telegram bot."""
    from bot import main as bot_main
    bot_main()


def run_api():
    """Run the Flask API server."""
    from api import app
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


def main():
    """Main entry point."""
    # Initialize database first
    logger.info("Initializing database...")
    init_database()
    logger.info("Database initialized successfully!")
    
    # Check what mode to run
    mode = os.getenv('RUN_MODE', 'both').lower()
    
    if mode == 'bot':
        logger.info("Starting Telegram Bot only...")
        run_bot()
    elif mode == 'api':
        logger.info("Starting API server only...")
        run_api()
    else:
        # Run both in separate threads
        logger.info("Starting both Bot and API server...")
        
        # Start API in a thread
        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()
        logger.info("API server started in background")
        
        # Run bot in main thread (it has its own event loop)
        run_bot()


if __name__ == '__main__':
    main()
