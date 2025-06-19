"""Audible audiobook conversion helpers."""

from __future__ import annotations

import json
import queue
import re
import shutil
import string
import subprocess
import tempfile
import threading
from pathlib import Path

from . import config

# Directory for completed conversions
DOWNLOADS_DIR = Path(config.SYNC_QUEUE_DIR) / "audiobook"

# Job tracking state
JOBS: dict[str, dict] = {}
JOB_QUEUE: queue.Queue[tuple[str, str]] = queue.Queue()

_worker_started = False

# Authentication state
IS_AUTHENTICATED = False


def check_authentication() -> bool:
    """Return True if audible-cli is authenticated."""
    global IS_AUTHENTICATED
    try:
        result = subprocess.run(
            ["audible", "profile", "list", "--json"],
            check=True,
            capture_output=True,
            text=True,
        )
        profiles = json.loads(result.stdout)
        IS_AUTHENTICATED = len(profiles) > 0
    except Exception:
        IS_AUTHENTICATED = False
    return IS_AUTHENTICATED


def check_dependencies() -> None:
    """Ensure ffmpeg and audible-cli are installed."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found")
    if not shutil.which("audible"):
        raise RuntimeError("audible-cli not found")


def sanitize_filename(name: str) -> str:
    valid = f"-_.() {string.ascii_letters}{string.digits}"
    return "".join(c for c in name if c in valid).replace(" ", "_")


def flatten_chapters(chapters: list[dict]) -> list[dict]:
    flat: list[dict] = []
    for ch in chapters:
        c = ch.copy()
        sub = c.pop("chapters", None)
        flat.append(c)
        if sub:
            flat.extend(flatten_chapters(sub))
    return flat


def get_audio_duration(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def start_worker() -> None:
    """Start the conversion worker thread if not already running."""
    global _worker_started
    if _worker_started:
        return
    check_dependencies()
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    t = threading.Thread(target=conversion_worker, daemon=True)
    t.start()
    _worker_started = True


def queue_conversion(asin: str, title: str) -> None:
    """Queue a new book for conversion."""
    start_worker()
    if asin in JOBS and JOBS[asin]["status"] in {"queued", "processing"}:
        return
    JOBS[asin] = {"status": "queued", "title": title}
    JOB_QUEUE.put((asin, title))


def fetch_library() -> list[dict]:
    """Return the user's Audible library using audible-cli."""
    result = subprocess.run(
        ["audible", "library", "list", "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def _download_book(asin: str, tmp: Path) -> tuple[Path, Path, Path]:
    subprocess.run(
        [
            "audible",
            "download",
            "-a",
            asin,
            "--aaxc",
            "--cover",
            "--cover-size",
            "1215",
            "--chapter",
            "-o",
            str(tmp),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    audio = next(tmp.glob("*.aax*"))
    cover = next(tmp.glob("*.jpg"))
    chapter_json = next(tmp.glob("*.json"))
    return audio, cover, chapter_json


def _fetch_metadata(asin: str) -> dict:
    result = subprocess.run(
        [
            "audible",
            "api",
            "-p",
            "response_groups=media,contributors,series,category_ladders",
            f"/1.0/library/{asin}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)["item"]


def _prepare_decrypt_options(tmp: Path) -> list[str]:
    voucher = next(tmp.glob("*.voucher"), None)
    if voucher:
        with open(voucher) as fh:
            data = json.load(fh)
        key = data["content_license"]["license_response"]["key"]
        iv = data["content_license"]["license_response"]["iv"]
        return ["-audible_key", key, "-audible_iv", iv]
    act = subprocess.run(
        ["audible", "activation-bytes"],
        check=True,
        capture_output=True,
        text=True,
    )
    return ["-activation_bytes", act.stdout.strip()]


def _build_metadata_file(
    info: dict,
    chapters_json: Path,
    asin: str,
    tmp: Path,
    decrypt_opts: list[str],
    audio_file: Path,
) -> Path:
    metadata = tmp / "chapters.txt"
    proc = subprocess.run(
        ["ffprobe", *decrypt_opts, str(audio_file)],
        capture_output=True,
        text=True,
    )
    copyright_text = "Unknown"
    for line in proc.stderr.splitlines():
        if "copyright" in line.lower():
            copyright_text = line.split(":", 1)[-1].strip()
            break
    with open(chapters_json) as f:
        chap_data = json.load(f)
    chapters = flatten_chapters(chap_data["content_metadata"]["chapter_info"]["chapters"])
    with open(metadata, "w", encoding="utf-8") as f:
        f.write(";FFMETADATA1\n")
        f.write(f"title={info.get('title', 'Unknown Title')}\n")
        f.write(f"artist={', '.join(a['name'] for a in info.get('authors', []))}\n")
        f.write(f"composer={', '.join(n['name'] for n in info.get('narrators', []))}\n")
        f.write(f"album_artist={', '.join(n['name'] for n in info.get('narrators', []))}\n")
        f.write(f"date={info.get('release_date', '').split('-')[0]}\n")
        f.write(f"copyright={copyright_text}\n")
        summary = info.get("merchandising_summary", "").replace("<br/>", "\n")
        f.write(f"comment={summary}\n")
        f.write(f"description={summary}\n")
        f.write(f"asin={asin}\n")
        f.write("genre=Audiobook\n")
        for ch in chapters:
            f.write("[CHAPTER]\n")
            f.write("TIMEBASE=1/1000\n")
            f.write(f"START={ch['start_offset_ms']}\n")
            f.write(f"END={ch['start_offset_ms'] + ch['length_ms']}\n")
            f.write(f"title={ch['title']}\n")
    return metadata


def _run_ffmpeg(
    audio: Path,
    cover: Path,
    metadata: Path,
    dest: Path,
    decrypt_opts: list[str],
    update_cb,
) -> None:
    total = get_audio_duration(audio)
    cmd = [
        "ffmpeg",
        *decrypt_opts,
        "-y",
        "-i",
        str(audio),
        "-i",
        str(cover),
        "-i",
        str(metadata),
        "-map",
        "0:a",
        "-map",
        "1:v",
        "-map_metadata",
        "2",
        "-map_chapters",
        "2",
        "-c:a",
        "aac",
        "-c:v",
        "copy",
        "-id3v2_version",
        "3",
        "-disposition:v",
        "attached_pic",
        "-movflags",
        "+faststart",
        "-metadata:s:v",
        'title="Album cover"',
        "-metadata:s:v",
        'comment="Cover (front)"',
        str(dest),
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )
    time_re = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.\d{2}")
    for line in iter(proc.stdout.readline, ""):
        m = time_re.search(line)
        if m:
            h, m_, s = map(int, m.groups())
            current = h * 3600 + m_ * 60 + s
            pct = int((current / total) * 100)
            update_cb(pct)
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg failed")


def conversion_worker() -> None:
    """Process jobs from ``JOB_QUEUE`` until the program exits."""
    while True:
        asin, title = JOB_QUEUE.get()
        try:
            JOBS[asin] = {"status": "processing", "progress": "Starting...", "title": title}
            with tempfile.TemporaryDirectory() as temp_dir:
                tmp = Path(temp_dir)
                audio, cover, chapters = _download_book(asin, tmp)
                info = _fetch_metadata(asin)
                decrypt_opts = _prepare_decrypt_options(tmp)
                metadata = _build_metadata_file(
                    info,
                    chapters,
                    asin,
                    tmp,
                    decrypt_opts,
                    audio,
                )
                output_name = sanitize_filename(title) + ".m4b"
                dest = DOWNLOADS_DIR / output_name

                def update(pct: int) -> None:
                    JOBS[asin]["progress"] = f"Converting ({pct}%)..."

                _run_ffmpeg(audio, cover, metadata, dest, decrypt_opts, update)
                JOBS[asin] = {"status": "complete", "title": title, "file": output_name}
        except Exception as exc:
            msg = f"An error occurred: {exc}"
            if hasattr(exc, "stderr"):
                msg += f" | Details: {exc.stderr}"
            JOBS[asin] = {"status": "error", "title": title, "message": msg}
        finally:
            JOB_QUEUE.task_done()


