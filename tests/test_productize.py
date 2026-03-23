from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from instadow.cli import _effective_config, _load_targets_from_file, build_parser, main
from instadow.config import AppConfig, config_to_dict, load_config, save_config


class ConfigTests(unittest.TestCase):
    def test_save_and_load_config_roundtrip(self) -> None:
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config = AppConfig(
                output_dir="C:/downloads",
                cookies_file="C:/cookies.txt",
                write_caption=True,
                reels_only=True,
                max_posts=15,
            )

            save_config(config_path, config)
            loaded_config = load_config(config_path)

        self.assertEqual(config_to_dict(loaded_config), config_to_dict(config))

    def test_effective_config_prefers_cli_values(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--output-dir", "custom", "--write-caption", "demo_user"])
        saved = AppConfig(output_dir="saved", write_caption=False, max_posts=10)

        effective = _effective_config(args, saved)

        self.assertEqual(effective.output_dir, str(Path("custom").resolve()))
        self.assertTrue(effective.write_caption)
        self.assertEqual(effective.max_posts, 10)

    def test_save_config_command_can_run_without_targets(self) -> None:
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            exit_code = main(["--config", str(config_path), "--output-dir", "custom", "--save-config"])

            self.assertEqual(exit_code, 0)
            saved = load_config(config_path)

        self.assertEqual(saved.output_dir, str(Path("custom").resolve()))


class TargetsFileTests(unittest.TestCase):
    def test_load_targets_from_file_skips_comments_and_dedupes(self) -> None:
        with TemporaryDirectory() as tmpdir:
            targets_path = Path(tmpdir) / "targets.txt"
            targets_path.write_text(
                "# comment\n"
                "11_14_42\n"
                "https://www.instagram.com/p/ABC123/\n"
                "11_14_42\n",
                encoding="utf-8",
            )

            targets = _load_targets_from_file(targets_path)

        self.assertEqual(len(targets), 2)
        self.assertEqual(targets[0].kind, "profile")
        self.assertEqual(targets[0].value, "11_14_42")
        self.assertEqual(targets[1].kind, "media")


if __name__ == "__main__":
    unittest.main()
