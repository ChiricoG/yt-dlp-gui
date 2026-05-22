import os
import sys
import zipfile
import urllib.request
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QMessageBox
)
from PySide6.QtCore import QThread, Signal, Qt, QUrl
from PySide6.QtGui import QDesktopServices

class FFmpegDownloadWorker(QThread):
    progress_signal = Signal(int, str)  # (percentuale, messaggio_stato)
    finished_signal = Signal(bool, str)  # (successo, messaggio_errore)

    def __init__(self, target_dir):
        super().__init__()
        self.target_dir = target_dir
        self.zip_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

    def run(self):
        try:
            # Assicuriamoci che la cartella target esista
            os.makedirs(self.target_dir, exist_ok=True)
            zip_path = os.path.join(self.target_dir, "ffmpeg.zip")

            self.progress_signal.emit(0, "Connessione in corso per il download...")

            # Download con chunk per calcolare il progresso
            req = urllib.request.Request(
                self.zip_url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req) as response:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                block_size = 1024 * 64  # 64 KB

                with open(zip_path, 'wb') as f:
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
                                int(percent * 0.9),  # Riserva il 10% per l'estrazione
                                f"Scaricamento: {percent}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)"
                            )

            # Estrazione dei file
            self.progress_signal.emit(90, "Estrazione di ffmpeg.exe e ffprobe.exe...")
            
            extracted_count = 0
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    filename = os.path.basename(file_info.filename)
                    if filename in ["ffmpeg.exe", "ffprobe.exe"]:
                        source = zip_ref.open(file_info)
                        target_path = os.path.join(self.target_dir, filename)
                        with open(target_path, "wb") as target_file:
                            target_file.write(source.read())
                        source.close()
                        extracted_count += 1

            # Elimina il file zip temporaneo
            try:
                os.remove(zip_path)
            except Exception:
                pass

            if extracted_count >= 2:
                self.progress_signal.emit(100, "Installazione completata con successo!")
                self.finished_signal.emit(True, "")
            else:
                self.finished_signal.emit(False, "Impossibile trovare ffmpeg.exe o ffprobe.exe all'interno del pacchetto scaricato.")
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class FFmpegDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FFmpeg Mancante - yt-dlp GUI")
        self.setMinimumSize(480, 260)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(True)
        
        # Supporto path per PyInstaller
        if getattr(sys, 'frozen', False):
            self.base_dir = sys._MEIPASS
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.target_dir = os.path.join(self.base_dir, "ffmpeg", "bin")
        
        self.success = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Icona e Titolo
        title_label = QLabel("<h3>FFmpeg non trovato nel sistema</h3>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Descrizione
        desc_label = QLabel(
            "FFmpeg è un componente fondamentale per questa applicazione.<br/>"
            "È necessario per unire i flussi audio e video ad alta risoluzione (es. in formato MP4) "
            "o per convertire/estrarre file audio in MP3.<br/><br/>"
            "Scegli una delle opzioni per procedere:"
        )
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignJustify)
        layout.addWidget(desc_label)

        # Progress info (nascosta inizialmente)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        
        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)

        # Pulsanti
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
        # Disabilita i pulsanti e mostra la barra di progresso
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
                "FFmpeg è stato installato correttamente ed è pronto all'uso!"
            )
            self.success = True
            self.accept()
        else:
            QMessageBox.critical(
                self, 
                "Errore di Installazione", 
                f"Impossibile installare FFmpeg automaticamente:\n\n{error_msg}\n\n"
                "Riprova o seleziona l'installazione manuale."
            )
            # Ripristina i pulsanti
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
            "Dopo aver posizionato i file, riavvia l'applicazione."
        )
