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

from typing import Optional
from tgfs.config import Config
from tgfs.database.mysql import MySQLDB
from tgfs.database.mongodb import MongoDB
from tgfs.database.database import BaseStorage

_BACKENDS: dict[str, type[BaseStorage]] = {
    "mysql": MySQLDB,
    "mongodb": MongoDB,
}

class DB:
    db: Optional[BaseStorage] = None
    config: dict

    @classmethod
    def load_config(cls):
        if Config.DB_BACKEND in Config.DB_LIST:
            cls.config: dict = Config.load_backend_config(*Config.DB_LIST[Config.DB_BACKEND])
        else:
            raise RuntimeError(
                f"Unsupported DB_BACKEND '{Config.DB_BACKEND}'. "
                f"Valid options: {Config.DB_LIST.keys()}"
            )

    @classmethod
    async def init(cls) -> None:
        if cls.db is None:
            backend = Config.DB_BACKEND
            db_cls = _BACKENDS[backend]
            cls.db = db_cls()

        await cls.db.connect(**cls.config)
        await cls.db.init_db()

    @classmethod
    async def close(cls):
        if cls.db:
            await cls.db.close()
            cls.db = None
