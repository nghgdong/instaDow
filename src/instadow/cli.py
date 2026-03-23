from __future__ import annotations

import argparse
from pathlib import Path
import sys
from urllib.parse import urlparse

from .downloader import DownloadOptions, download


SUPPORTED_HOSTS = {"instagram.com", "www.instagram.com", "m.instagram.com", "instagr.am"}


def instagram_url(value: str) -> str:
    candidate = value.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate.lstrip('/')}"

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise argparse.ArgumentTypeError("URL phai bat dau bang http:// hoac https://")

    if parsed.netloc.lower() not in SUPPORTED_HOSTS:
        raise argparse.ArgumentTypeError("Chi ho tro URL cua Instagram.")

    if not parsed.path or parsed.path == "/":
        raise argparse.ArgumentTypeError("URL Instagram chua co duong dan bai post hoac reel.")

    return candidate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="instadow",
        description="Tai anh, video va reels tu Instagram public URLs.",
    )
    parser.add_argument(
        "urls",
        nargs="+",
        type=instagram_url,
        help="Mot hoac nhieu Instagram URLs can tai.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="downloads",
        help="Thu muc luu file. Mac dinh: downloads",
    )
    parser.add_argument(
        "-t",
        "--template",
        dest="filename_template",
        help="Mau ten file theo output template cua yt-dlp.",
    )
    parser.add_argument(
        "--cookies-file",
        help="Duong dan toi file cookies.txt neu URL can dang nhap.",
    )
    parser.add_argument(
        "--write-caption",
        action="store_true",
        help="Luu them caption ra file mo ta.",
    )
    parser.add_argument(
        "--write-thumbnail",
        action="store_true",
        help="Luu them thumbnail neu co.",
    )
    parser.add_argument(
        "--print-info",
        action="store_true",
        help="In metadata JSON ma khong tai media.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Bat log chi tiet cua yt-dlp.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    options = DownloadOptions(
        output_dir=Path(args.output_dir).resolve(),
        filename_template=args.filename_template,
        cookies_file=Path(args.cookies_file).resolve() if args.cookies_file else None,
        write_caption=args.write_caption,
        write_thumbnail=args.write_thumbnail,
        print_info=args.print_info,
        verbose=args.verbose,
    )

    try:
        result = download(args.urls, options)
    except RuntimeError as exc:
        print(f"Download that bai: {exc}", file=sys.stderr)
        return 1

    if options.print_info:
        print(f"Da trich xuat metadata cho {result.inspected_items} URL(s).")
        return 0

    if result.downloaded_files:
        print(f"Tai thanh cong {len(result.downloaded_files)} file vao {options.output_dir}")
        for file_path in result.downloaded_files:
            print(file_path)
    else:
        print(f"Lenh da chay xong. Kiem tra file trong {options.output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

