from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


DEFAULT_CONCURRENT_FRAGMENTS = 1
DEFAULT_FRAGMENT_RETRIES = 10


@dataclass(frozen=True)
class DownloadOptions:
    concurrent_fragments: int = DEFAULT_CONCURRENT_FRAGMENTS
    fragment_retries: int = DEFAULT_FRAGMENT_RETRIES
    strict_fragments: bool = False


def validate_url(value: str) -> str:
    """Accept any HTTPS URL."""
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise argparse.ArgumentTypeError("provide a valid HTTPS URL")
    return value


def positive_int(value: str) -> int:
    """Parse a strictly positive integer for argparse."""
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if number < 1:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def build_command(
    url: str,
    temporary_dir: Path,
    filepath_marker: Path,
    options: DownloadOptions = DownloadOptions(),
    yt_dlp: str = "yt-dlp",
) -> list[str]:
    """Build an isolated yt-dlp invocation for one title."""
    command = [
        yt_dlp,
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

    command.extend(
        [
            "--format",
            (
                # Preserve every audio stream exposed by the manifest instead
                # of guessing a preferred language from unreliable metadata.
                "bestvideo*+mergeall[vcodec=none]/best"
            ),
            "--audio-multistreams",
            "--merge-output-format",
            "mkv",
            "--sub-langs",
            "all,-live_chat",
            "--write-subs",
            "--convert-subs",
            "vtt",
            "--embed-subs",
            "--output",
            str(temporary_dir / "%(title)s.%(ext)s"),
            "--print-to-file",
            "after_dl:%(filepath)s",
            str(filepath_marker),
            url,
        ]
    )
    return command


def resolve_yt_dlp() -> str | None:
    """Find either a globally installed or virtualenv-local yt-dlp binary."""
    yt_dlp = shutil.which("yt-dlp")
    local_yt_dlp = Path(sys.executable).with_name("yt-dlp")
    if yt_dlp is None and local_yt_dlp.is_file():
        yt_dlp = str(local_yt_dlp)
    return yt_dlp


def read_downloaded_video(filepath_marker: Path) -> Path | None:
    """Read the final media path emitted by yt-dlp after post-processing."""
    if not filepath_marker.is_file():
        return None
    marker_lines = filepath_marker.read_text(encoding="utf-8").splitlines()
    if not marker_lines:
        return None
    downloaded_video = Path(marker_lines[-1].strip())
    return downloaded_video if downloaded_video.is_file() else None


def default_destination(downloaded_video: Path) -> Path:
    return Path.home() / "Downloads" / downloaded_video.name


def run_download(
    url: str,
    *,
    options: DownloadOptions,
    yt_dlp: str,
    output_path: Path | None = None,
    keep_temp_on_error: bool = False,
) -> int:
    """Download one title and move the completed media file to its destination."""
    temporary_dir = Path(tempfile.mkdtemp(prefix="streaming-downloader-"))
    failed = True

    try:
        filepath_marker = temporary_dir / ".last-download-path"
        command = build_command(url, temporary_dir, filepath_marker, options, yt_dlp)
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as error:
            print(f"yt-dlp exited with code {error.returncode}", file=sys.stderr)
            return error.returncode or 1

        downloaded_video = read_downloaded_video(filepath_marker)
        if downloaded_video is None:
            print("Error: unable to determine the downloaded file.", file=sys.stderr)
            return 1

        destination = (output_path or default_destination(downloaded_video)).expanduser()
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(downloaded_video), destination)
        except OSError as error:
            print(f"Error: unable to move the downloaded file: {error}", file=sys.stderr)
            return 1

        failed = False
        print(destination)
        return 0
    finally:
        if failed and keep_temp_on_error:
            print(f"Temporary files kept at: {temporary_dir}", file=sys.stderr)
        else:
            shutil.rmtree(temporary_dir, ignore_errors=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Download a title with yt-dlp.")
    result.add_argument("url", type=validate_url)
    result.add_argument(
        "--output-path",
        type=Path,
        metavar="FILE",
        help="final MKV file path (default: ~/Downloads/<title>.mkv)",
    )
    result.add_argument(
        "--concurrent-fragments",
        type=positive_int,
        default=DEFAULT_CONCURRENT_FRAGMENTS,
        metavar="N",
        help=f"number of fragments downloaded in parallel (default: {DEFAULT_CONCURRENT_FRAGMENTS})",
    )
    result.add_argument(
        "--fragment-retries",
        type=positive_int,
        default=DEFAULT_FRAGMENT_RETRIES,
        metavar="N",
        help=f"retries for each unavailable fragment (default: {DEFAULT_FRAGMENT_RETRIES})",
    )
    result.add_argument(
        "--strict-fragments",
        action="store_true",
        help="fail instead of creating an output with missing fragments",
    )
    result.add_argument(
        "--keep-temp-on-error",
        action="store_true",
        help="keep temporary files and print their path when the download fails",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    yt_dlp = resolve_yt_dlp()
    if yt_dlp is None:
        print("Error: yt-dlp was not found. Follow the README instructions.", file=sys.stderr)
        return 2
    if shutil.which("ffmpeg") is None:
        print("Error: ffmpeg was not found. Follow the README instructions.", file=sys.stderr)
        return 2

    options = DownloadOptions(
        concurrent_fragments=args.concurrent_fragments,
        fragment_retries=args.fragment_retries,
        strict_fragments=args.strict_fragments,
    )
    return run_download(
        args.url,
        options=options,
        yt_dlp=yt_dlp,
        output_path=args.output_path,
        keep_temp_on_error=args.keep_temp_on_error,
    )


if __name__ == "__main__":
    raise SystemExit(main())
