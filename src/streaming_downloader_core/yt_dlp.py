from __future__ import annotations

import subprocess
from pathlib import Path

from .models import DownloadOptions


class YtDlpClient:
    """Command builder for yt-dlp operations on provider pages and manifests."""

    def __init__(self, executable: str) -> None:
        self.executable = executable

    def download_command(
        self,
        url: str,
        temporary_dir: Path,
        filepath_marker: Path,
        options: DownloadOptions,
    ) -> list[str]:
        command = [
            self.executable,
            "--no-playlist",
            "--restrict-filenames",
            "--no-write-comments",
            "--concurrent-fragments",
            str(options.concurrent_fragments),
            "--fragment-retries",
            str(options.fragment_retries),
        ]
        if options.strict_fragments:
            command.append("--abort-on-unavailable-fragments")

        tracks = options.tracks
        command.extend(["--format", tracks.audio_format, "--audio-multistreams", "--merge-output-format", "mkv"])
        command.extend(["--sub-langs", tracks.subtitle_languages, "--write-subs", "--convert-subs", "vtt"])
        if tracks.embed_subtitles:
            command.append("--embed-subs")
        command.extend(
            [
                "--output",
                str(temporary_dir / "%(title)s.%(ext)s"),
                "--print-to-file",
                "after_dl:%(filepath)s",
                str(filepath_marker),
                url,
            ]
        )
        return command

    def inspect_command(self, url: str) -> list[str]:
        return [self.executable, "--no-playlist", "--skip-download", "--dump-single-json", url]

    def formats_command(self, url: str) -> list[str]:
        return [self.executable, "--no-playlist", "--list-formats", url]

    def run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, check=True, text=True)
