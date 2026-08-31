"""Seed public sample media into Reflex ``uploaded_files`` (``/_upload``).

Downloaded once on backend startup via a lifespan task; the frontend uses
``rx.get_upload_url(...)``. See:
https://reflex.dev/docs/utility-methods/lifespan-tasks/
https://reflex.dev/docs/library/forms/upload/
"""

from __future__ import annotations

import asyncio
import http.client
import logging
import urllib.error
import urllib.request
from pathlib import Path

import reflex as rx

logger = logging.getLogger(__name__)

AUDIO_NAME = "sample.mp3"
VIDEO_NAME = "sample.mp4"

_AUDIO_URLS = (
    "https://interactive-examples.mdn.mozilla.net/media/cc0-audio/flower.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
    "https://samplelib.com/lib/preview/mp3/sample-9s.mp3",
)
_VIDEO_URLS = (
    "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
    "https://samplelib.com/lib/preview/mp4/sample-5s.mp4",
)


def upload_media_path(name: str) -> Path:
    return Path(rx.get_upload_dir()) / name


def demo_media_ready() -> bool:
    return all(
        upload_media_path(n).is_file() and upload_media_path(n).stat().st_size > 0
        for n in (AUDIO_NAME, VIDEO_NAME)
    )


def _download(url: str, dest: Path, *, timeout_s: float) -> int:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "reflex-capacitor-demo/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        data = resp.read()
    if not data:
        raise OSError("empty_download")
    dest.write_bytes(data)
    return len(data)


def ensure_demo_media(*, timeout_s: float = 90.0) -> dict[str, object]:
    """Download missing samples into ``rx.get_upload_dir()``. Idempotent (sync)."""
    dest_dir = Path(rx.get_upload_dir())
    dest_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, object] = {}

    audio = upload_media_path(AUDIO_NAME)
    a_entry: dict[str, object] = {
        "path": str(audio),
        "ok": False,
        "downloaded": False,
        "error": None,
        "bytes": audio.stat().st_size if audio.is_file() else 0,
    }
    if audio.is_file() and audio.stat().st_size > 0:
        a_entry["ok"] = True
    else:
        last_err: str | None = None
        for url in _AUDIO_URLS:
            try:
                a_entry["bytes"] = _download(url, audio, timeout_s=timeout_s)
                a_entry["downloaded"] = True
                a_entry["ok"] = True
                last_err = None
                break
            except (
                urllib.error.URLError,
                TimeoutError,
                OSError,
                http.client.HTTPException,
                http.client.IncompleteRead,
            ) as err:
                last_err = str(err)
                if audio.is_file():
                    audio.unlink(missing_ok=True)
        if last_err:
            a_entry["error"] = last_err
    files[AUDIO_NAME] = a_entry

    video = upload_media_path(VIDEO_NAME)
    v_entry: dict[str, object] = {
        "path": str(video),
        "ok": False,
        "downloaded": False,
        "error": None,
        "bytes": video.stat().st_size if video.is_file() else 0,
    }
    if video.is_file() and video.stat().st_size > 0:
        v_entry["ok"] = True
    else:
        last_err: str | None = None
        for url in _VIDEO_URLS:
            try:
                v_entry["bytes"] = _download(url, video, timeout_s=timeout_s)
                v_entry["downloaded"] = True
                v_entry["ok"] = True
                last_err = None
                break
            except (
                urllib.error.URLError,
                TimeoutError,
                OSError,
                http.client.HTTPException,
                http.client.IncompleteRead,
            ) as err:
                last_err = str(err)
                if video.is_file():
                    video.unlink(missing_ok=True)
        if last_err:
            v_entry["error"] = last_err
    files[VIDEO_NAME] = v_entry

    return {
        "dir": str(dest_dir),
        "files": files,
        "ok": all(bool(v.get("ok")) for v in files.values()),  # type: ignore[union-attr]
    }


async def seed_demo_media_lifespan() -> None:
    """Lifespan task: seed upload dir without blocking the event loop."""
    info = await asyncio.to_thread(ensure_demo_media)
    if info.get("ok"):
        logger.info("demo cloud media ready under %s", info.get("dir"))
    else:
        logger.warning("demo cloud media seed incomplete: %s", info)
