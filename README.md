# LocalSRT

LocalSRT is a lightweight, offline subtitle generator that uses **FFmpeg** and **Faster-Whisper** to automatically create `.srt` subtitle files from video files.

It supports:

* Single video transcription
* Batch processing of folders
* Multiple Whisper model sizes
* Configurable chunk length
* Modern web-based local UI
* Fully offline operation (after model download)

---

## Features

* Generate subtitles from video files
* Process an entire folder of videos
* Faster-Whisper powered transcription
* Adjustable chunk size
* Select Whisper model (Tiny, Base, Medium, Large)
* Skip videos that already have matching `.srt` files
* Windows, Linux, and macOS support
* Runs entirely on your machine

---

## Supported Video Formats

The following formats are currently supported:

* `.mp4`
* `.mkv`
* `.avi`
* `.mov`

Additional formats can be added by updating:

```python
ALLOWED_EXTENSIONS = [
    ".mp4",
    ".mkv",
    ".avi",
    ".mov"
]
```

---

## Requirements

### Python

* Python 3.12+
* FFmpeg (already packaged)
* FFprobe (already packaged)

---

## Installation

Clone the repository:

```bash
git clone https://github.com/yourusername/localsrt.git

cd localsrt
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Running Locally

Start the application:

```bash
python main.py
```

The application will automatically open a browser window:

```text
http://127.0.0.1:3555
```

---

## Using the Application

### Single Video

1. Open the UI
2. Click **Select File**
3. Choose a video
4. Select:

   * Chunk Length
   * Whisper Model
5. Click **Start**

Generated subtitles will be saved next to the source video:

```text
Movie.mp4
Movie.srt
```

---

### Folder Processing

1. Click **Select Folder**
2. Choose a directory
3. Click **Start**

All supported video files inside the folder will be processed.

Existing subtitle files are automatically skipped.

---

## Whisper Models

| Model  | Speed    | Accuracy | Recommended      |
| ------ | -------- | -------- | ---------------- |
| tiny   | Fastest  | Lowest   | Quick drafts     |
| base   | Fast     | Good     | Default          |
| medium | Moderate | Better   | General use      |
| large  | Slowest  | Best     | Highest accuracy |

Example configuration:

```python
MODEL_SIZE = "base"
```

---

## Chunk Processing

Videos are split into chunks before transcription.

Default:

```python
CHUNK_LENGTH = 30
OVERLAP = 5
```

Meaning:

* 30-second chunks
* 5-second overlap between chunks

This improves subtitle continuity while reducing memory usage.

---

## Output

Generated subtitle files use the SubRip (`.srt`) format:

```text
1
00:00:01,000 --> 00:00:04,000
Hello and welcome.

2
00:00:04,500 --> 00:00:08,000
Today we will discuss...
```

---

## Skip Existing Files

Before processing begins, LocalSRT checks whether a subtitle file already exists:

```text
Video.mp4
Video.srt
```

If found, processing is skipped automatically.

Example log:

```text
[SKIP] SRT already exists:
Video.srt
```

---

## Project Structure

```text
localsrt/
│
├── main.py
├── core.py
├── ffmpeg_binary_manager.py
│
├── ui/
│   └── index.html
│
├── bin/
│   ├── ffmpeg
│   ├── ffprobe
│   
│
│
└── requirements.txt
```

---

### FFmpeg not found

Verify:

```bash
ffmpeg -version
```

or ensure bundled binaries exist in:

```text
bin/
```

---

### WebSocket dependency warning

Install standard Uvicorn extras:

```bash
pip install "uvicorn[standard]"
```

---

## Acknowledgements

Built using:

* [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper)
* [FFmpeg](https://ffmpeg.org)
* [FastAPI](https://fastapi.tiangolo.com)
* [Uvicorn](https://www.uvicorn.org)
* [PyInstaller](https://pyinstaller.org)
