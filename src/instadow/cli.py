from __future__ import annotations

import argparse
from http.cookiejar import MozillaCookieJar
from importlib.metadata import PackageNotFoundError, version as package_version
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import urlparse

from . import __version__
from .config import AppConfig, config_to_dict, default_config_path, delete_config, load_config, save_config
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


def _package_version(name: str) -> str:
    try:
        return package_version(name)
    except PackageNotFoundError:
        return "not-installed"


def _resolve_path_string(value: str | None) -> str | None:
    if not value:
        return None
    return str(Path(value).expanduser().resolve())


def _resolve_value(cli_value, saved_value, fallback):
    if cli_value is not None:
        return cli_value
    if saved_value is not None:
        return saved_value
    return fallback


def _effective_config(args: argparse.Namespace, saved_config: AppConfig) -> AppConfig:
    return AppConfig(
        output_dir=_resolve_path_string(_resolve_value(args.output_dir, saved_config.output_dir, "downloads")),
        filename_template=_resolve_value(args.filename_template, saved_config.filename_template, None),
        profile_template=_resolve_value(args.profile_template, saved_config.profile_template, None),
        cookies_file=_resolve_path_string(_resolve_value(args.cookies_file, saved_config.cookies_file, None)),
        login_user=_resolve_value(args.login_user, saved_config.login_user, None),
        session_file=_resolve_path_string(_resolve_value(args.session_file, saved_config.session_file, None)),
        write_caption=_resolve_value(args.write_caption, saved_config.write_caption, False),
        write_thumbnail=_resolve_value(args.write_thumbnail, saved_config.write_thumbnail, False),
        max_posts=_resolve_value(args.max_posts, saved_config.max_posts, None),
        no_reels=_resolve_value(args.no_reels, saved_config.no_reels, False),
        reels_only=_resolve_value(args.reels_only, saved_config.reels_only, False),
        no_profile_pic=_resolve_value(args.no_profile_pic, saved_config.no_profile_pic, False),
        fast_update=_resolve_value(args.fast_update, saved_config.fast_update, False),
        verbose=_resolve_value(args.verbose, saved_config.verbose, False),
    )


def _load_targets_from_file(path: Path) -> list[DownloadTarget]:
    if not path.is_file():
        raise RuntimeError(f"Khong tim thay targets file: {path}")

    targets: list[DownloadTarget] = []
    seen_targets: set[tuple[str, str]] = set()
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        try:
            target = instagram_target(stripped)
        except argparse.ArgumentTypeError as exc:
            raise RuntimeError(f"Loi trong targets file {path} dong {line_number}: {exc}") from exc

        key = (target.kind, target.value)
        if key in seen_targets:
            continue
        seen_targets.add(key)
        targets.append(target)

    return targets


def _merge_targets(direct_targets: list[DownloadTarget], file_targets: list[DownloadTarget]) -> list[DownloadTarget]:
    merged_targets: list[DownloadTarget] = []
    seen_targets: set[tuple[str, str]] = set()

    for target in [*direct_targets, *file_targets]:
        key = (target.kind, target.value)
        if key in seen_targets:
            continue
        seen_targets.add(key)
        merged_targets.append(target)

    return merged_targets


def _inspect_cookie_file(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"configured": False}

    info: dict[str, Any] = {
        "configured": True,
        "path": str(path),
        "exists": path.is_file(),
    }
    if not path.is_file():
        return info

    jar = MozillaCookieJar()
    try:
        jar.load(str(path), ignore_discard=True, ignore_expires=True)
    except OSError as exc:
        info["load_error"] = str(exc)
        return info

    cookie_names = [cookie.name for cookie in jar if "instagram" in (cookie.domain or "")]
    info["instagram_cookie_count"] = len(cookie_names)
    info["has_sessionid"] = "sessionid" in cookie_names
    info["has_csrftoken"] = "csrftoken" in cookie_names
    info["has_ds_user_id"] = "ds_user_id" in cookie_names
    return info


