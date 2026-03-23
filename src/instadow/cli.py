from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

from .downloader import DownloadOptions, DownloadTarget, download


SUPPORTED_HOSTS = {"instagram.com", "www.instagram.com", "m.instagram.com", "instagr.am"}
SUPPORTED_MEDIA_TYPES = {"p", "reel", "reels", "tv"}
PROFILE_TAB_PATHS = {"reels", "tagged"}
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._]+$")


def _normalize_instagram_url(value: str) -> str:
    candidate = value.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate.lstrip('/')}"
    return candidate


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Gia tri phai la so nguyen duong.") from exc

    if number < 1:
        raise argparse.ArgumentTypeError("Gia tri phai lon hon 0.")

    return number


def instagram_target(value: str) -> DownloadTarget:
    raw_value = value.strip()
    if not raw_value:
        raise argparse.ArgumentTypeError("Target khong duoc de trong.")

    if "://" in raw_value or "instagram.com/" in raw_value or "instagr.am/" in raw_value:
        candidate = _normalize_instagram_url(raw_value)
        parsed = urlparse(candidate)

        if parsed.scheme not in {"http", "https"}:
            raise argparse.ArgumentTypeError("URL phai bat dau bang http:// hoac https://")

        if parsed.netloc.lower() not in SUPPORTED_HOSTS:
            raise argparse.ArgumentTypeError("Chi ho tro URL cua Instagram.")

        path_parts = [part for part in parsed.path.split("/") if part]
        if not path_parts:
            raise argparse.ArgumentTypeError("URL Instagram chua co duong dan post, reel hoac profile.")

        first = path_parts[0].lower()
        if first in SUPPORTED_MEDIA_TYPES:
            if len(path_parts) < 2:
                raise argparse.ArgumentTypeError("URL media cua Instagram chua co media id.")
            return DownloadTarget(raw=raw_value, kind="media", value=candidate)

        if len(path_parts) == 1 or (len(path_parts) == 2 and path_parts[1].lower() in PROFILE_TAB_PATHS):
            username = path_parts[0].lstrip("@")
            if not USERNAME_PATTERN.fullmatch(username):
                raise argparse.ArgumentTypeError("Username Instagram khong hop le.")
            return DownloadTarget(raw=raw_value, kind="profile", value=username)

        raise argparse.ArgumentTypeError(
            "Chi ho tro media URLs nhu /p/<id>/, /reel/<id>/, /tv/<id>/ va profile URLs nhu /<username>/."
        )

    username = raw_value.lstrip("@")
    if not USERNAME_PATTERN.fullmatch(username):
        raise argparse.ArgumentTypeError(
            "Target phai la Instagram URL hop le hoac username nhu `nghgdong`."
        )

    return DownloadTarget(raw=raw_value, kind="profile", value=username)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="instadow",
        description="Tai post, reel va profile tu Instagram.",
    )
    parser.add_argument(
        "targets",
        nargs="+",
        type=instagram_target,
        help="Instagram media URL, profile URL hoac username can tai.",
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
        help="Mau ten file cho media URL theo output template cua yt-dlp.",
    )
    parser.add_argument(
        "--profile-template",
        help="Mau ten file cho asset profile do Instaloader quan ly, vi du profile pic.",
    )
    parser.add_argument(
        "--cookies-file",
        help="Duong dan toi file cookies.txt cho media URLs hoac profile downloads neu can dang nhap.",
    )
    parser.add_argument(
        "--login",
        dest="login_user",
        help="Dang nhap Instagram bang username nay khi tai profile. Neu co session file thi se dung session truoc.",
    )
    parser.add_argument(
        "--session-file",
        help="Duong dan toi session file cua instaloader de dung cho profile downloads.",
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
        "--max-posts",
        type=positive_int,
        help="Gioi han so item moi luot quet profile.",
    )
    parser.add_argument(
        "--no-reels",
        action="store_true",
        help="Khong tai reels khi target la profile.",
    )
    parser.add_argument(
        "--reels-only",
        action="store_true",
        help="Chi tai reels khi target la profile.",
    )
    parser.add_argument(
        "--no-profile-pic",
        action="store_true",
        help="Khong tai avatar khi target la profile.",
    )
    parser.add_argument(
        "--fast-update",
        action="store_true",
        help="Dung lai khi gap item da tai truoc do. Huu ich khi cap nhat profile.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Bat log chi tiet cua yt-dlp va instaloader.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    options = DownloadOptions(
        output_dir=Path(args.output_dir).resolve(),
        filename_template=args.filename_template,
        profile_template=args.profile_template,
        cookies_file=Path(args.cookies_file).resolve() if args.cookies_file else None,
        login_user=args.login_user,
        session_file=Path(args.session_file).resolve() if args.session_file else None,
        write_caption=args.write_caption,
        write_thumbnail=args.write_thumbnail,
        print_info=args.print_info,
        verbose=args.verbose,
        include_profile_reels=args.reels_only or not args.no_reels,
        profile_reels_only=args.reels_only,
        include_profile_pic=not args.no_profile_pic,
        profile_limit=args.max_posts,
        fast_update=args.fast_update,
    )

    try:
        result = download(args.targets, options)
    except RuntimeError as exc:
        print(f"Download that bai: {exc}", file=sys.stderr)
        return 1

    if options.print_info:
        print(f"Da trich xuat metadata cho {result.inspected_items} target(s).")
        return 0

    if result.downloaded_files:
        print(f"Tai thanh cong {len(result.downloaded_files)} file vao {options.output_dir}")
        for file_path in result.downloaded_files:
            print(file_path)
    elif result.downloaded_profiles:
        print(f"Da xu ly {len(result.downloaded_profiles)} profile trong {options.output_dir}")
    else:
        print(f"Lenh da chay xong. Kiem tra file trong {options.output_dir}")

    if result.downloaded_profiles:
        print("Profiles:", ", ".join(result.downloaded_profiles))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
