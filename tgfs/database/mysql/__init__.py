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

import warnings
import importlib.util
from pathlib import Path

import aiomysql

from .file import FileDB
from .user import UserDB
from .group import GroupDB
from .utils import UtilDB

SUPPORTED_VERSION = "0.0.2"

def read_sql_file(path: Path) -> list[str]:
    sql = Path(path).read_text(encoding="utf-8")
    statements = []
    buffer = []

    for line in sql.splitlines():
        line = line.strip()
        if not line or line.startswith("--"):
            continue

        buffer.append(line)
        if line.endswith(";"):
            statements.append(" ".join(buffer))
            buffer.clear()

    return statements

def parse_version(v: str):
    return tuple(map(int, v.split(".")))

def extract_range(file: Path):
    name = file.stem
    left, right = name.split("_to_")

    from_v = left[1:].replace("_", ".")
    to_v = right[1:].replace("_", ".")

    return parse_version(from_v), parse_version(to_v), from_v, to_v

class MySQLDB(FileDB, GroupDB, UserDB, UtilDB):
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

    async def init_db(self) -> None:
        statements = read_sql_file(Path(__file__).resolve().parent / "schema.sql")

        async with self._pool.acquire() as conn:
            warnings.filterwarnings('ignore', module=r"aiomysql")
            async with conn.cursor() as cur:
                for stmt in statements:
                    await cur.execute(stmt)
                await conn.commit()
            warnings.filterwarnings('default', module=r"aiomysql")

    async def migrate(self, current: str, target: str) -> bool:
        migration_dir = Path(__file__).resolve().parent / "migration"

        current_v = parse_version(current)
        target_v = parse_version(target)
        supported_v = parse_version(SUPPORTED_VERSION)
        if supported_v < target_v:
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
