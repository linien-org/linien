#!/usr/bin/env python
import asyncio
import websockets

async def hello():
    async with websockets.connect(
        'ws://192.168.0.95:8765'
    ) as websocket:
        while True:
            greeting = await websocket.recv()
            print(f"< {greeting}")

asyncio.get_event_loop().run_until_complete(hello())
