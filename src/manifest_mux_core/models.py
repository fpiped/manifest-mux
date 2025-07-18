from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet


DEFAULT_CONCURRENT_FRAGMENTS = 1
DEFAULT_FRAGMENT_RETRIES = 30


@dataclass(frozen=True)
class TrackSelection:
    """Language-agnostic media track policy passed to yt-dlp."""

    audio_format: str = "bestvideo*+mergeall[vcodec=none]/best"
    subtitle_languages: str = "all,-live_chat"
    embed_subtitles: bool = True


@dataclass(frozen=True)
class DownloadOptions:
    concurrent_fragments: int = DEFAULT_CONCURRENT_FRAGMENTS
    fragment_retries: int = DEFAULT_FRAGMENT_RETRIES
    strict_fragments: bool = True
    sample_seconds: float | None = None
    verbose: bool = False
    tracks: TrackSelection = TrackSelection()


@dataclass(frozen=True)
class MediaStream:
    """Technical metadata for one stream inside a media container."""

    index: int
    codec_type: str
    codec_name: str | None = None
    width: int | None = None
    height: int | None = None
    channels: int | None = None
    channel_layout: str | None = None
    title: str | None = None
    language: str | None = None
    forced: bool = False


@dataclass(frozen=True)
class MediaProbe:
    """Minimal, container-agnostic result returned by ffprobe."""

    duration_seconds: float | None
    stream_types: FrozenSet[str]
    streams: tuple[MediaStream, ...] = ()

    @property
    def has_video(self) -> bool:
        return "video" in self.stream_types

    @property
    def has_audio(self) -> bool:
        return "audio" in self.stream_types
