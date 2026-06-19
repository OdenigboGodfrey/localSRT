import asyncio
import subprocess
import os
import tempfile
import shutil
from faster_whisper import WhisperModel
from ffmpeg_binary_manager import get_ffmpeg_binary
import math

FFMPEG = get_ffmpeg_binary("ffmpeg")
FFPROBE = get_ffmpeg_binary("ffprobe")

SAMPLE_RATE = 16000
OVERLAP = 5

WHISPER_CACHE = None

ALLOWED_EXTENSIONS = [
    ".mp4",
    ".mkv",
    ".avi",
    ".mov"
]


def format_time(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02}:{mins:02}:{secs:02},{ms:03}"


def extract_audio(video, output):
    subprocess.run([
        FFMPEG, "-y", "-i", video,
        "-ac", "1", "-ar", str(SAMPLE_RATE),
        output
    ], check=True)


def get_duration(audio):
    result = subprocess.run([
        FFPROBE, "-i", audio,
        "-show_entries", "format=duration",
        "-v", "quiet",
        "-of", "csv=p=0"
    ], capture_output=True, text=True)

    return float(result.stdout.strip())


def load_model(size):
    global WHISPER_CACHE
    if WHISPER_CACHE is None or WHISPER_CACHE["size"] != size:
        WHISPER_CACHE = {
            "size": size,
            "model": WhisperModel(size, device="cpu", compute_type="int8")
        }
    return WHISPER_CACHE["model"]
    

def process_srt_job(selected_path, chunk_length, model_size, progress, progress_callback=None):

    audio_file = os.path.join(tempfile.gettempdir(), "localsrt_audio.wav")
    chunks_dir = os.path.join(tempfile.gettempdir(), "localsrt_chunks")
    output_srt = os.path.splitext(selected_path)[0] + ".srt"
    filename = os.path.basename(selected_path)

    if os.path.exists(output_srt):
        progress["status"] = f"Skipping {filename} (SRT exists)"
        if progress_callback:
            progress_callback(progress.copy())
        return output_srt

    if os.path.exists(chunks_dir):
        shutil.rmtree(chunks_dir)

    os.makedirs(chunks_dir, exist_ok=True)

    extract_audio(selected_path, audio_file)

    duration = get_duration(audio_file)
    step = max(1, chunk_length - OVERLAP)
    num_chunks = math.ceil(duration / step)

    model = load_model(model_size)

    index = 1

    with open(output_srt, "w", encoding="utf-8") as f:

        for i in range(num_chunks):

            start = i * step
            chunk_path = os.path.join(chunks_dir, f"c{i}.wav")

            subprocess.run([
                FFMPEG, "-y",
                "-i", audio_file,
                "-ss", str(start),
                "-t", str(chunk_length),
                "-ac", "1",
                "-ar", str(SAMPLE_RATE),
                chunk_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            segments, info = model.transcribe(chunk_path)

            for seg in segments:
                f.write(f"{index}\n")
                f.write(
                    f"{format_time(seg.start + start)} --> "
                    f"{format_time(seg.end + start)}\n"
                )
                f.write(seg.text.strip() + "\n\n")
                index += 1

            # ---------------- PROGRESS UPDATE
            progress["current"] = i + 1
            progress["total"] = num_chunks
            progress["status"] = f"Chunk {i+1}/{num_chunks} - {filename}"

            if progress_callback:
                progress_callback(progress.copy())

            os.remove(chunk_path)

    os.remove(audio_file)

    progress["status"] = "Completed"
    if progress_callback:
        progress_callback(progress.copy())

    return output_srt


def process_srt_job_with_progress(selected_path, chunk_length, model_size, progress, progress_callback=None):

    if os.path.isdir(selected_path):

        files = [
            f for f in os.listdir(selected_path)
            if f.lower().endswith(tuple(ALLOWED_EXTENSIONS))
        ]

        progress["total_files"] = len(files)

        for i, file in enumerate(files):

            progress["current_file"] = i + 1
            progress["status"] = f"Processing {file}"

            if progress_callback:
                progress_callback(progress.copy())

            process_srt_job(
                os.path.join(selected_path, file),
                chunk_length,
                model_size,
                progress,
                progress_callback
            )

    else:
        progress["total_files"] = 1
        progress["current_file"] = 1

        process_srt_job(
            selected_path,
            chunk_length,
            model_size,
            progress,
            progress_callback
        )
    
    # reset
    progress.update({
        "current": 0,
        "total": 0,
        "status": "idle",
        "total_files": 0,
        "current_file": 0
    })

    if progress_callback:
        progress_callback(progress.copy())