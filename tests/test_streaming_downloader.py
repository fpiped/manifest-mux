import argparse
import io
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from streaming_downloader import (
    DownloadOptions,
    build_command,
    parser,
    positive_int,
    run_download,
    validate_url,
)


SAMPLE_URL = "https://example.com/it/watch/12015"


class UrlValidationTests(unittest.TestCase):
    def test_accepts_https_url(self) -> None:
        self.assertEqual(validate_url(SAMPLE_URL), SAMPLE_URL)
        self.assertEqual(
            validate_url("https://example.com/watch/7942"),
            "https://example.com/watch/7942",
        )

    def test_rejects_non_https(self) -> None:
        for value in ["http://example.com", "ftp://example.com", "not-a-url"]:
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    validate_url(value)


class CommandTests(unittest.TestCase):
    def test_download_is_single_title_and_mkv(self) -> None:
        marker = Path(".last-download-path")
        command = build_command(SAMPLE_URL, Path("/tmp/download"), marker)
        self.assertIn("--no-playlist", command)
        self.assertIn("--concurrent-fragments", command)
        self.assertEqual(command[command.index("--concurrent-fragments") + 1], "1")
        self.assertIn("--fragment-retries", command)
        self.assertEqual(command[command.index("--fragment-retries") + 1], "10")
        self.assertIn("--merge-output-format", command)
        format_value = command[command.index("--format") + 1]
        self.assertEqual(format_value, "bestvideo*+mergeall[vcodec=none]/best")
        self.assertIn("--audio-multistreams", command)
        self.assertEqual(command[command.index("--sub-langs") + 1], "all,-live_chat")
        self.assertIn("--embed-subs", command)
        self.assertNotIn("--abort-on-unavailable-fragments", command)

        output_value = command[command.index("--output") + 1]
        self.assertEqual(output_value, "/tmp/download/%(title)s.%(ext)s")
        print_index = command.index("--print-to-file")
        self.assertEqual(command[print_index + 1], "after_dl:%(filepath)s")
        self.assertEqual(command[print_index + 2], str(marker))
        self.assertEqual(command[-1], SAMPLE_URL)

    def test_strict_fragment_mode_is_passed_to_yt_dlp(self) -> None:
        options = DownloadOptions(concurrent_fragments=4, fragment_retries=30, strict_fragments=True)
        command = build_command(SAMPLE_URL, Path("/tmp/download"), Path("marker"), options)
        self.assertEqual(command[command.index("--concurrent-fragments") + 1], "4")
        self.assertEqual(command[command.index("--fragment-retries") + 1], "30")
        self.assertIn("--abort-on-unavailable-fragments", command)

    def test_parser_exposes_recovery_options(self) -> None:
        args = parser().parse_args(
            [SAMPLE_URL, "--fragment-retries", "25", "--strict-fragments", "--keep-temp-on-error"]
        )
        self.assertEqual(args.fragment_retries, 25)
        self.assertTrue(args.strict_fragments)
        self.assertTrue(args.keep_temp_on_error)

    def test_positive_int_must_be_positive(self) -> None:
        self.assertEqual(positive_int("3"), 3)
        for value in ["0", "-1", "not-a-number"]:
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    positive_int(value)


class DownloadLifecycleTests(unittest.TestCase):
    def test_success_moves_final_video_and_removes_temporary_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            destination = root / "output" / "movie.mkv"

            def complete_download(command: list[str], check: bool) -> None:
                marker = Path(command[command.index("--print-to-file") + 2])
                video = marker.parent / "movie.mkv"
                video.write_text("video")
                marker.write_text(str(video), encoding="utf-8")

            with (
                patch("streaming_downloader.tempfile.mkdtemp", return_value=str(workspace)),
                patch("streaming_downloader.subprocess.run", side_effect=complete_download),
            ):
                result = run_download(
                    SAMPLE_URL,
                    options=DownloadOptions(),
                    yt_dlp="yt-dlp",
                    output_path=destination,
                )

            self.assertEqual(result, 0)
            self.assertEqual(destination.read_text(), "video")
            self.assertFalse(workspace.exists())

    def test_failed_download_keeps_workspace_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            workspace.mkdir()
            stderr = io.StringIO()
            with (
                patch("streaming_downloader.tempfile.mkdtemp", return_value=str(workspace)),
                patch(
                    "streaming_downloader.subprocess.run",
                    side_effect=subprocess.CalledProcessError(1, ["yt-dlp"]),
                ),
                redirect_stderr(stderr),
            ):
                result = run_download(
                    SAMPLE_URL,
                    options=DownloadOptions(),
                    yt_dlp="yt-dlp",
                    keep_temp_on_error=True,
                )

            self.assertEqual(result, 1)
            self.assertTrue(workspace.exists())
            self.assertIn(f"Temporary files kept at: {workspace}", stderr.getvalue())
            shutil.rmtree(workspace)

    def test_failed_download_removes_workspace_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            workspace.mkdir()
            with (
                patch("streaming_downloader.tempfile.mkdtemp", return_value=str(workspace)),
                patch(
                    "streaming_downloader.subprocess.run",
                    side_effect=subprocess.CalledProcessError(1, ["yt-dlp"]),
                ),
            ):
                result = run_download(SAMPLE_URL, options=DownloadOptions(), yt_dlp="yt-dlp")

            self.assertEqual(result, 1)
            self.assertFalse(workspace.exists())


if __name__ == "__main__":
    unittest.main()
