import subprocess
from faster_whisper import WhisperModel
import math
import os
import tempfile
import shutil
from ffmpeg_binary_manager import get_ffmpeg_binary
import pprint

## LocalSRT v3: folder or file with chunking support


INPUT_VIDEO = ""

AUDIO_FILE = os.path.join(tempfile.gettempdir(), "localsrt_audio.wav")
CHUNKS_DIR = os.path.join(tempfile.gettempdir(), "localsrt_chunks/")

CHUNK_LENGTH = 30  # seconds
SAMPLE_RATE = 16000
OVERLAP = 5
WHISPER_MODEL = False
ALLOWED_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov']
MODEL_SIZE = "base"  # or "tiny", "base", "medium", "large"
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
    print(f"Extracting from {input_video} to {output_audio}")
    cmd = [
        FFMPEG,
        "-y",
        "-i", input_video,
        "-ac", "1",
        "-ar", str(SAMPLE_RATE),
        output_audio
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---------------------------
# Step 2: Get audio duration
# ---------------------------
def get_audio_duration(audio_file):
    print(f"Fetching audio duration from {audio_file}")
    cmd = [
        FFPROBE,
        "-i", audio_file,
        "-show_entries", "format=duration",
        "-v", "quiet",
        "-of", "csv=p=0"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
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
    return f"{hrs:02}:{mins:02}:{secs:02},{ms:03}"


# ---------------------------
# Step 4: Transcribe in chunks
# ---------------------------
def transcribe_chunks(audio_file, whisper_model, chunk_length):
    print(f"Transcribing {audio_file} in chunks of {chunk_length} seconds")
    # get audio duration to use for total number of chunks
    duration = get_audio_duration(audio_file)
    # get total number of chunks by dividing audio duration by chunk length e.g 1m total audio/30s chunk = 2 chunks
    step = chunk_length - OVERLAP
    num_chunks = math.ceil(duration / step)

    detected_language = ""

    # force recreation of chunks directory
    if os.path.exists(CHUNKS_DIR):
        shutil.rmtree(CHUNKS_DIR)
    os.makedirs(CHUNKS_DIR, exist_ok=True)
    
    all_segments = []

    for i in range(num_chunks):
        start_time = i * (chunk_length - OVERLAP)
        # chunk_file = CHUNKS_DIR + f"chunk_{i}.wav"
        chunk_file = os.path.join(
            CHUNKS_DIR,
            f"chunk_{i}.wav"
        )

        # Extract chunk
        cmd = [
            FFMPEG,
            "-y",
            "-i", audio_file,
            "-ss", str(start_time),
            "-t", str(chunk_length),
            "-ac", "1",
            "-ar", str(SAMPLE_RATE),
            chunk_file
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Transcribe chunk
        segments, info = whisper_model.transcribe(chunk_file)

        # print("Detected language:", info.language)
        # print("Probability:", info.language_probability)
        if info.language_probability > 0.8:
            detected_language = info.language

        # Adjust timestamps
        for seg in segments:
            # pprint.pprint(seg)
            all_segments.append({
                "start": seg.start + start_time,
                "end": seg.end + start_time,
                "text": seg.text.strip()
            })

        os.remove(chunk_file)  # cleanup

    return {'all_segments': all_segments, 'detected_language': detected_language}


# ---------------------------
# Step 5: Write SRT
# ---------------------------
def write_srt(segments, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n")
            f.write(f"{format_time(seg['start'])} --> {format_time(seg['end'])}\n")
            f.write(f"{seg['text']}\n\n")

# ---------------------------
# Process SRT
# ---------------------------
def process_srt(input_file_path):
        try:
            filename = os.path.splitext(os.path.basename(input_file_path))[0]
            input_directory = os.path.dirname(input_file_path)
            output_file_name = os.path.join(input_directory, filename + ".srt")
            
            print("Extracting audio...")
            extract_audio(input_file_path, AUDIO_FILE)

            global WHISPER_MODEL
            if not WHISPER_MODEL:
                print("Loading Whisper model...")
                WHISPER_MODEL = WhisperModel(
                    MODEL_SIZE,
                    device=DEVICE,
                    compute_type=COMPUTE_TYPE
                )
            whisper_model = WHISPER_MODEL

            print("Transcribing in chunks...")
            transcribe_result = transcribe_chunks(AUDIO_FILE, whisper_model, CHUNK_LENGTH)

            # translate if destination language is different from source language (video)

            print("Writing subtitles...")
            write_srt(transcribe_result["all_segments"], output_file_name)

            print("Done! Saved to", output_file_name)
        except Exception as e:
            print(f"Error on process srt:{ str(e)}")
        # remove generated audio file 
        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)
        # remove generated chunks directory
        if os.path.exists(CHUNKS_DIR):
            shutil.rmtree(CHUNKS_DIR, ignore_errors=True)
        

# ---------------------------
# MAIN
# ---------------------------
def main():
    check_ffmpeg() 
    while True:
        prompt = ""
        if prompt == "" or prompt == None:
            prompt = input("Enter a video or directory path to import or /bye to exit: \n")
        if prompt == "/bye":
            break
        if prompt == "":
            continue
        INPUT_VIDEO = prompt
        
        is_folder = False

        if os.path.isfile(INPUT_VIDEO):
            print("File detected")
        elif os.path.isdir(INPUT_VIDEO):
            print("Directory detected")
            is_folder = True
        else:
            print("[Error]: File not found in path supplied. FILE does not exist.")
            continue

        # Crete audio_file folder if it doesn't exist
        audio_file_parent_directory = os.path.dirname(AUDIO_FILE)
        if not os.path.exists(audio_file_parent_directory):
            os.makedirs(audio_file_parent_directory)
        chunks_parent_directory = os.path.dirname(CHUNKS_DIR)
        # Crete chunks_dir folder if it doesn't exist
        if not os.path.exists(chunks_parent_directory):
            os.makedirs(chunks_parent_directory)

        if is_folder:
            folder_items = os.listdir(INPUT_VIDEO)
            for i, file in enumerate(folder_items):
                if not file.endswith(tuple(ALLOWED_EXTENSIONS)):
                    print(f"Skipping {file}")
                    continue
                print(f"Processing {file}. No {i+1} out of {len(folder_items)}")
                process_srt(os.path.join(INPUT_VIDEO, file))
        else:
            process_srt(INPUT_VIDEO)

        


if __name__ == "__main__":
    main()