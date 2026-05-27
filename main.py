import asyncio
import time
import os
import signal
import webbrowser
import threading
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
import tkinter as tk
from tkinter import filedialog
from core import process_srt_job_with_progress
from fastapi import WebSocket
from contextlib import asynccontextmanager

from shared import resource_path

port = 3555
event_loop = None

# -----
# Monitor web socket connections and auto kill the app when there's no active connection
# -----
last_seen = time.time()


def monitor():
    while True:
        time.sleep(5)
        if active_connections == 0 and (time.time() - last_seen >= 5):
            print("No browser for 5s. Shutting down.")
            os.kill(os.getpid(), signal.SIGTERM)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global event_loop
    event_loop = asyncio.get_running_loop()

    monitor_thread = threading.Thread(
        target=monitor,
        daemon=True
    )
    monitor_thread.start()

    print("Server starting...")

    yield

    print("Server shutting down...")


app = FastAPI(lifespan=lifespan)
clients = set()
clients_lock = asyncio.Lock()

progress_store = {
    "current": 0,
    "total": 1,
    "status": "idle",
    "total_files": 0,
    "current_file": 0
}

# -----------------------------
# UI
# -----------------------------
@app.get("/")
def home():
    with open(
        resource_path("ui/index.html"),
        "r",
        encoding="utf-8"
    ) as f:
        return HTMLResponse(f.read())


# -----------------------------
# File picker
# -----------------------------
@app.get("/select-file")
def select_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    path = filedialog.askopenfilename(
        title="Select Video File",
        filetypes=[
            ("Video Files", "*.mp4 *.mkv *.avi *.mov")
        ]
    )

    root.destroy()

    return {"path": path}


# -----------------------------
# Folder picker
# -----------------------------
@app.get("/select-folder")
def select_folder():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    path = filedialog.askdirectory(title="Select Folder")

    root.destroy()

    return {"path": path}


# -----------------------------
# Run job
# -----------------------------
class JobRequest(BaseModel):
    path: str
    chunk_length: int
    model_size: str


@app.post("/run")
def run_job(req: JobRequest):
    if progress_store["status"] != "idle":
        raise HTTPException(status_code=400, detail="Job already running")

    def worker():
        process_srt_job_with_progress(
            req.path,
            req.chunk_length,
            req.model_size,
            progress_store,
            event_loop,
            clients_lock,
            clients
        )

    progress_store["status"] = "running"

    threading.Thread(target=worker).start()

    return {"status": "started"}

@app.get("/progress")
def get_progress():
    return progress_store

# -----------------------------
# Websocket
# -----------------------------
active_connections = 0
@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    global active_connections, last_seen

    await websocket.accept()
    active_connections += 1
    last_seen = time.time()

    async with clients_lock:
        clients.add(websocket)

    try:
        while True:
            # keep connection alive
            await websocket.receive_text()
            last_seen = time.time()
    except Exception as e:
        # print(f"[WS exception caught] {e}")
        pass
    finally:
        async with clients_lock:
            clients.remove(websocket)
            active_connections -= 1
            last_seen = time.time()




# -----------------------------
# Auto open browser
# -----------------------------
def open_browser():
    webbrowser.open(f"http://127.0.0.1:{port}")

if __name__ == "__main__":
    threading.Timer(1.5, open_browser).start() 
    uvicorn.run(app, host="127.0.0.1", port=port)