def _self_check_payload(
    config_path: Path,
    saved_config: AppConfig,
    effective_config: AppConfig,
    targets: list[DownloadTarget],
    targets_file: Path | None,
) -> dict[str, Any]:
    return {
        "instadow_version": __version__,
        "python_version": sys.version,
        "python_executable": sys.executable,
        "working_directory": str(Path.cwd()),
        "dependencies": {
            "yt-dlp": _package_version("yt-dlp"),
            "instaloader": _package_version("instaloader"),
        },
        "config": {
            "path": str(config_path),
            "exists": config_path.is_file(),
            "saved": config_to_dict(saved_config),
            "effective": config_to_dict(effective_config),
        },
        "targets": {
            "count": len(targets),
            "from_file": str(targets_file) if targets_file else None,
            "items": [{"kind": target.kind, "value": target.value} for target in targets],
        },
        "cookies": _inspect_cookie_file(Path(effective_config.cookies_file) if effective_config.cookies_file else None),
        "session_file": {
            "configured": effective_config.session_file is not None,
            "path": effective_config.session_file,
            "exists": Path(effective_config.session_file).is_file() if effective_config.session_file else False,
        },
    }


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="instadow",
        description="Tai post, reel va profile tu Instagram.",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        type=instagram_target,
        help="Instagram media URL, profile URL hoac username can tai.",
    )
    parser.add_argument(
        "--targets-file",
        help="File text chua danh sach media URL hoac username, moi dong mot target.",
    )
    parser.add_argument(
        "--config",
        help="Duong dan toi file config JSON. Mac dinh nam trong LOCALAPPDATA/instadow/config.json.",
    )
    parser.add_argument(
        "--save-config",
        action="store_true",
        help="Luu cac option hien tai thanh mac dinh cho cac lan chay sau.",
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="In config dang luu va config hieu luc sau khi merge voi option hien tai.",
    )
    parser.add_argument(
        "--reset-config",
        action="store_true",
        help="Xoa file config dang luu.",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="In thong tin chan doan moi truong, config, cookies va targets.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=None,
        help="Thu muc luu file. Mac dinh: downloads hoac gia tri trong config.",
    )
    parser.add_argument(
        "-t",
        "--template",
        dest="filename_template",
        default=None,
        help="Mau ten file cho media URL theo output template cua yt-dlp.",
    )
    parser.add_argument(
        "--profile-template",
        default=None,
        help="Mau ten file cho asset profile do Instaloader quan ly, vi du profile pic.",
    )
    parser.add_argument(
        "--cookies-file",
        default=None,
        help="Duong dan toi file cookies.txt cho media URLs hoac profile downloads neu can dang nhap.",
    )
    parser.add_argument(
        "--login",
        dest="login_user",
        default=None,
        help="Dang nhap Instagram bang username nay khi tai profile. Neu co session file thi se dung session truoc.",
    )
    parser.add_argument(
        "--session-file",
        default=None,
        help="Duong dan toi session file cua instaloader de dung cho profile downloads.",
    )
    parser.add_argument(
        "--write-caption",
        action="store_true",
        default=None,
        help="Luu them caption ra file mo ta.",
    )
    parser.add_argument(
        "--write-thumbnail",
        action="store_true",
        default=None,
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
        default=None,
        help="Gioi han so item moi luot quet profile.",
    )
    parser.add_argument(
        "--no-reels",
        action="store_true",
        default=None,
        help="Khong tai reels khi target la profile.",
    )
    parser.add_argument(
        "--reels-only",
        action="store_true",
        default=None,
        help="Chi tai reels khi target la profile.",
    )
    parser.add_argument(
        "--no-profile-pic",
        action="store_true",
        default=None,
        help="Khong tai avatar khi target la profile.",
    )
    parser.add_argument(
        "--fast-update",
        action="store_true",
        default=None,
        help="Dung lai khi gap item da tai truoc do. Huu ich khi cap nhat profile.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=None,
        help="Bat log chi tiet cua yt-dlp va instaloader.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config_path = (
        Path(args.config).expanduser().resolve()
        if args.config
        else default_config_path()
    )

    if args.reset_config:
        deleted = delete_config(config_path)
        print(f"Da xoa config: {config_path}" if deleted else f"Khong co config de xoa: {config_path}")
        if not (args.show_config or args.self_check or args.save_config or args.targets or args.targets_file):
            return 0

    saved_config = load_config(config_path)
    effective_config = _effective_config(args, saved_config)

    if effective_config.no_reels and effective_config.reels_only:
        parser.error("Khong the dung cung luc `--no-reels` va `--reels-only`.")

    direct_targets = list(args.targets or [])
    file_targets = _load_targets_from_file(Path(args.targets_file).expanduser().resolve()) if args.targets_file else []
    targets = _merge_targets(direct_targets, file_targets)

    if args.save_config:
        save_config(config_path, effective_config)
        print(f"Da luu config vao {config_path}")
        saved_config = load_config(config_path)
        if not targets and not (args.show_config or args.self_check):
            return 0

    if args.show_config:
        _print_json(
            {
                "config_path": str(config_path),
                "exists": config_path.is_file(),
                "saved": config_to_dict(saved_config),
                "effective": config_to_dict(effective_config),
            }
        )
        if not targets and not args.self_check:
            return 0

    if args.self_check:
        _print_json(
            _self_check_payload(
                config_path=config_path,
                saved_config=saved_config,
                effective_config=effective_config,
                targets=targets,
                targets_file=Path(args.targets_file).expanduser().resolve() if args.targets_file else None,
            )
        )
        if not targets:
            return 0

    if not targets:
        parser.error("Hay cung cap it nhat 1 target hoac dung `--show-config` / `--self-check` / `--version`.")

    options = DownloadOptions(
        output_dir=Path(effective_config.output_dir or "downloads").expanduser().resolve(),
        filename_template=effective_config.filename_template,
        profile_template=effective_config.profile_template,
        cookies_file=Path(effective_config.cookies_file).resolve() if effective_config.cookies_file else None,
        login_user=effective_config.login_user,
        session_file=Path(effective_config.session_file).resolve() if effective_config.session_file else None,
        write_caption=bool(effective_config.write_caption),
        write_thumbnail=bool(effective_config.write_thumbnail),
        print_info=args.print_info,
        verbose=bool(effective_config.verbose),
        include_profile_reels=bool(effective_config.reels_only) or not bool(effective_config.no_reels),
        profile_reels_only=bool(effective_config.reels_only),
        include_profile_pic=not bool(effective_config.no_profile_pic),
        profile_limit=effective_config.max_posts,
        fast_update=bool(effective_config.fast_update),
    )

    try:
        result = download(targets, options)
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
