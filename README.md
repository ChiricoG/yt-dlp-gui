# yt-dlp GUI

A simple and lightweight graphical interface for [`yt-dlp`](https://github.com/yt-dlp/yt-dlp), powered by Python and PySide6.  
Supports downloading audio, video, or both from supported platforms with selectable quality and additional options.  
FFmpeg is resolved automatically so the app can run on Windows without a global install when a local or bundled copy is available.

---

## Features

- Download videos or extract audio only
- Quality presets (`best`, `worst`, `1080p`, `720p`, `480p`)
- Optional subtitles download
- Simulation mode (dry run, no files written)
- First-run FFmpeg setup dialog (download or manual install)
- Simple interface using PySide6

---

## Project structure

```
yt-dlp-gui/
├── main.py              # Entry point
├── ui_main.py           # Main GUI
├── downloader.py        # yt-dlp download handler
├── utils.py             # Paths and FFmpeg detection
├── ffmpeg_dialog.py     # FFmpeg missing / install dialog
├── requirements.txt
├── yt-dlp-gui.spec      # PyInstaller spec (recommended for builds)
└── ffmpeg/
    └── bin/
        ├── ffmpeg.exe   # Not in repo (.gitignore); dev / build / install target
        └── ffprobe.exe
```

---

## Requirements

- Python 3.8+
- Windows (current target platform)

```bash
pip install -r requirements.txt
```

If `requirements.txt` is missing:

```bash
pip install PySide6 yt-dlp
```

For building a standalone executable:

```bash
pip install pyinstaller
```

---

## Run (development)

```bash
python main.py
```

On first start, if FFmpeg is not found, a dialog offers to download it or open manual install instructions.

---

## FFmpeg: how it is found

At startup and before downloads, the app looks for FFmpeg in this order:

1. **System PATH** — globally installed `ffmpeg`
2. **Persistent local copy** — `ffmpeg/bin/` next to the project (dev) or next to the `.exe` (release)
3. **PyInstaller bundle** — `ffmpeg/bin/` included via `--add-data` (extracted under `sys._MEIPASS` at runtime)

| Mode | Persistent path (`ffmpeg/bin/`) | Bundled path (`_MEIPASS`) |
|------|----------------------------------|---------------------------|
| `python main.py` | Project folder | Same as project folder |
| Built `.exe` | Folder containing the executable | Inside the PyInstaller bundle |

- **Automatic install** (dialog) always writes to the **persistent** folder so it survives restarts.
- **Manual install**: place `ffmpeg.exe` and `ffprobe.exe` in the persistent `ffmpeg/bin/` folder shown by the dialog.
- FFmpeg binaries are **not** committed to this repository (see `.gitignore`).

---

## Build standalone executable (Windows)

Place `ffmpeg.exe` and `ffprobe.exe` in `ffmpeg/bin/` before building if you want them embedded in the release.

Recommended — use the spec file:

```bash
pyinstaller yt-dlp-gui.spec
```

Or manually:

```bash
pyinstaller main.py --name yt-dlp-gui --noconsole --onefile --add-data "ffmpeg\bin;ffmpeg/bin"
```

The executable is created under `dist/`.

**Distribution options**

- **With bundled FFmpeg** (`--add-data`): works out of the box; binaries live in the PyInstaller bundle (`_MEIPASS`).
- **Without bundled FFmpeg**: ship only the `.exe`; on first run the user can install FFmpeg via the dialog into `ffmpeg/bin/` next to the executable.

---

## Notes

- Merge, remux, and MP3 extraction require FFmpeg.
- Only Windows is supported in this setup (`ffmpeg.exe` paths); cross-platform support would need path and binary name adjustments in `utils.py`.
- The simulation checkbox runs yt-dlp in dry-run mode; destination folder is optional (defaults to the system temp directory).
- Multiple URLs: one per line, or separated by spaces.
- If the install folder next to the executable is not writable (e.g. `Program Files`), FFmpeg is installed under `%LOCALAPPDATA%\yt-dlp-gui\ffmpeg\bin`.

---

## License

MIT © 2025 ChiricoG
