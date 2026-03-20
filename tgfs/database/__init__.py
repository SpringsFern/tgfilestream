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

from os import environ
from typing import Any, Optional
from tgfs.config import Config
from tgfs.database.mongodb import MongoDB, MONGODB_CONFIG, MONGODB_REQUIRED
from tgfs.database.database import BaseStorage

class DBConfig:
    DB_LIST = {
        "mongodb": ("MONGODB", MONGODB_CONFIG, MONGODB_REQUIRED)
    }

    DB_CLASS: dict[str, type[BaseStorage]] = {
        "mongodb": MongoDB,
    }

    @staticmethod
    def load_backend_config(
        prefix: str,
        schema: dict[str, tuple[type, Any]],
        required: set[str],
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        missing: list[str] = []

        for key, (typ, default) in schema.items():
            env_key = f"{prefix}_{key.upper()}"

            if env_key in environ:
                kwargs[key] = typ(environ[env_key])
            elif default is not None:
                kwargs[key] = default
            else:
                missing.append(env_key)

        if set(missing) & required:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        return kwargs


class DB:
    MIN_VERSION: str
    db: Optional[BaseStorage] = None
    config: dict

    @classmethod
    def load_config(cls):
        if Config.DB_BACKEND in DBConfig.DB_LIST:
            cls.config: dict = DBConfig.load_backend_config(*DBConfig.DB_LIST[Config.DB_BACKEND])
        else:
            raise RuntimeError(
                f"Unsupported DB_BACKEND '{Config.DB_BACKEND}'. "
                f"Valid options: {DBConfig.DB_LIST.keys()}"
            )

    @classmethod
    async def init(cls) -> None:
        if cls.db is None:
            backend = Config.DB_BACKEND
            db_cls = DBConfig.DB_CLASS[backend]
            cls.db = db_cls()
            cls.MIN_VERSION = cls.db.MIN_VERSION

        await cls.db.connect(**cls.config)
        await cls.db.init_db()

    @classmethod
    async def close(cls):
        if cls.db:
            await cls.db.close()
            cls.db = None
