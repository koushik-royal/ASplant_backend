import asyncio
import websockets

async def test():
    try:
        async with websockets.connect('ws://127.0.0.1:8000/ws/admin') as ws:
            print('Connected!')
    except Exception as e:
        print('Error:', e)

asyncio.run(test())
