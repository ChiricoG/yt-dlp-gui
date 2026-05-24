import os
import tempfile
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QRadioButton,
    QComboBox, QFileDialog, QCheckBox, QProgressBar, QButtonGroup,
)
from PySide6.QtCore import Qt, QThread
from downloader import YtDlpDownloader
from utils import get_ffmpeg_status, get_persistent_ffmpeg_dir, get_bundled_ffmpeg_dir, parse_urls


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("yt-dlp GUI - ChiricoG 2025")
        self.setMinimumSize(600, 500)
        self.is_downloading = False
        self.worker = None
        self.thread = None
        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        layout = QVBoxLayout()

        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText("Incolla uno o più URL (uno per riga, oppure separati da spazi)")
        self.url_input.setMaximumHeight(80)
        layout.addWidget(QLabel("URL Video:"))
        layout.addWidget(self.url_input)

        format_layout = QHBoxLayout()
        self.radio_audio = QRadioButton("Solo Audio")
        self.radio_video = QRadioButton("Solo Video")
        self.radio_both = QRadioButton("Audio + Video")
        self.radio_both.setChecked(True)
        self.format_group = QButtonGroup(self)
        self.format_group.addButton(self.radio_audio)
        self.format_group.addButton(self.radio_video)
        self.format_group.addButton(self.radio_both)
        format_layout.addWidget(self.radio_audio)
        format_layout.addWidget(self.radio_video)
        format_layout.addWidget(self.radio_both)
        layout.addLayout(format_layout)

        layout.addWidget(QLabel("Qualità desiderata:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["best", "worst", "1080p", "720p", "480p"])
        layout.addWidget(self.quality_combo)

        path_layout = QHBoxLayout()
        self.dest_path = QLineEdit()
        self.dest_path.setPlaceholderText("Cartella destinazione")
        self.browse_button = QPushButton("Sfoglia")
        self.browse_button.clicked.connect(self.choose_folder)
        path_layout.addWidget(self.dest_path)
        path_layout.addWidget(self.browse_button)
        layout.addLayout(path_layout)

        self.checkbox_subs = QCheckBox("Scarica sottotitoli")
        self.checkbox_simulate = QCheckBox("Simula (non scarica)")
        layout.addWidget(self.checkbox_subs)
        layout.addWidget(self.checkbox_simulate)

        self.progress_label = QLabel("Pronto per il download")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(QLabel("Log download:"))
        layout.addWidget(self.log_output)

        self.download_button = QPushButton("Avvia Download")
        self.download_button.clicked.connect(self.on_download_button_clicked)
        layout.addWidget(self.download_button)

        central.setLayout(layout)
        self.setCentralWidget(central)

        if not get_ffmpeg_status():
            self.log(
                f"⚠️ ffmpeg non trovato (né di sistema, né in {get_persistent_ffmpeg_dir()}, "
                f"né in {get_bundled_ffmpeg_dir()}). Alcune funzionalità potrebbero non funzionare."
            )

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Scegli cartella destinazione")
        if folder:
            self.dest_path.setText(folder)

    def log(self, msg):
        self.log_output.append(msg)

    def update_progress(self, current, total):
        if total > 0:
            progress_percent = int((current / total) * 100)
            self.progress_bar.setValue(progress_percent)
            self.progress_label.setText(
                f"Progresso: {current}/{total} completati ({progress_percent}%)"
            )
        else:
            self.progress_bar.setValue(0)
            self.progress_label.setText("Pronto per il download")

    def on_download_button_clicked(self):
        if self.is_downloading:
            if self.worker:
                self.worker.stop_requested = True
            self.download_button.setText("Annullamento...")
            self.download_button.setEnabled(False)
        else:
            self.start_download()

    def _validate_destination(self, simulate):
        if simulate:
            dest = self.dest_path.text().strip() or tempfile.gettempdir()
            return dest

        dest = self.dest_path.text().strip()
        if not dest:
            self.log("❌ Seleziona una cartella di destinazione!")
            return None
        if not os.path.isdir(dest):
            self.log("❌ La cartella di destinazione non esiste!")
            return None
        if not os.access(dest, os.W_OK):
            self.log("❌ La cartella di destinazione non è scrivibile!")
            return None
        return dest

    def start_download(self):
        urls = parse_urls(self.url_input.toPlainText())
        if not urls:
            self.log("❌ Inserisci almeno un URL valido!")
            return

        simulate = self.checkbox_simulate.isChecked()
        output_path = self._validate_destination(simulate)
        if output_path is None:
            return

        self.download_button.setText("Annulla download")
        self.download_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Inizializzazione...")

        if len(urls) > 1:
            self.log("\n🎬 === INIZIO SESSIONE DOWNLOAD ===")
            self.log(f"📋 URLs da scaricare: {len(urls)}")

        options = {
            "urls": urls,
            "audio_only": self.radio_audio.isChecked(),
            "video_only": self.radio_video.isChecked(),
            "quality": self.quality_combo.currentText(),
            "output_path": output_path,
            "subs": self.checkbox_subs.isChecked(),
            "simulate": simulate,
        }

        self.thread = QThread()
        self.worker = YtDlpDownloader(options)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished.connect(self.on_download_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.is_downloading = True
        self.thread.start()

    def on_download_finished(self):
        self.is_downloading = False
        self.worker = None
        self.thread = None
        self.download_button.setText("Avvia Download")
        self.download_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Pronto per il download")

    def closeEvent(self, event):
        if self.is_downloading and self.worker:
            self.worker.stop_requested = True
            if self.thread and self.thread.isRunning():
                self.thread.wait(10000)
        event.accept()
