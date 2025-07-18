# manifest-mux

`manifest-mux` is a manifest-aware command-line wrapper around
`yt-dlp`. It downloads a single movie or TV episode from supported HLS embed
pages and can inspect any source that yt-dlp understands, including HLS and
DASH manifests.

It includes a custom source adapter for StreamingCommunity-style `watch` and
`titles` URLs, such as `https://example.com/it/watch/12015?e=38156`. Other
sources are resolved by yt-dlp's built-in extractors.

The application is intended for content you are allowed to download. Make sure
your use complies with the provider's terms and applicable law.

## What it downloads

For each requested title, the downloader:

- selects the best available video stream;
- keeps every audio stream exposed by the manifest, rather than guessing a
  preferred language;
- downloads all available subtitles except live chat, converts them to WebVTT,
  and embeds them in the final file;
- merges the selected streams into a single Matroska (`.mkv`) container;
- downloads one title at a time, never a whole playlist.

Fragments, subtitle files, and yt-dlp state are created in the system temporary
directory. When the download completes, only the final MKV is moved to the
chosen destination.

The downloader retries each unavailable HLS fragment up to 30 times and aborts
if it still cannot be recovered. It never presents an output with a known
missing section as a successful archive.

Before delivering the final file, the application uses `ffprobe` to verify that
the container contains both a video and an audio stream.

## Installation

```bash
uv sync
```

On macOS, install `ffmpeg` with Homebrew:

```bash
brew install ffmpeg
```

## Commands

The original shorthand remains supported:

```bash
uv run manifest-mux 'https://example.com/it/watch/12015?e=38156' \
  --output ~/Movies/my-title.mkv
```

It is equivalent to the explicit `download` command:

```bash
uv run manifest-mux download 'https://example.com/it/watch/12015?e=38156' \
  --output ~/Movies/my-title.mkv
```

Use these read-only commands to understand a source before downloading it:

```bash
# Print yt-dlp metadata as JSON
uv run manifest-mux inspect 'https://example.com/it/watch/12015?e=38156'

# List video, audio, and subtitle formats
uv run manifest-mux formats 'https://example.com/it/watch/12015?e=38156'

# Check local tool availability
uv run manifest-mux doctor
```

Always wrap pasted URLs in single quotes. In particular, zsh interprets `?` as
a wildcard, so an unquoted URL containing `?e=...` is rejected by the shell
before the application receives it.

## Download options

- `-o, --output FILE`: exact path and filename for the final MKV. If omitted,
  the output is `~/Downloads/<title>.mkv`.
- `--sample [SECONDS]`: download only the beginning while still running normal
  muxing, subtitle embedding, and validation. Without a value, it downloads the
  first 60 seconds.
- `--debug`: show detailed yt-dlp/ffmpeg diagnostics and preserve temporary
  files when an error occurs.

For a quick end-to-end test that downloads the first 60 seconds and verifies
the resulting muxed file:

```bash
uv run manifest-mux download 'https://example.com/it/watch/12015?e=38156' \
  --sample \
  --output ~/Movies/my-title-sample.mkv
```

HLS/DASH streams are segmented, so the actual duration can be slightly longer
than the requested number of seconds.

## Architecture

The command-line layer coordinates small, testable components:

```text
CLI
 ├── TrackSelection and DownloadOptions
 ├── YtDlpClient
 │    ├── provider/custom extractors
 │    └── HLS or DASH manifest download
 ├── ffprobe media validation
 └── output delivery and temporary workspace cleanup
```

Track selection is language-agnostic by default: the application preserves all
audio streams and all subtitle languages exposed by a manifest. No preferred
language is assumed by the application or baked into an extractor.

## Tests

```bash
uv run python -m unittest discover -s tests -v
```
