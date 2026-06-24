import sys
from loguru import logger
from bot.config import Config
import os

# Ensure log directory exists
os.makedirs(Config.LOG_PATH, exist_ok=True)

# Remove default handler
logger.remove()

# Add console handler
logger.add(sys.stdout, format="{time} | {level} | {message}", level="DEBUG" if Config.DEBUG else "INFO")

# Add file handlers
logger.add(
    os.path.join(Config.LOG_PATH, "downloads.log"),
    rotation="1 day",
    retention="30 days",
    format="{time} | {level} | {message}",
    level="INFO"
)

logger.add(
    os.path.join(Config.LOG_PATH, "errors.log"),
    rotation="1 day",
    retention="30 days",
    format="{time} | {level} | {message}",
    level="ERROR"
)

logger.add(
    os.path.join(Config.LOG_PATH, "activity.log"),
    rotation="1 day",
    retention="30 days",
    format="{time} | {level} | {message}",
    level="INFO"
)

logger.add(
    os.path.join(Config.LOG_PATH, "admin.log"),
    rotation="1 day",
    retention="30 days",
    format="{time} | {level} | {message}",
    level="INFO"
)
