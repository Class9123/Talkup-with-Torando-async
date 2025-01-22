import motor.motor_asyncio
import asyncio
from datetime import datetime
from values import DEV_MONGO_URI, DB_NAME 

class AsyncMongodb:
    def __init__(self, uri, db_name):
        self.uri = uri
        self.db_name = db_name

    async def connect(self):
        try:
            client = motor.motor_asyncio.AsyncIOMotorClient(self.uri)
            self.db = client[self.db_name]
            print("Connected successfully")
            collections = await self.db.list_collection_names()
            print(f"Available collections are {collections}")
        except Exception as e:
            raise ValueError(f"Cannot connect with {self.uri}. Error: {e}")
        self.users = self.db["Users"]
        self.messages = self.db["Messages"]

    async def add_user(self, user):
        # user = {name: "John Doe", password: "password123", email: "email@example.com", friends: [id, ...], status: "online"}
        result = await self.users.insert_one(user)
        return result.inserted_id

    async def find_user(self, data):
        return await self.users.find_one(data)

    async def add_message(self, senderId, receiverId, time, text="", url=""):
        message = {
            "senderId": senderId,
            "receiverId": receiverId,
            "text": text,
            "image": url,
            "time": time,
            "timestamp": datetime.utcnow()
        }
        result = await self.messages.insert_one(message)
        return result.inserted_id

    async def get_messages(self, userId, friendId):
        cursor = self.messages.find(
            {
                "$or": [
                    {"senderId": userId, "receiverId": friendId},
                    {"senderId": friendId, "receiverId": userId}
                ]
            },
            {"_id": 0, "timestamp": 0}  # Exclude the "_id" and "timestamp" field
        ).sort("timestamp", 1)
        return await cursor.to_list(length=None)
