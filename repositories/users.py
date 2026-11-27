from db.mongo import get_collection

class UserRepository:
    
    async def upsert_user(self, telegram_id:int, name: str):
        collection = get_collection("users")
        return await collection.update_one(
            {"telegram_id":telegram_id},
            {"$set": {"name":name}},
            upsert=True
        )