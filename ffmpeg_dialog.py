import os
import zipfile
import urllib.request
from utils import get_persistent_ffmpeg_dir, get_ffmpeg_status, invalidate_ffmpeg_cache
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QMessageBox
)
from PySide6.QtCore import QThread, Signal, Qt, QUrl
from PySide6.QtGui import QDesktopServices

DOWNLOAD_TIMEOUT = 120


class FFmpegDownloadWorker(QThread):
    progress_signal = Signal(int, str)
    finished_signal = Signal(bool, str)

    def __init__(self, target_dir):
        super().__init__()
        self.target_dir = target_dir
        self.zip_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

    def run(self):
        try:
            os.makedirs(self.target_dir, exist_ok=True)
            zip_path = os.path.join(self.target_dir, "ffmpeg.zip")

            self.progress_signal.emit(0, "Connessione in corso per il download...")

            req = urllib.request.Request(
                self.zip_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as response:
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0
                block_size = 1024 * 64

                with open(zip_path, "wb") as f:
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        downloaded += len(buffer)
                        f.write(buffer)
                        if total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            mb_downloaded = downloaded / (1024 * 1024)
                            mb_total = total_size / (1024 * 1024)
                            self.progress_signal.emit(
                                int(percent * 0.9),
                                f"Scaricamento: {percent}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)",
                            )

            self.progress_signal.emit(90, "Estrazione di ffmpeg.exe e ffprobe.exe...")

            extracted_count = 0
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                for file_info in zip_ref.infolist():
                    filename = os.path.basename(file_info.filename)
                    if filename in ["ffmpeg.exe", "ffprobe.exe"]:
                        source = zip_ref.open(file_info)
                        target_path = os.path.join(self.target_dir, filename)
                        with open(target_path, "wb") as target_file:
                            target_file.write(source.read())
                        source.close()
                        extracted_count += 1

            try:
                os.remove(zip_path)
            except OSError:
                pass

            if extracted_count >= 2:
                invalidate_ffmpeg_cache()
                self.progress_signal.emit(100, "Installazione completata con successo!")
                self.finished_signal.emit(True, "")
            else:
                self.finished_signal.emit(
                    False,
                    "Impossibile trovare ffmpeg.exe o ffprobe.exe nel pacchetto scaricato.",
                )
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class FFmpegDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FFmpeg Mancante - yt-dlp GUI")
        self.setMinimumSize(480, 260)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(True)
        self.target_dir = get_persistent_ffmpeg_dir()
        self.success = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("<h3>FFmpeg non trovato nel sistema</h3>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        desc_label = QLabel(
            "FFmpeg è un componente fondamentale per questa applicazione.<br/>"
            "È necessario per unire i flussi audio e video ad alta risoluzione (es. in formato MP4) "
            "o per convertire/estrarre file audio in MP3.<br/><br/>"
            "Scegli una delle opzioni per procedere:"
        )
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignJustify)
        layout.addWidget(desc_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)

        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)

        self.btn_layout = QHBoxLayout()

        self.btn_download = QPushButton("Scarica ed Installa\n(Consigliato)")
        self.btn_download.setMinimumHeight(45)
        self.btn_download.clicked.connect(self.start_auto_download)

        self.btn_manual = QPushButton("Istruzioni\nManuali")
        self.btn_manual.setMinimumHeight(45)
        self.btn_manual.clicked.connect(self.show_manual_instructions)

        self.btn_exit = QPushButton("Esci")
        self.btn_exit.setMinimumHeight(45)
        self.btn_exit.clicked.connect(self.reject)

        self.btn_layout.addWidget(self.btn_download)
        self.btn_layout.addWidget(self.btn_manual)
        self.btn_layout.addWidget(self.btn_exit)

        layout.addLayout(self.btn_layout)
        self.setLayout(layout)

    def start_auto_download(self):
        self.btn_download.setEnabled(False)
        self.btn_manual.setEnabled(False)
        self.btn_exit.setEnabled(False)

        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Avvio download...")
        self.status_label.setVisible(True)

        self.worker = FFmpegDownloadWorker(self.target_dir)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_download_finished)
        self.worker.start()

    def update_progress(self, percent, message):
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)

    def on_download_finished(self, success, error_msg):
        if success:
            QMessageBox.information(
                self,
                "Installazione Completata",
                "FFmpeg è stato installato correttamente ed è pronto all'uso!",
            )
            self.success = True
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Errore di Installazione",
                f"Impossibile installare FFmpeg automaticamente:\n\n{error_msg}\n\n"
                "Riprova o seleziona l'installazione manuale.",
            )
            self.btn_download.setEnabled(True)
            self.btn_manual.setEnabled(True)
            self.btn_exit.setEnabled(True)
            self.progress_bar.setVisible(False)
            self.status_label.setVisible(False)

    def show_manual_instructions(self):
        QDesktopServices.openUrl(QUrl("https://www.gyan.dev/ffmpeg/builds/"))

        cartella_dest = os.path.abspath(self.target_dir)

        QMessageBox.information(
            self,
            "Installazione Manuale",
            "È stato aperto il sito ufficiale di FFmpeg.\n\n"
            "Istruzioni:\n"
            "1. Scarica il file zip chiamato 'ffmpeg-release-essentials.zip'\n"
            "2. Estrai 'ffmpeg.exe' e 'ffprobe.exe' dalla cartella 'bin' dentro lo zip.\n"
            f"3. Copia ed incolla entrambi i file in questa cartella:\n\n{cartella_dest}\n\n"
            "Dopo aver posizionato i file, premi di nuovo «Istruzioni manuali» per verificare "
            "oppure riavvia l'applicazione.",
        )

        invalidate_ffmpeg_cache()
        if get_ffmpeg_status():
            QMessageBox.information(
                self,
                "FFmpeg rilevato",
                "FFmpeg è stato trovato nella cartella di installazione.",
            )
            self.success = True
            self.accept()
