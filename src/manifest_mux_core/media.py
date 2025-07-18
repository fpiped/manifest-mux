from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .models import MediaProbe, MediaStream


class MediaValidationError(RuntimeError):
    """Raised when a completed media file is missing required streams."""


def probe_media(path: Path, ffprobe: str) -> MediaProbe:
    """Inspect a local container without decoding it."""
    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        (
            "format=duration:"
            "stream=index,codec_type,codec_name,width,height,channels,channel_layout:"
            "stream_tags=title,language:stream_disposition=forced"
        ),
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
    streams = tuple(
        _parse_stream(stream)
        for stream in payload.get("streams", [])
        if isinstance(stream, dict) and isinstance(stream.get("codec_type"), str)
    )
    return MediaProbe(
        duration_seconds=duration_seconds,
        stream_types=frozenset(stream.codec_type for stream in streams),
        streams=streams,
    )


def _parse_stream(stream: dict[str, object]) -> MediaStream:
    tags = stream.get("tags") if isinstance(stream.get("tags"), dict) else {}
    disposition = stream.get("disposition") if isinstance(stream.get("disposition"), dict) else {}
    return MediaStream(
        index=int(stream.get("index", 0)),
        codec_type=str(stream["codec_type"]),
        codec_name=_optional_str(stream.get("codec_name")),
        width=_optional_int(stream.get("width")),
        height=_optional_int(stream.get("height")),
        channels=_optional_int(stream.get("channels")),
        channel_layout=_optional_str(stream.get("channel_layout")),
        title=_optional_str(tags.get("title")),
        language=_optional_str(tags.get("language")),
        forced=bool(disposition.get("forced", 0)),
    )


def _optional_str(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _optional_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def validate_media(path: Path, ffprobe: str) -> MediaProbe:
    """Require a playable audiovisual container before it is delivered."""
    probe = probe_media(path, ffprobe)
    missing = [kind for kind in ("video", "audio") if kind not in probe.stream_types]
    if missing:
        raise MediaValidationError(f"missing required stream(s): {', '.join(missing)}")
    return probe
