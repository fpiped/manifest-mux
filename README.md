# streaming-downloader

Download titles through `yt-dlp` as MKV files, preserving every available audio
track and embedding all available subtitles.

## Installation

```bash
uv sync
```

On macOS, install `ffmpeg` with Homebrew:

```bash
brew install ffmpeg
```

## Usage

```bash
uv run streaming-downloader 'https://example.com/it/watch/12015?e=38156' \
  --output-path ~/Movies/my-title.mkv
```

Arguments:

- `url` (required): HTTPS URL of the title.
- `--output-path FILE`: final MKV file path (default: `~/Downloads/<title>.mkv`).
- `--concurrent-fragments N`: fragments downloaded in parallel (default: 1).

Always wrap pasted URLs in single quotes. In particular, zsh interprets `?` as
a wildcard, so an unquoted URL containing `?e=...` is rejected by the shell
before the application receives it.

All temporary files (fragments, subtitles, and yt-dlp state) are written to the
system temporary directory. Only the final MKV is kept at the selected path.

## Tests

```bash
uv run python -m unittest discover -s tests -v
```
