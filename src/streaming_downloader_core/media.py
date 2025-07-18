from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .models import MediaProbe


class MediaValidationError(RuntimeError):
    """Raised when a completed media file is missing required streams."""


def probe_media(path: Path, ffprobe: str) -> MediaProbe:
    """Inspect a local container without decoding it."""
    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=codec_type",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or "ffprobe could not inspect the file"
        raise MediaValidationError(detail)

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise MediaValidationError("ffprobe returned invalid JSON") from error

    duration = payload.get("format", {}).get("duration")
    try:
        duration_seconds = float(duration) if duration is not None else None
    except (TypeError, ValueError):
        duration_seconds = None
    stream_types = frozenset(
        stream["codec_type"]
        for stream in payload.get("streams", [])
        if isinstance(stream, dict) and isinstance(stream.get("codec_type"), str)
    )
    return MediaProbe(duration_seconds=duration_seconds, stream_types=stream_types)


def validate_media(path: Path, ffprobe: str) -> MediaProbe:
    """Require a playable audiovisual container before it is delivered."""
    probe = probe_media(path, ffprobe)
    missing = [kind for kind in ("video", "audio") if kind not in probe.stream_types]
    if missing:
        raise MediaValidationError(f"missing required stream(s): {', '.join(missing)}")
    return probe
