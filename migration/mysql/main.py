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
import json
from typing import Optional, Union
import importlib.util
from pathlib import Path

import aiomysql

SUPPORTED_VERSION = "0.0.2"

SupportedType = Union[bytes, bool, int, str, list, dict]

def encode_value(value: SupportedType) -> tuple[bytes, str]:
    if isinstance(value, bytes):
        return value, "bytes"

    if isinstance(value, str):
        return value.encode("utf-8"), "str"

    if isinstance(value, bool):
        return (b"\x01" if value else b"\x00"), "bool"

    if isinstance(value, int):
        size = max(1, (value.bit_length() + 7) // 8)
        return value.to_bytes(size, "big", signed=True), "int"

    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":")).encode("utf-8"), "json"

    raise TypeError(f"Unsupported type: {type(value)}")

def decode_value(data: bytes, vtype: str) -> SupportedType:
    if vtype == "bytes":
        return data

    if vtype == "str":
        return data.decode("utf-8")

    if vtype == "bool":
        return data != b"\x00"

    if vtype == "int":
        return int.from_bytes(data, "big", signed=True)

    if vtype == "json":
        return json.loads(data.decode("utf-8"))

    raise ValueError(f"Unknown type: {vtype}")

def parse_version(v: str):
    return tuple(map(int, v.split(".")))

def extract_range(file: Path):
    name = file.stem
    left, right = name.split("_to_")

    from_v = left[1:].replace("_", ".")
    to_v = right[1:].replace("_", ".")

    return parse_version(from_v), parse_version(to_v), from_v, to_v

class MySQLDB():
    _pool: aiomysql.Pool
    is_connected: bool = False

    async def connect(self, *, host: str, port: int = 3306, user: str, password: str,  # pylint: disable=W0221
                          db: str, minsize: int = 1, maxsize: int = 10, autocommit: bool = False,
                          connect_timeout: int = 10) -> None:
        if not self.is_connected:
            self._pool = await aiomysql.create_pool(
                host=host, port=port, user=user, password=password, db=db,
                minsize=minsize, maxsize=maxsize, autocommit=autocommit,
                connect_timeout=connect_timeout, charset="utf8mb4"
            )
            self.is_connected = True

    async def close(self, force: bool = False) -> None:
        if self.is_connected or force:
            self._pool.close()
            await self._pool.wait_closed()
            self.is_connected = False

    async def get_config_value(self, key: str) -> Optional[SupportedType]:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT v, type FROM APP_CONFIG WHERE k = %s",
                    (key,)
                )
                row = await cur.fetchone()
                if not row:
                    return None

                data, vtype = row
                return decode_value(data, vtype)

    async def set_config_value(self, key: str, value: SupportedType) -> None:
        data, vtype = encode_value(value)

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        """
                        INSERT INTO APP_CONFIG (k, v, type)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                          v = VALUES(v),
                          type = VALUES(type)
                        """,
                        (key, data, vtype)
                    )
                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    raise

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
    print("Enter MySQL Server Connection Details")
    host: str = input("Host: ")
    port: int = 3306
    port_str = input("Port [Default: 3306]: ")
    if port_str.isdigit():
        port=int(port_str)
    user: str = input("Username: ")
    password: str = input("Password: ")
    db_name: str = input("Database Name: ")
    db = MySQLDB()
    await db.connect(host=host, port=port, user=user, password=password, db=db_name)
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
