# filestream

from os import environ
from aiohttp import web
async def stats(request):
    return web.json_response({"Hi": "Hello"})

app = web.Application()
app.add_routes([web.get('/', stats)])

if __name__ == "__main__":
    web.run_app(app, host='0.0.0.0', port=int(environ.get("PORT")))