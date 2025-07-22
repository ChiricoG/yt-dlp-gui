from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QRadioButton,
    QComboBox, QFileDialog, QCheckBox
)
from PySide6.QtCore import Qt, QThread
from downloader import YtDlpDownloader
from utils import get_ffmpeg_status
import os
import sys

# Supporto path per PyInstaller
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FFMPEG_DIR = os.path.join(BASE_DIR, "ffmpeg", "bin")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("yt-dlp GUI - ChiricoG 2025")
        self.setMinimumSize(600, 500)
        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        layout = QVBoxLayout()

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Incolla uno o più URL separati da spazi")
        layout.addWidget(QLabel("URL Video:"))
        layout.addWidget(self.url_input)

        format_layout = QHBoxLayout()
        self.radio_audio = QRadioButton("Solo Audio")
        self.radio_video = QRadioButton("Solo Video")
        self.radio_both = QRadioButton("Audio + Video")
        self.radio_both.setChecked(True)
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
        self.checkbox_proxy = QCheckBox("Usa proxy")
        self.checkbox_simulate = QCheckBox("Simula (non scarica)")
        layout.addWidget(self.checkbox_subs)
        layout.addWidget(self.checkbox_proxy)
        layout.addWidget(self.checkbox_simulate)

        # Pulsante disabilitato permanentemente
        self.ffmpeg_button = QPushButton("Individua ffmpeg...")
        self.ffmpeg_button.setVisible(False)
        layout.addWidget(self.ffmpeg_button)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(QLabel("Log download:"))
        layout.addWidget(self.log_output)

        self.download_button = QPushButton("Avvia Download")
        self.download_button.clicked.connect(self.start_download)
        layout.addWidget(self.download_button)

        central.setLayout(layout)
        self.setCentralWidget(central)

        self.check_dependencies()

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Scegli cartella destinazione")
        if folder:
            self.dest_path.setText(folder)

    def log(self, msg):
        self.log_output.append(msg)

    def check_dependencies(self):
        # Verifica solo se ffmpeg è disponibile nella cartella locale
        if not get_ffmpeg_status():
            self.log("⚠️ ffmpeg non trovato nella cartella locale. Alcune funzionalità potrebbero non funzionare.")

        self.ffmpeg_button.setVisible(False)

    def start_download(self):
        options = {
            "urls": self.url_input.text().strip().split(),
            "audio_only": self.radio_audio.isChecked(),
            "video_only": self.radio_video.isChecked(),
            "both": self.radio_both.isChecked(),
            "quality": self.quality_combo.currentText(),
            "output_path": self.dest_path.text().strip(),
            "subs": self.checkbox_subs.isChecked(),
            "proxy": self.checkbox_proxy.isChecked(),
            "simulate": self.checkbox_simulate.isChecked(),
        }

        self.thread = QThread()
        self.worker = YtDlpDownloader(options)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.log_signal.connect(self.log)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()
