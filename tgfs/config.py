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

import argparse
import logging
from os import environ
from pathlib import Path
from typing import Optional

from tgfs.utils.config_utils import ConfigBase

log = logging.getLogger(__name__)

parser = argparse.ArgumentParser(
    prog="tgfilestream", description="tgfilestream server",)
parser.add_argument("--host", help="Bind host")
parser.add_argument("--port", type=int, help="Bind port")
parser.add_argument("--public-url", help="Public base URL")
parser.add_argument("--connection-limit", type=int, help="Max concurrent connections")
parser.add_argument("--db-backend", help="Database server", choices=["mongodb"])
parser.add_argument("--no-update", action="store_true", help="Ignore Telegram Updates")
parser.add_argument("--no-main", action="store_true",
    help="Skip main bot and use only worker bots for Telegram file requests")
parser.add_argument("--env", nargs="+", help="path(s) to .env files", default=[".env"])
args = parser.parse_args()

try:
    from dotenv import load_dotenv
    for env_path in args.env:
        load_dotenv(env_path)
except ImportError:
    log.warning("python-dotenv not installed. Skipping .env loading.")

class Config(ConfigBase):
    # ---------- Telegram ----------
    API_ID: int = int(environ["API_ID"])
    API_HASH: str = environ["API_HASH"]
    BOT_TOKEN: str = environ["BOT_TOKEN"]

    BIN_CHANNEL: int = int(environ["BIN_CHANNEL"])
    TOKENS: list[str] = ConfigBase.get_multi_client_tokens()

    # ---------- Server ----------
    HOST: str = args.host or environ.get("HOST", "0.0.0.0")
    PORT: int = args.port or ConfigBase.env_int("PORT", 8080)
    PUBLIC_URL: str = args.public_url or environ.get("PUBLIC_URL", f"http://{HOST}:{PORT}")

    CONNECTION_LIMIT: int = args.connection_limit or ConfigBase.env_int("CONNECTION_LIMIT", 5)

    DOWNLOAD_PART_SIZE: int = ConfigBase.env_int(
        "DOWNLOAD_PART_SIZE", 1024 * 1024
    )

    # ---------- Bot behavior ----------
    NO_UPDATE: bool = args.no_update or ConfigBase.env_bool("NO_UPDATE")
    NO_MAIN: bool = args.no_main or ConfigBase.env_bool("NO_MAIN")
    SEQUENTIAL_UPDATES: bool = ConfigBase.env_bool("SEQUENTIAL_UPDATES")
    FILE_INDEX_LIMIT: int = ConfigBase.env_int("FILE_INDEX_LIMIT", 10)
    MAX_WARNS: int = ConfigBase.env_int("MAX_WARNS", 3)

    ADMIN_IDS: set[int] = {
        int(x)
        for x in environ.get("ADMIN_IDS", "").split(",")
        if x.strip().isdigit()
    }
    ALLOWED_IDS: set[int] = {
        int(x)
        for x in environ.get("ALLOWED_IDS", "").split(",")
        if x.strip().isdigit()
    }
    if ALLOWED_IDS:
        ALLOWED_IDS = ALLOWED_IDS | ADMIN_IDS

    # ---------- DB ----------
    DB_BACKEND: str = args.db_backend or environ.get("DB_BACKEND", "mongodb").lower()

    SESSION_NAME: str = str(PORT)

    # ---------- Extras ----------
    DEBUG: bool = ConfigBase.env_bool("DEBUG")
    EXT_DEBUG: bool = ConfigBase.env_bool("EXT_DEBUG")
    PATCH_PATH: str = environ.get("PATCH_PATH", "tgfs/patches")
    CACHE_DIR = Path("cache")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ---------- Security ----------
    SECRET: Optional[bytes] = None
    BOT_ID: Optional[int] = None
