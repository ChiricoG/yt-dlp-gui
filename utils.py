
import shutil
import importlib.util
import os
import sys

# Supporto path per PyInstaller
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FFMPEG_DIR = os.path.join(BASE_DIR, "ffmpeg", "bin")


def get_ffmpeg_status():
    import os
    import subprocess
    import sys
    import shutil

    # 1. Controlla se ffmpeg è presente nel PATH globale di sistema
    if shutil.which("ffmpeg"):
        return True

    # 2. Controlla se ffmpeg è presente localmente
    if getattr(sys, 'frozen', False):
        BASE_DIR = sys._MEIPASS
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    ffmpeg_path = os.path.join(BASE_DIR, "ffmpeg", "bin", "ffmpeg.exe")
    try:
        subprocess.run([ffmpeg_path, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False
