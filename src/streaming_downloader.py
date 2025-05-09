from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit


DEFAULT_CONCURRENT_FRAGMENTS = "1"
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def load_env(path: Path = ENV_FILE) -> dict[str, str]:
    """Minimal .env parser: KEY=VALUE lines, ignores comments and blanks."""
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip("'\"")
    return env


def _env(defaults: dict[str, str]) -> dict[str, str]:
    """Merge .env file with os.environ (os.environ takes precedence)."""
    merged = defaults | load_env()
    for key in defaults:
        if key in os.environ:
            merged[key] = os.environ[key]
    return merged


def get_config() -> dict[str, str]:
    return _env({
        "SC_CONCURRENT_FRAGMENTS": DEFAULT_CONCURRENT_FRAGMENTS,
    })


def validate_url(value: str) -> str:
    """Accept any https URL."""
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise argparse.ArgumentTypeError("passa un URL https valido")
    return value


def positive_int(value: str) -> int:
    """Parse a strictly positive integer for argparse."""
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("deve essere un numero intero") from error
    if number < 1:
        raise argparse.ArgumentTypeError("deve essere maggiore di zero")
    return number


def build_command(
    url: str,
    temporary_dir: Path,
    filepath_marker: Path,
    concurrent_fragments: int = 1,
    yt_dlp: str = "yt-dlp",
) -> list[str]:
    command = [
        yt_dlp,
        "--no-playlist",
        "--restrict-filenames",
        "--no-write-comments",
        "--concurrent-fragments",
        str(concurrent_fragments),
    ]
    command.extend(
        [
            "--format",
            (
                # Keep every audio stream exposed by the manifest. This is more
                # reliable than guessing the original language from metadata,
                # which is frequently absent or inconsistent across providers.
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
        ]
    )
    command.append(url)
    return command


def parser() -> argparse.ArgumentParser:
    config = get_config()
    result = argparse.ArgumentParser(
        description="Scarica un titolo via yt-dlp."
    )
    result.add_argument("url", type=validate_url)
    result.add_argument(
        "--output-path",
        type=Path,
        metavar="FILE",
        help="percorso del file MKV finale (default: ~/Downloads/<titolo>.mkv)",
    )
    result.add_argument(
        "--concurrent-fragments",
        type=positive_int,
        default=positive_int(config["SC_CONCURRENT_FRAGMENTS"]),
        metavar="N",
        help=f"numero di frammenti scaricati in parallelo (default: {config['SC_CONCURRENT_FRAGMENTS']})",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)

    yt_dlp = shutil.which("yt-dlp")
    local_yt_dlp = Path(sys.executable).with_name("yt-dlp")
    if yt_dlp is None and local_yt_dlp.is_file():
        yt_dlp = str(local_yt_dlp)
    if yt_dlp is None:
        print(
            "Errore: yt-dlp non trovato. Segui le istruzioni nel README.",
            file=sys.stderr,
        )
        return 2

    if shutil.which("ffmpeg") is None:
        print(
            "Errore: ffmpeg non trovato. Segui le istruzioni nel README.",
            file=sys.stderr,
        )
        return 2

    # Keep subtitles, fragments and yt-dlp state out of the working directory.
    with tempfile.TemporaryDirectory(prefix="streaming-downloader-") as directory:
        temporary_dir = Path(directory)
        filepath_marker = temporary_dir / ".last-download-path"
        command = build_command(
            args.url, temporary_dir, filepath_marker, args.concurrent_fragments, yt_dlp
        )

        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as error:
            print(f"yt-dlp è terminato con codice {error.returncode}", file=sys.stderr)
            return error.returncode or 1

        if not filepath_marker.is_file():
            print(
                "Errore: impossibile determinare il file scaricato.",
                file=sys.stderr,
            )
            return 1

        marker_lines = filepath_marker.read_text(encoding="utf-8").splitlines()
        if not marker_lines:
            print(
                "Errore: impossibile determinare il file scaricato.",
                file=sys.stderr,
            )
            return 1

        downloaded_video = Path(marker_lines[-1].strip())
        destination = args.output_path or Path.home() / "Downloads" / downloaded_video.name
        destination = destination.expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(downloaded_video), destination)
        print(destination)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
