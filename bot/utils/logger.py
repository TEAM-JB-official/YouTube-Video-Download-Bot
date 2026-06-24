import sys
from loguru import logger
from bot.config import Config
import os

logger.remove()
logger.add(sys.stdout, format="{time} | {level} | {message}", level="DEBUG" if Config.DEBUG else "INFO")
logger.add(
    os.path.join(Config.LOG_PATH, "downloads.log"),
    rotation="1 day", retention="30 days",
    format="{time} | {level} | {message}", level="INFO"
)
logger.add(
    os.path.join(Config.LOG_PATH, "errors.log"),
    rotation="1 day", retention="30 days",
    format="{time} | {level} | {message}", level="ERROR"
)
logger.add(
    os.path.join(Config.LOG_PATH, "activity.log"),
    rotation="1 day", retention="30 days",
    format="{time} | {level} | {message}", level="INFO"
)
logger.add(
    os.path.join(Config.LOG_PATH, "admin.log"),
    rotation="1 day", retention="30 days",
    format="{time} | {level} | {message}", level="INFO"
)
