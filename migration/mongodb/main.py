# tgfilestream
# Copyright (C) 2025-2026 Deekshith SH

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import asyncio
import importlib.util
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection

SUPPORTED_VERSION = "0.0.2"

def parse_version(v: str):
    return tuple(map(int, v.split(".")))

def extract_range(file: Path):
    name = file.stem
    left, right = name.split("_to_")

    from_v = left[1:].replace("_", ".")
    to_v = right[1:].replace("_", ".")

    return parse_version(from_v), parse_version(to_v), from_v, to_v

class MongoDB():
    is_connected: bool = False
    client: AsyncIOMotorClient
    db: AsyncIOMotorDatabase
    files: AsyncIOMotorCollection
    groups: AsyncIOMotorCollection
    users: AsyncIOMotorCollection
    config: AsyncIOMotorCollection

    async def connect(self, uri: str, dbname) -> None: # pylint: disable=W0221
        if not self.is_connected:
            self.client = AsyncIOMotorClient(uri)
            self.is_connected = True
        self.db = self.client[dbname]

        self.files  = self.db.files
        self.groups = self.db.groups
        self.users  = self.db.users
        self.config = self.db.app_config

    async def close(self, force: bool = False) -> None:
        if self.is_connected or force:
            self.client.close()
            self.is_connected = False

    async def get_config_value(self, key: str):
        doc = await self.config.find_one({"_id": key})
        return doc["value"] if doc else None

    async def set_config_value(self, key: str, value):
        await self.config.update_one(
            {"_id": key},
            {"$set": {"value": value}},
            upsert=True,
        )

    async def migrate(self, current: str, target: str) -> bool:
        migration_dir = Path(__file__).resolve().parent / "migration"

        current_v = parse_version(current)
        target_v = parse_version(target)
        if target_v < current_v:
            print(f"Current version {current} is grater than traget version {target}")
            return False

        while current_v < target_v:
            candidates = []

            for file in migration_dir.glob("v*_to_v*.py"):
                from_v, to_v, _, _ = extract_range(file)

                if from_v <= current_v < to_v:
                    candidates.append((to_v, file))

            if not candidates:
                return

            candidates.sort(key=lambda x: x[0])
            next_v, file = candidates[0]

            spec = importlib.util.spec_from_file_location(file.stem.replace(".", "_"), file)
            start = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(start)
            await start.run(self)

            current_v = next_v
        return True

async def main():
    print("Enter Mongodb Server Connection Details")
    mongo_uri: str = input("MongoDB URI: ")
    db_name: str = input("Database Name [default: TGFS]: ")
    db = MongoDB()
    await db.connect(uri=mongo_uri, dbname=db_name)
    version = await db.get_config_value("VERSION")
    if not version:
        print("Version not found in database")
        return
    status = await db.migrate(version, SUPPORTED_VERSION)
    await db.set_config_value("OLD_VERSION", version)
    await db.set_config_value("VERSION", SUPPORTED_VERSION)
    await db.close()
    if status:
        print("Database Migration Completed")
    else:
        print("Database Migration Failed")

if __name__ == "__main__":
    asyncio.run(main())
