# tgfilestream - A Telegram bot that can stream Telegram files to users over HTTP.
# Copyright (C) 2019 Tulir Asokan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from typing import Tuple, Union

from telethon import events
from telethon.tl.custom import Message
from telethon.tl.types import TypeInputPeer, InputPeerChannel, InputPeerChat, InputPeerUser
from aiohttp import web

from .config import trust_headers

chat_id_bits = 64
chat_id_mask = (1 << chat_id_bits) - 1

msg_id_bits = 32
msg_id_mask = (1 << msg_id_bits) - 1

group_bit = 0b01
channel_bit = 0b10
chat_id_offset = 2
msg_id_offset = chat_id_bits + chat_id_offset


def pack_id(evt: events.NewMessage.Event) -> int:
    file_id = 0
    chat_id=evt.chat_id
    if evt.is_channel:
        file_id |= channel_bit
        chat_id -= - 1000000000000
    elif evt.is_group:
        file_id |= group_bit
        chat_id -= chat_id
    file_id |= evt.chat_id << chat_id_offset
    file_id |= evt.id << msg_id_offset
    return file_id


def unpack_id(file_id: int) -> Tuple[TypeInputPeer, int]:
    is_group = file_id & group_bit
    is_channel = file_id & channel_bit
    chat_id = file_id >> chat_id_offset & chat_id_mask
    msg_id = file_id >> msg_id_offset & msg_id_mask
    if is_channel:
        peer = InputPeerChannel(channel_id=chat_id, access_hash=0)
    elif is_group:
        peer = InputPeerChat(chat_id=chat_id)
    else:
        peer = InputPeerUser(user_id=chat_id, access_hash=0)
    return peer, msg_id


def get_file_name(message: Union[Message, events.NewMessage.Event]) -> str:
    if message.file.name:
        return message.file.name
    ext = message.file.ext or ""
    return f"{message.date.strftime('%Y-%m-%d_%H:%M:%S')}{ext}"


def get_requester_ip(req: web.Request) -> str:
    if trust_headers:
        try:
            return req.headers["X-Forwarded-For"]
        except KeyError:
            pass
    peername = req.transport.get_extra_info('peername')
    if peername is not None:
        return peername[0]
