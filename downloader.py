from PySide6.QtCore import QObject, Signal
from yt_dlp import YoutubeDL
import os
import time
from utils import (
    get_ffmpeg_location_for_ytdlp,
    get_ffmpeg_snapshot,
    get_local_ffmpeg_path,
)

class YtDlpDownloader(QObject):
    log_signal = Signal(str)
    progress_signal = Signal(int, int)  # (current, total)
    finished = Signal()

    def __init__(self, options):
        super().__init__()
        self.options = options
        self.current_url_index = 0
        self.total_urls = len(options["urls"])
        self.stop_requested = False
        self._last_progress_log = 0.0
        self._last_progress_pct = ""

    def run(self):
        snap = get_ffmpeg_snapshot()
        if snap["local_valid"]:
            self.log_signal.emit(
                f"[INFO] ✅ ffmpeg {snap['local_kind']}: {get_local_ffmpeg_path()}"
            )
        elif snap["system"]:
            self.log_signal.emit("[INFO] ✅ ffmpeg di sistema (PATH)")
        else:
            self.log_signal.emit(
                "[WARNING] ❌ ffmpeg non trovato — merge/conversione potrebbero fallire!"
            )

        ydl_opts = {
            "format": self._build_format(),
            "outtmpl": os.path.join(self.options["output_path"], "%(title)s.%(ext)s"),
            "quiet": True,
            "noprogress": True,
            "simulate": self.options["simulate"],
            "writesubtitles": self.options["subs"],
            "writeautomaticsub": self.options["subs"],
            "progress_hooks": [self._hook],
            "keepvideo": False,
            "logger": self,
        }

        ffmpeg_location = get_ffmpeg_location_for_ytdlp()
        if ffmpeg_location:
            ydl_opts["ffmpeg_location"] = ffmpeg_location

        if self.options["audio_only"]:
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
        elif self.options["video_only"]:
            ydl_opts["postprocessors"] = []
        else:
            ydl_opts["merge_output_format"] = "mp4"
            ydl_opts["postprocessors"] = [
                {"key": "FFmpegMerger"},
                {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"},
            ]

        errore_rilevato = False
        annullato = False
        success_count = 0

        if self.total_urls > 1:
            self.log_signal.emit(f"🚀 Inizio download di {self.total_urls} URL...")
        else:
            self.log_signal.emit("🚀 Inizio download...")

        self.progress_signal.emit(0, self.total_urls)

        with YoutubeDL(ydl_opts) as ydl:
            for i, url in enumerate(self.options["urls"]):
                if self.stop_requested:
                    annullato = True
                    break

                self.current_url_index = i + 1
                self._last_progress_pct = ""
                self._last_progress_log = 0.0

                if self.total_urls > 1:
                    self.log_signal.emit(
                        f"\n📺 [{self.current_url_index}/{self.total_urls}] "
                        f"Elaborazione: {url[:50]}{'...' if len(url) > 50 else ''}"
                    )
                else:
                    self.log_signal.emit(
                        f"📺 Elaborazione: {url[:50]}{'...' if len(url) > 50 else ''}"
                    )

                try:
                    ydl.download([url])
                    success_count += 1
                    if self.total_urls > 1:
                        self.log_signal.emit(
                            f"✅ [{self.current_url_index}/{self.total_urls}] Completato!"
                        )
                    else:
                        self.log_signal.emit("✅ Download completato!")

                except Exception as e:
                    msg = str(e)
                    if "Download annullato dall'utente" in msg:
                        annullato = True
                        break
                    errore_rilevato = True
                    if "[WinError 2]" in msg:
                        self.log_signal.emit(
                            f"❌ [{self.current_url_index}/{self.total_urls}] "
                            "Errore: FFmpeg non trovato o non configurato correttamente."
                        )
                    else:
                        self.log_signal.emit(
                            f"❌ [{self.current_url_index}/{self.total_urls}] Errore: {msg}"
                        )

                self.progress_signal.emit(self.current_url_index, self.total_urls)

        self.log_signal.emit("\n" + "=" * 50)
        if annullato:
            if self.total_urls > 1:
                self.log_signal.emit(
                    f"⚠️ Annullato. {success_count}/{self.total_urls} download completati prima "
                    "dell'interruzione."
                )
            else:
                self.log_signal.emit("⚠️ Download annullato dall'utente.")
        elif not errore_rilevato:
            if self.total_urls > 1:
                self.log_signal.emit(
                    f"🎉 COMPLETATO! Tutti i {self.total_urls} download eseguiti con successo!"
                )
            else:
                self.log_signal.emit("🎉 COMPLETATO! Download eseguito con successo!")
        else:
            if self.total_urls > 1:
                self.log_signal.emit(
                    f"⚠️ COMPLETATO CON ERRORI! {success_count}/{self.total_urls} download riusciti."
                )
            else:
                self.log_signal.emit("❌ ERRORE! Download fallito.")

        self.finished.emit()

    def _build_format(self):
        q = self.options["quality"].lower()

        if self.options["audio_only"]:
            return "bestaudio/best"

        if self.options["video_only"]:
            if q == "best":
                return "bestvideo[ext=mp4]/bestvideo"
            if q == "worst":
                return "worstvideo[ext=mp4]/worstvideo"
            if q.endswith("p") and q[:-1].isdigit():
                height = q[:-1]
                return (
                    f"bestvideo[height<={height}][ext=mp4]/"
                    f"bestvideo[height<={height}]"
                )
            return "bestvideo[ext=mp4]/bestvideo"

        if q == "best":
            return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        if q == "worst":
            return "worstvideo+worstaudio/worst"
        if q.endswith("p") and q[:-1].isdigit():
            height = q[:-1]
            return (
                f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
                f"best[height<={height}][ext=mp4]/best"
            )

        return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

    def _hook(self, d):
        if self.stop_requested:
            raise ValueError("Download annullato dall'utente")

        if d["status"] == "downloading":
            percent = d.get("_percent_str", "N/A").strip()
            now = time.time()
            if percent == self._last_progress_pct and now - self._last_progress_log < 1.0:
                return
            self._last_progress_pct = percent
            self._last_progress_log = now

            speed = d.get("_speed_str", "N/A").strip()
            eta = d.get("_eta_str", "N/A")
            if self.total_urls > 1:
                self.log_signal.emit(
                    f"⬇ [{self.current_url_index}/{self.total_urls}] "
                    f"{percent} @ {speed} ETA {eta}"
                )
            else:
                self.log_signal.emit(f"⬇ {percent} @ {speed} ETA {eta}")

        elif d["status"] == "finished":
            if self.total_urls > 1:
                self.log_signal.emit(
                    f"⏳ [{self.current_url_index}/{self.total_urls}] "
                    "Post-processing in corso..."
                )
            else:
                self.log_signal.emit("⏳ Post-processing in corso...")

    def debug(self, msg):
        if msg.startswith("[debug] "):
            return
        self.log_signal.emit(f"[DEBUG] {msg}")

    def warning(self, msg):
        self.log_signal.emit(f"[WARN] {msg}")

    def error(self, msg):
        msg_str = str(msg)
        if "WinError 2" in msg_str:
            return
        self.log_signal.emit(f"[ERROR] {msg}")
