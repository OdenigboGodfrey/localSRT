import asyncio
import os
import webbrowser
import threading
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
import tkinter as tk
from tkinter import filedialog
from core import process_srt_job
from core import process_srt_job_with_progress
import threading
from fastapi import WebSocket
from contextlib import asynccontextmanager

port = 3555
event_loop = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global event_loop
    event_loop = asyncio.get_running_loop()
    print("Server starting...")

    yield

    print("Server shutting down...")


app = FastAPI(lifespan=lifespan)
clients = set()
clients_lock = asyncio.Lock()

progress_store = {
    "current": 0,
    "total": 1,
    "status": "idle"
}

# -----------------------------
# UI
# -----------------------------
@app.get("/")
def home():
    with open("ui/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)


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
@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()

    async with clients_lock:
        clients.add(websocket)

    try:
        while True:
            # keep connection alive
            await websocket.receive_text()
    except:
        pass
    finally:
        async with clients_lock:
            clients.remove(websocket)



# -----------------------------
# Auto open browser
# -----------------------------
def open_browser():
    webbrowser.open(f"http://127.0.0.1:{port}")

if __name__ == "__main__":
    threading.Timer(1.5, open_browser).start() 
    uvicorn.run(app, host="127.0.0.1", port=port)