from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .media import MediaValidationError
from .models import MediaProbe, MediaStream


CODEC_LABELS = {
    "h264": "H.264",
    "hevc": "H.265/HEVC",
    "av1": "AV1",
    "vp9": "VP9",
    "aac": "AAC",
    "ac3": "AC-3",
    "eac3": "E-AC-3",
    "dts": "DTS",
    "flac": "FLAC",
    "mp3": "MP3",
    "opus": "Opus",
}


def generated_track_title(stream: MediaStream) -> str | None:
    """Generate a technical title only when the provider did not supply one."""
    if stream.title:
        return None
    if stream.codec_type == "video":
        return _video_title(stream)
    if stream.codec_type == "audio":
        return _audio_title(stream)
    if stream.codec_type == "subtitle":
        return _subtitle_title(stream)
    return None


def apply_track_titles(path: Path, ffmpeg: str, probe: MediaProbe) -> bool:
    """Write missing stream titles with a stream-copy remux."""
    titles = [
        (stream.index, title)
        for stream in probe.streams
        if (title := generated_track_title(stream)) is not None
    ]
    if not titles:
        return False

    temporary_path = path.with_name(f"{path.stem}.metadata{path.suffix}")
    command = [
        ffmpeg,
        "-y",
        "-v",
        "error",
        "-i",
        str(path),
        "-map",
        "0",
        "-map_metadata",
        "0",
        "-c",
        "copy",
    ]
    for index, title in titles:
        command.extend([f"-metadata:s:{index}", f"title={title}"])
    command.append(str(temporary_path))

    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        temporary_path.unlink(missing_ok=True)
        detail = result.stderr.strip() or "ffmpeg could not write track metadata"
        raise MediaValidationError(detail)
    os.replace(temporary_path, path)
    return True


def _video_title(stream: MediaStream) -> str:
    height = stream.height
    quality = {
        2160: "Ultra HD",
        1440: "QHD",
        1080: "Full HD",
        720: "HD",
        480: "SD",
    }.get(height, f"{height}p" if height else "Video")
    details = [f"{height}p" if height else None, _codec_label(stream.codec_name)]
    technical = ", ".join(detail for detail in details if detail)
    return f"{quality} ({technical})" if technical else quality


def _audio_title(stream: MediaStream) -> str:
    prefix = stream.language or "Audio"
    details = [_codec_label(stream.codec_name), _channel_label(stream)]
    technical = " ".join(detail for detail in details if detail)
    return f"{prefix} — {technical}" if technical else prefix


def _subtitle_title(stream: MediaStream) -> str:
    title = stream.language or "Subtitles"
    return f"{title} — Forced" if stream.forced else title


def _codec_label(codec_name: str | None) -> str | None:
    return CODEC_LABELS.get(codec_name, codec_name.upper() if codec_name else None)


def _channel_label(stream: MediaStream) -> str | None:
    return {
        1: "Mono",
        2: "Stereo",
        6: "5.1",
        8: "7.1",
    }.get(stream.channels, f"{stream.channels} channels" if stream.channels else None)
