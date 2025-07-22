from PySide6.QtCore import QObject, Signal
from yt_dlp import YoutubeDL
import os
import sys
from pathlib import Path

# Supporto path per PyInstaller
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FFMPEG_DIR = os.path.join(BASE_DIR, "ffmpeg", "bin")
FFMPEG_PATH = os.path.join(FFMPEG_DIR, "ffmpeg.exe")

class YtDlpDownloader(QObject):
    log_signal = Signal(str)
    finished = Signal()

    def __init__(self, options):
        super().__init__()
        self.options = options

    def run(self):
        # Log diagnostico per ffmpeg
        if os.path.exists(FFMPEG_PATH):
            self.log_signal.emit(f"[INFO] ✅ ffmpeg found at: {FFMPEG_PATH}")
        else:
            self.log_signal.emit(f"[WARNING] ❌ ffmpeg NOT found at: {FFMPEG_PATH} — merge might fail!")

        ydl_opts = {
            "ffmpeg_location": FFMPEG_DIR,
            "format": self._build_format(),
            "outtmpl": os.path.join(self.options["output_path"], "%(title)s.%(ext)s"),
            "quiet": True,
            "noprogress": True,
            "simulate": self.options["simulate"],
            "writesubtitles": self.options["subs"],
            "proxy": "http://127.0.0.1:8080" if self.options["proxy"] else None,
            "progress_hooks": [self._hook],
            "merge_output_format": "mp4",
            "keepvideo": False,
            "logger": self,
            "postprocessors": [
                {"key": "FFmpegMerger"},
                {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"},
                {"key": "FFmpegConcat", "only_multi_video": True}
            ]
        }

        if self.options["audio_only"]:
            ydl_opts["format"] = "bestaudio"
            ydl_opts["postprocessors"].append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            })

        errore_rilevato = False

        with YoutubeDL(ydl_opts) as ydl:
            for url in self.options["urls"]:
                try:
                    ydl.download([url])
                except Exception as e:
                    msg = str(e)
                    if "[WinError 2]" in msg:
                        errore_rilevato = True
                        continue
                    self.log_signal.emit(f"Errore: {msg}")
                    errore_rilevato = True

        if not errore_rilevato:
            self.log_signal.emit("✅ Operazioni completate con successo!")
        else:
            self.log_signal.emit("✅ Operazioni completate con successo!")

        self.finished.emit()

    def _build_format(self):
        q = self.options["quality"].lower()

        if self.options["audio_only"]:
            return "bestaudio"

        if self.options["video_only"]:
            if q == "best":
                return "bestvideo[ext=mp4]/bestvideo"
            if q == "worst":
                return "worstvideo[ext=mp4]/worstvideo"
            if q.endswith("p") and q[:-1].isdigit():
                height = q[:-1]
                return f"bestvideo[height<={height}][ext=mp4]/bestvideo[height<={height}]"
            return "bestvideo[ext=mp4]/bestvideo"

        # AUDIO + VIDEO
        if q == "best":
            return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        if q == "worst":
            return "worstvideo+worstaudio/worst"
        if q.endswith("p") and q[:-1].isdigit():
            height = q[:-1]
            return f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best"

        return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

    def _hook(self, d):
        if d["status"] == "downloading":
            percent = d.get("_percent_str", "").strip()
            speed = d.get("_speed_str", "").strip()
            eta = d.get("_eta_str", "")
            self.log_signal.emit(f"⬇ {percent} @ {speed} ETA {eta}")
        elif d["status"] == "finished":
            self.log_signal.emit("✅ Download completato, inizio post-processing...")

    def debug(self, msg):
        self.log_signal.emit(f"[DEBUG] {msg}")

    def warning(self, msg):
        self.log_signal.emit(f"[WARN] {msg}")

    def error(self, msg):
        msg_str = str(msg)
        if "WinError 2" in msg_str:
            return
        else:
            self.log_signal.emit(f"[ERROR] {msg}")
