import subprocess
from faster_whisper import WhisperModel
import math
import os
import tempfile
import shutil
from ffmpeg_binary_manager import get_ffmpeg_binary
import tkinter as tk
from tkinter import filedialog

## LocalSRT v3: folder or file with chunking support

INPUT_VIDEO = ""

AUDIO_FILE = os.path.join(
    tempfile.gettempdir(),
    "localsrt_audio.wav"
)

CHUNKS_DIR = os.path.join(
    tempfile.gettempdir(),
    "localsrt_chunks"
)

CHUNK_LENGTH = 30  # seconds
SAMPLE_RATE = 16000
OVERLAP = 5

WHISPER_MODEL = False

ALLOWED_EXTENSIONS = [
    ".mp4",
    ".mkv",
    ".avi",
    ".mov"
]

MODEL_SIZE = "base"  # tiny, base, medium, large
DEVICE = "cpu"
COMPUTE_TYPE = "int8"


def check_ffmpeg():
    try:
        global FFMPEG
        global FFPROBE

        FFMPEG = get_ffmpeg_binary("ffmpeg")
        FFPROBE = get_ffmpeg_binary("ffprobe")

        print(f"Using FFmpeg: {FFMPEG}")

    except Exception as e:
        print("Error:", str(e))
        exit(1)


# ---------------------------
# Step 1: Extract audio
# ---------------------------
def extract_audio(input_video, output_audio):
    print(
        f"Extracting from "
        f"{input_video} "
        f"to "
        f"{output_audio}"
    )

    cmd = [
        FFMPEG,
        "-y",
        "-i",
        input_video,
        "-ac",
        "1",
        "-ar",
        str(SAMPLE_RATE),
        output_audio
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)


