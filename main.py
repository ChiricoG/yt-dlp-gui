
from PySide6.QtWidgets import QApplication
from ui_main import MainWindow
from utils import get_ffmpeg_status, invalidate_ffmpeg_cache
from ffmpeg_dialog import FFmpegDialog
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)

    if not get_ffmpeg_status():
        dialog = FFmpegDialog()
        dialog.exec()
        if not dialog.success:
            sys.exit(0)

    invalidate_ffmpeg_cache()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
