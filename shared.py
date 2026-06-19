import asyncio
import os
import sys

APP_NAME = "LocalSRT"

progress_store = {
    "current": 0,
    "total": 1,
    "status": "idle",
    "total_files": 0,
    "current_file": 0
}

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
    # asyncio.run_coroutine_threadsafe(
    #     broadcast(data, clients_lock, clients),
    #     loop
    # )
    pass

def resource_path(relative_path):
    base_path = getattr(
        sys,
        "_MEIPASS",
        os.path.abspath(".")
    )

    return os.path.join(base_path, relative_path)
