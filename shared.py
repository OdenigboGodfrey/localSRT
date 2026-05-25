import asyncio


async def broadcast(data: dict, clients_lock, clients):
    async with clients_lock:
        dead = []

        for ws in clients:
            try:
                await ws.send_json(data)
            except:
                dead.append(ws)

        for ws in dead:
            clients.remove(ws)

def broadcast_sync(loop, data: dict, clients_lock, clients):
    asyncio.run_coroutine_threadsafe(
        broadcast(data, clients_lock, clients),
        loop
    )
