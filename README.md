# yt-dlp GUI

A simple and lightweight graphical interface for [`yt-dlp`](https://github.com/yt-dlp/yt-dlp), powered by Python and PySide6.  
Supports downloading audio, video, or both from supported platforms with selectable quality and additional options.  
Built-in `ffmpeg` support allows this tool to run on Windows machines without requiring any external installation.

---

## 🚀 Features

- Download videos or extract audio only
- Choose between quality presets
- Optional subtitles download
- Proxy and simulation options
- Includes `ffmpeg` bundled for standalone use (release only, can't upload ffmpeg in the repo)
- Simple and clean interface using PySide6

---

## 📁 Project Structure

```
yt-dlp-gui/
├── main.py              # Entry point
├── ui_main.py           # Main GUI logic
├── downloader.py        # yt-dlp download handler
├── utils.py             # Helper functions (e.g., ffmpeg detection)
├── ffmpeg/
│   └── bin/
│       └── ffmpeg.exe   # Bundled static ffmpeg binary (Windows)
```

---

## 🔧 Requirements

- Python 3.8+
- Install dependencies:

```bash
pip install -r requirements.txt
```

If `requirements.txt` is missing, install manually:

```bash
pip install PySide6 yt-dlp
```

---

## 🧪 Run the App (Development Mode)

```bash
python main.py
```

---

## 📦 Build Standalone Executable (Windows)

Make sure `ffmpeg.exe` is in the `ffmpeg/bin/` folder, as included.

Use [PyInstaller](https://pyinstaller.org/) to generate a `.exe`:

```bash
pyinstaller main.py --name yt-dlp-gui --noconsole --onefile --add-data "ffmpeg\bin;ffmpeg/bin"
```

📦 The resulting executable will be located in the `dist/` folder.

---

## ✅ Notes

- `ffmpeg` is **not required to be installed globally**, as the app uses the bundled version.
- Only Windows is supported in this setup, but cross-platform support can be added.

---

## 📄 License

MIT © 2025 ChiricoG
