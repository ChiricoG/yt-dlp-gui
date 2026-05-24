
import os
import re
import shutil
import subprocess
import sys
import tempfile

# Sequenze ANSI (es. colori nel progresso yt-dlp) e caratteri di controllo
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

FFMPEG_EXE = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
FFPROBE_EXE = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"

_dir_cache: dict[str, bool] = {}
_ffmpeg_snapshot: dict | None = None


def invalidate_ffmpeg_cache():
    global _ffmpeg_snapshot
    _dir_cache.clear()
    _ffmpeg_snapshot = None


def get_app_dir():
    """Directory persistente accanto a exe/script."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_bundle_dir():
    """Directory dati PyInstaller (--add-data) o progetto in dev."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", get_app_dir())
    return get_app_dir()


def _can_write_dir(directory):
    try:
        os.makedirs(directory, exist_ok=True)
        test_file = os.path.join(directory, ".write_test")
        with open(test_file, "w", encoding="utf-8") as handle:
            handle.write("ok")
        os.remove(test_file)
        return True
    except OSError:
        return False


def get_persistent_ffmpeg_dir():
    """Cartella ffmpeg/bin persistente; fallback in LOCALAPPDATA se non scrivibile."""
    primary = os.path.join(get_app_dir(), "ffmpeg", "bin")
    fallback = os.path.join(
        os.environ.get("LOCALAPPDATA", tempfile.gettempdir()),
        "yt-dlp-gui",
        "ffmpeg",
        "bin",
    )
    if os.path.normpath(primary) == os.path.normpath(fallback):
        return primary
    if _is_valid_ffmpeg_dir(primary, use_cache=True) or _can_write_dir(primary):
        return primary
    return fallback


def get_bundled_ffmpeg_dir():
    """Cartella ffmpeg/bin nel bundle PyInstaller."""
    return os.path.join(get_bundle_dir(), "ffmpeg", "bin")


def _is_valid_ffmpeg_dir(directory, use_cache=True):
    key = os.path.normcase(os.path.abspath(directory))
    if use_cache and key in _dir_cache:
        return _dir_cache[key]

    ffmpeg_path = os.path.join(directory, FFMPEG_EXE)
    ffprobe_path = os.path.join(directory, FFPROBE_EXE)
    if not os.path.isfile(ffmpeg_path) or not os.path.isfile(ffprobe_path):
        result = False
    else:
        try:
            subprocess.run(
                [ffmpeg_path, "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=10,
            )
            result = True
        except (OSError, subprocess.SubprocessError):
            result = False

    _dir_cache[key] = result
    return result


def _build_ffmpeg_snapshot():
    persistent_dir = get_persistent_ffmpeg_dir()
    bundled_dir = get_bundled_ffmpeg_dir()
    persistent_valid = _is_valid_ffmpeg_dir(persistent_dir)
    bundled_valid = (
        os.path.normpath(bundled_dir) != os.path.normpath(persistent_dir)
        and _is_valid_ffmpeg_dir(bundled_dir)
    )
    system = shutil.which("ffmpeg") is not None

    if persistent_valid:
        local_dir = persistent_dir
        local_kind = "persistente"
    elif bundled_valid:
        local_dir = bundled_dir
        local_kind = "bundled"
    else:
        local_dir = None
        local_kind = None

    ytdlp_location = persistent_dir if persistent_valid else (
        bundled_dir if bundled_valid else None
    )

    return {
        "system": system,
        "persistent_dir": persistent_dir,
        "bundled_dir": bundled_dir,
        "persistent_valid": persistent_valid,
        "bundled_valid": bundled_valid,
        "local_valid": persistent_valid or bundled_valid,
        "local_dir": local_dir,
        "local_kind": local_kind,
        "local_path": os.path.join(local_dir, FFMPEG_EXE) if local_dir else None,
        "ytdlp_location": ytdlp_location,
        "available": system or persistent_valid or bundled_valid,
    }


def get_ffmpeg_snapshot():
    global _ffmpeg_snapshot
    if _ffmpeg_snapshot is None:
        _ffmpeg_snapshot = _build_ffmpeg_snapshot()
    return _ffmpeg_snapshot


def has_system_ffmpeg():
    return get_ffmpeg_snapshot()["system"]


def has_persistent_ffmpeg():
    return get_ffmpeg_snapshot()["persistent_valid"]


def has_bundled_ffmpeg():
    return get_ffmpeg_snapshot()["bundled_valid"]


def has_local_ffmpeg():
    return get_ffmpeg_snapshot()["local_valid"]


def get_local_ffmpeg_path():
    snap = get_ffmpeg_snapshot()
    return snap["local_path"] or os.path.join(get_persistent_ffmpeg_dir(), FFMPEG_EXE)


def get_ffmpeg_status():
    return get_ffmpeg_snapshot()["available"]


def get_ffmpeg_location_for_ytdlp():
    return get_ffmpeg_snapshot()["ytdlp_location"]


def parse_urls(text):
    """Estrae URL da testo (una o più righe, spazi come separatore secondario)."""
    urls = []
    for line in text.replace("\r\n", "\n").split("\n"):
        for part in line.split():
            part = part.strip()
            if part:
                urls.append(part)
    return urls


def sanitize_log_text(text):
    """Rimuove codici ANSI e caratteri di controllo per log leggibili in QTextEdit."""
    if text is None:
        return ""
    cleaned = _ANSI_ESCAPE_RE.sub("", str(text))
    cleaned = cleaned.replace("\r", "")
    cleaned = _CONTROL_CHARS_RE.sub("", cleaned)
    return cleaned
