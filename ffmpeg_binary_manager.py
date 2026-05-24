import platform
import sys
import os
import shutil

def get_ffmpeg_binary(name="ffmpeg"):
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))

    system_ffmpeg = shutil.which(name)
    if system_ffmpeg:
        return system_ffmpeg

    os_platform = platform.system()
    print(f"Detected OS {os_platform}")
    if os_platform.lower() == "windows":
        binary = f"{name}.exe"
    else:
        binary = name

    path = os.path.join(base_path, "bin", binary)

    if os.path.exists(path):
        print(f"FFmpeg found at {path}")
        return path

    raise RuntimeError("FFmpeg not found")