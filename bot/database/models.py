from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from bot.config import Config
import asyncio
from bot.utils.logger import logger

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self._connected = False
        
    async def connect(self):
        """Lazy connection to MongoDB with retries"""
        if self._connected:
            return
        
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to MongoDB... (attempt {attempt + 1}/{max_retries})")
                self.client = AsyncIOMotorClient(
                    Config.MONGO_URI,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                    socketTimeoutMS=5000
                )
                # Test connection
                await self.client.admin.command('ping')
                self.db = self.client[Config.DB_NAME]
                self._connected = True
                await self.init_indexes()
                logger.info("✅ MongoDB connected successfully!")
                return
            except Exception as e:
                logger.error(f"MongoDB connection attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
    
    async def init_indexes(self):
        if not self._connected:
            return
        try:
            await self.db.users.create_index("user_id", unique=True)
            await self.db.users.create_index("premium_expiry")
            await self.db.downloads.create_index("user_id")
            await self.db.downloads.create_index("timestamp")
            await self.db.logs.create_index("user_id")
            await self.db.logs.create_index("timestamp")
            await self.db.global_cookies.create_index("type")
            logger.info("✅ Database indexes created")
        except Exception as e:
            logger.error(f"Index creation failed: {e}")

# Create singleton with lazy connection
db = Database()
