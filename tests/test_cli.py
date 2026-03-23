from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from instadow.cli import build_parser, instagram_target
from instadow.downloader import DownloadOptions, DownloadTarget, DownloadTracker, build_ydl_options, download


class InstagramTargetTests(unittest.TestCase):
    def test_adds_https_when_scheme_is_missing_for_media_url(self) -> None:
        self.assertEqual(
            instagram_target("www.instagram.com/reel/abc123/"),
            DownloadTarget(
                raw="www.instagram.com/reel/abc123/",
                kind="media",
                value="https://www.instagram.com/reel/abc123/",
            ),
        )

    def test_rejects_non_instagram_hosts(self) -> None:
        with self.assertRaisesRegex(Exception, "Instagram"):
            instagram_target("https://example.com/reel/abc123/")

    def test_accepts_profile_urls(self) -> None:
        self.assertEqual(
            instagram_target("https://www.instagram.com/11_14_42/"),
            DownloadTarget(
                raw="https://www.instagram.com/11_14_42/",
                kind="profile",
                value="11_14_42",
            ),
        )

    def test_accepts_usernames(self) -> None:
        self.assertEqual(
            instagram_target("@11_14_42"),
            DownloadTarget(raw="@11_14_42", kind="profile", value="11_14_42"),
        )


class ParserTests(unittest.TestCase):
    def test_default_output_directory_is_downloads(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["https://www.instagram.com/p/abc123/"])
        self.assertEqual(args.output_dir, "downloads")
        self.assertFalse(args.write_caption)
        self.assertFalse(args.no_reels)


class DownloaderOptionTests(unittest.TestCase):
    def test_build_ydl_options_maps_flags(self) -> None:
        options = DownloadOptions(
            output_dir=Path("downloads"),
            filename_template="%(title)s.%(ext)s",
            cookies_file=Path("cookies.txt"),
            write_caption=True,
            write_thumbnail=True,
            print_info=True,
            verbose=True,
        )

        ydl_options = build_ydl_options(options, DownloadTracker())

        self.assertEqual(ydl_options["paths"]["home"], "downloads")
        self.assertEqual(ydl_options["outtmpl"], "%(title)s.%(ext)s")
        self.assertEqual(ydl_options["cookiefile"], "cookies.txt")
        self.assertTrue(ydl_options["writedescription"])
        self.assertTrue(ydl_options["writethumbnail"])
        self.assertTrue(ydl_options["skip_download"])
        self.assertFalse(ydl_options["quiet"])


class ProfileDownloadTests(unittest.TestCase):
    def test_anonymous_profile_error_suggests_login(self) -> None:
        class DummyProfileNotExistsException(Exception):
            pass

        class DummyProfile:
            @staticmethod
            def from_username(_context, _username):
                raise DummyProfileNotExistsException("Profile instagram does not exist.")

        class DummyLoader:
            context = object()

            def close(self) -> None:
                return None

        with TemporaryDirectory() as tmpdir:
            options = DownloadOptions(output_dir=Path(tmpdir))
            targets = [DownloadTarget(raw="instagram", kind="profile", value="instagram")]

            with patch(
                "instadow.downloader._load_instaloader",
                return_value=(
                    object(),
                    DummyProfile,
                    Exception,
                    Exception,
                    Exception,
                    Exception,
                    DummyProfileNotExistsException,
                ),
            ):
                with patch("instadow.downloader._build_instaloader", return_value=DummyLoader()):
                    with self.assertRaisesRegex(RuntimeError, "Thu lai voi `--login <instagram_username>`"):
                        download(targets, options)


if __name__ == "__main__":
    unittest.main()
