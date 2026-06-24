from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from bot.config import Config

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(Config.MONGO_URI)
        self.db = self.client[Config.DB_NAME]
        self.users = self.db.users
        self.downloads = self.db.downloads
        self.logs = self.db.logs
        self.global_cookies = self.db.global_cookies

    async def init_indexes(self):
        await self.users.create_index("user_id", unique=True)
        await self.users.create_index("premium_expiry")
        await self.downloads.create_index("user_id")
        await self.downloads.create_index("timestamp")
        await self.logs.create_index("user_id")
        await self.logs.create_index("timestamp")
        await self.global_cookies.create_index("type")

db = Database()
