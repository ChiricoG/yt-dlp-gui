
from PySide6.QtWidgets import QApplication
from ui_main import MainWindow
import sys
import os
import sys

# Supporto path per PyInstaller
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FFMPEG_DIR = os.path.join(BASE_DIR, "ffmpeg", "bin")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())