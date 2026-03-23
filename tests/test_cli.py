from __future__ import annotations

import unittest

from instadow.cli import build_parser, instagram_url
from instadow.downloader import DownloadOptions, DownloadTracker, build_ydl_options


class InstagramUrlTests(unittest.TestCase):
    def test_adds_https_when_scheme_is_missing(self) -> None:
        self.assertEqual(
            instagram_url("www.instagram.com/reel/abc123/"),
            "https://www.instagram.com/reel/abc123/",
        )

    def test_rejects_non_instagram_hosts(self) -> None:
        with self.assertRaisesRegex(Exception, "Instagram"):
            instagram_url("https://example.com/reel/abc123/")


class ParserTests(unittest.TestCase):
    def test_default_output_directory_is_downloads(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["https://www.instagram.com/p/abc123/"])
        self.assertEqual(args.output_dir, "downloads")
        self.assertFalse(args.write_caption)


class DownloaderOptionTests(unittest.TestCase):
    def test_build_ydl_options_maps_flags(self) -> None:
        options = DownloadOptions(
            output_dir=__import__("pathlib").Path("downloads"),
            filename_template="%(title)s.%(ext)s",
            cookies_file=__import__("pathlib").Path("cookies.txt"),
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


if __name__ == "__main__":
    unittest.main()
