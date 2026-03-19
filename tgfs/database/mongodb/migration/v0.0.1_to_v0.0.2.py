from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

async def run(mongo_db):
    db: AsyncIOMotorDatabase = mongo_db.db
    db_files: AsyncIOMotorCollection = db.files
    await db_files.update_many(
        {"is_deleted": {"$exists": True}},
        {"$rename": {"is_deleted": "is_restricted"}}
    )
