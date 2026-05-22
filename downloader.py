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
    progress_signal = Signal(int, int)  # (current, total)
    finished = Signal()

    def __init__(self, options):
        super().__init__()
        self.options = options
        self.current_url_index = 0
        self.total_urls = len(options["urls"])
        self.current_download_progress = 0
        self.stop_requested = False

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
            "progress_hooks": [self._hook],
            "keepvideo": False,
            "logger": self,
        }

        # Configurazione postprocessors diversa per audio e video
        if self.options["audio_only"]:
            ydl_opts["postprocessors"] = [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }
            ]
        else:
            # Per video o audio+video
            ydl_opts["merge_output_format"] = "mp4"
            ydl_opts["postprocessors"] = [
                {"key": "FFmpegMerger"},
                {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"},
                {"key": "FFmpegConcat", "only_multi_video": True}
            ]

        errore_rilevato = False
        success_count = 0
        
        # Log inizio operazione
        if self.total_urls > 1:
            self.log_signal.emit(f"🚀 Inizio download di {self.total_urls} URL...")
        else:
            self.log_signal.emit("🚀 Inizio download...")
        
        self.progress_signal.emit(0, self.total_urls)

        with YoutubeDL(ydl_opts) as ydl:
            for i, url in enumerate(self.options["urls"]):
                self.current_url_index = i + 1
                self.current_download_progress = 0
                
                # Log URL corrente
                if self.total_urls > 1:
                    self.log_signal.emit(f"\n📺 [{self.current_url_index}/{self.total_urls}] Elaborazione: {url[:50]}{'...' if len(url) > 50 else ''}")
                else:
                    self.log_signal.emit(f"📺 Elaborazione: {url[:50]}{'...' if len(url) > 50 else ''}")
                
                try:
                    ydl.download([url])
                    success_count += 1
                    if self.total_urls > 1:
                        self.log_signal.emit(f"✅ [{self.current_url_index}/{self.total_urls}] Completato!")
                    else:
                        self.log_signal.emit("✅ Download completato!")
                        
                except Exception as e:
                    msg = str(e)
                    if "Download annullato dall'utente" in msg:
                        self.log_signal.emit("⚠️ Download annullato dall'utente.")
                        errore_rilevato = True
                        break
                    elif "[WinError 2]" in msg:
                        self.log_signal.emit(f"❌ [{self.current_url_index}/{self.total_urls}] Errore: FFmpeg non trovato o non configurato correttamente.")
                        errore_rilevato = True
                    else:
                        self.log_signal.emit(f"❌ [{self.current_url_index}/{self.total_urls}] Errore: {msg}")
                        errore_rilevato = True
                
                # Aggiorna progresso globale
                self.progress_signal.emit(self.current_url_index, self.total_urls)

        # Messaggio finale più dettagliato
        self.log_signal.emit("\n" + "="*50)
        if not errore_rilevato:
            if self.total_urls > 1:
                self.log_signal.emit(f"🎉 COMPLETATO! Tutti i {self.total_urls} download eseguiti con successo!")
            else:
                self.log_signal.emit("🎉 COMPLETATO! Download eseguito con successo!")
        else:
            if self.total_urls > 1:
                self.log_signal.emit(f"⚠️ COMPLETATO CON ERRORI! {success_count}/{self.total_urls} download riusciti.")
            else:
                self.log_signal.emit("❌ ERRORE! Download fallito.")

        self.finished.emit()

    def _build_format(self):
        q = self.options["quality"].lower()

        if self.options["audio_only"]:
            # Per solo audio, usa il miglior formato audio disponibile
            return "bestaudio/best"

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
        if self.stop_requested:
            raise ValueError("Download annullato dall'utente")
        
        if d["status"] == "downloading":
            percent = d.get("_percent_str", "N/A").strip()
            speed = d.get("_speed_str", "N/A").strip()
            eta = d.get("_eta_str", "N/A")
            
            # Progresso dettagliato con info globale
            if self.total_urls > 1:
                self.log_signal.emit(f"⬇ [{self.current_url_index}/{self.total_urls}] {percent} @ {speed} ETA {eta}")
            else:
                self.log_signal.emit(f"⬇ {percent} @ {speed} ETA {eta}")
                
        elif d["status"] == "finished":
            if self.total_urls > 1:
                self.log_signal.emit(f"✅ [{self.current_url_index}/{self.total_urls}] Download completato, inizio post-processing...")
            else:
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