# ---------------------------
# Step 2: Get audio duration
# ---------------------------
def get_audio_duration(audio_file):
    print(
        f"Fetching audio duration "
        f"from {audio_file}"
    )

    cmd = [
        FFPROBE,
        "-i",
        audio_file,
        "-show_entries",
        "format=duration",
        "-v",
        "quiet",
        "-of",
        "csv=p=0"
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return float(result.stdout.strip())


# ---------------------------
# Step 3: Format time (SRT)
# ---------------------------
def format_time(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)

    return (
        f"{hrs:02}:"
        f"{mins:02}:"
        f"{secs:02},"
        f"{ms:03}"
    )


# ---------------------------
# Step 4: Append SRT Entry
# ---------------------------
def append_srt_segment(
    file_handle,
    index,
    start,
    end,
    text
):
    file_handle.write(f"{index}\n")
    file_handle.write(
        f"{format_time(start)} "
        f"--> "
        f"{format_time(end)}\n"
    )
    file_handle.write(
        f"{text.strip()}\n\n"
    )


# ---------------------------
# Step 5: Transcribe Chunks
# ---------------------------
def transcribe_chunks(
    audio_file,
    whisper_model,
    chunk_length,
    output_srt_file
):
    print(
        f"Transcribing "
        f"{audio_file} "
        f"in chunks of "
        f"{chunk_length} seconds"
    )

    duration = get_audio_duration(audio_file)

    step = chunk_length - OVERLAP

    num_chunks = math.ceil(
        duration / step
    )

    detected_language = ""

    if os.path.exists(CHUNKS_DIR):
        shutil.rmtree(CHUNKS_DIR)

    os.makedirs(
        CHUNKS_DIR,
        exist_ok=True
    )

    subtitle_index = 1
    last_text = None

    with open(
        output_srt_file,
        "w",
        encoding="utf-8"
    ) as srt_file:

        for i in range(num_chunks):

            print(
                f"Chunk "
                f"{i + 1}"
                f"/"
                f"{num_chunks}"
            )

            start_time = i * step

            chunk_file = os.path.join(
                CHUNKS_DIR,
                f"chunk_{i}.wav"
            )

            cmd = [
                FFMPEG,
                "-y",
                "-i",
                audio_file,
                "-ss",
                str(start_time),
                "-t",
                str(chunk_length),
                "-ac",
                "1",
                "-ar",
                str(SAMPLE_RATE),
                chunk_file
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise RuntimeError(
                    result.stderr
                )

            segments, info = (
                whisper_model.transcribe(
                    chunk_file
                )
            )

            if (
                info.language_probability
                > 0.8
            ):
                detected_language = (
                    info.language
                )

            for seg in segments:

                text = seg.text.strip()

                # basic overlap duplicate filter
                if text == last_text:
                    continue

                last_text = text

                adjusted_start = (
                    seg.start
                    + start_time
                )

                adjusted_end = (
                    seg.end
                    + start_time
                )

                append_srt_segment(
                    srt_file,
                    subtitle_index,
                    adjusted_start,
                    adjusted_end,
                    text
                )

                subtitle_index += 1

            if os.path.exists(chunk_file):
                os.remove(chunk_file)

    return detected_language


# ---------------------------
# Process SRT
# ---------------------------
def process_srt(input_file_path):

    try:

        filename = os.path.splitext(os.path.basename(input_file_path))[0]

        input_directory = (os.path.dirname(input_file_path))

        output_file_name = (
            os.path.join(
                input_directory,
                filename + ".srt"
            )
        )

        print("Extracting audio...")

        extract_audio(input_file_path,AUDIO_FILE)

        global WHISPER_MODEL

        if not WHISPER_MODEL:

            print("Loading Whisper model...")

            WHISPER_MODEL = (
                WhisperModel(
                    MODEL_SIZE,
                    device=DEVICE,
                    compute_type=COMPUTE_TYPE)
            )

        whisper_model = (WHISPER_MODEL)

        print("Transcribing in chunks...")

        detected_language = (
            transcribe_chunks(
                AUDIO_FILE,
                whisper_model,
                CHUNK_LENGTH,
                output_file_name
            )
        )

        if detected_language:
            print(
                f"Detected language: {detected_language}"
            )

        print(
            f"Done! Saved to {output_file_name}"
        )

    except Exception as e:

        print(
            f"Error processing "
            f"{input_file_path}: "
            f"{str(e)}"
        )

    finally:

        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)

        if os.path.exists(CHUNKS_DIR):
            shutil.rmtree(
                CHUNKS_DIR,
                ignore_errors=True
            )


# ---------------------------
# MAIN
# ---------------------------

def select_path():
    root = tk.Tk()
    root.withdraw()  # hide main window
    root.attributes("-topmost", True)

    while True:
        choice = input(
            "\nSelect:\n"
            "1 - File\n"
            "2 - Folder\n"
            "3 - Cancel\n"
            "Choice: "
        ).strip()

        if choice == "1":
            path = filedialog.askopenfilename(
                title="Select Video File",
                filetypes=[
                    (
                        "Video Files",
                        "*.mp4 *.mkv *.avi *.mov"
                    ),
                ]
            )
            root.destroy()
            return path

        elif choice == "2":
            path = filedialog.askdirectory(
                title="Select Folder"
            )
            root.destroy()
            return path

        elif choice == "3":
            root.destroy()
            return None

        print("Invalid choice")

def main():

    check_ffmpeg()

    while True:
        prompt = ""
        if (prompt == "" or prompt is None):
            prompt = input(
                "Enter a video or directory path to import or "
                "/select to browse files, or /bye to exit:\n"
            ).strip()

        if prompt.lower() == "/bye":
            break

        if prompt == "":
            continue

        if prompt.lower() == "/select":
            selected_path = select_path()

            if not selected_path:
                continue

            prompt = selected_path

            print(
                f"Selected: {prompt}"
            )

        INPUT_VIDEO = prompt

        is_folder = False

        if os.path.isfile(
            INPUT_VIDEO
        ):
            print("File detected")

        elif os.path.isdir(INPUT_VIDEO):
            print("Directory detected")
            is_folder = True

        else:
            print("[Error]: File not found in path supplied.")
            continue

        audio_parent = (
            os.path.dirname(AUDIO_FILE)
        )

        if not os.path.exists(audio_parent):
            os.makedirs(audio_parent)

        chunks_parent = (os.path.dirname(CHUNKS_DIR))

        if not os.path.exists(chunks_parent):
            os.makedirs(chunks_parent)

        if is_folder:
            folder_items = os.listdir(INPUT_VIDEO)
            for i, file in enumerate(folder_items):
                if not file.lower().endswith(tuple(ALLOWED_EXTENSIONS)):
                    print(f"Skipping {file}")
                    continue

                print(
                    f"Processing {file}. No {i+1} out of {len(folder_items)}"
                )

                process_srt(os.path.join(INPUT_VIDEO,file))

        else:
            process_srt(INPUT_VIDEO)


if __name__ == "__main__":
    main()