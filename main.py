
from PySide6.QtWidgets import QApplication
from ui_main import MainWindow
from utils import get_ffmpeg_status
from ffmpeg_dialog import FFmpegDialog
import sys
import os

# Supporto path per PyInstaller
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FFMPEG_DIR = os.path.join(BASE_DIR, "ffmpeg", "bin")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Controlla FFmpeg prima di avviare l'applicazione principale
    if not get_ffmpeg_status():
        dialog = FFmpegDialog()
        dialog.exec()
        if not dialog.success:
            sys.exit(0)
            
    window = MainWindow()
    window.show()
    sys.exit(app.exec())