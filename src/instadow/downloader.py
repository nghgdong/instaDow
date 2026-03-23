from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Literal


@dataclass(slots=True)
class DownloadTarget:
    raw: str
    kind: Literal["media", "profile"]
    value: str


@dataclass(slots=True)
class DownloadOptions:
    output_dir: Path
    filename_template: str | None = None
    profile_template: str | None = None
    cookies_file: Path | None = None
    login_user: str | None = None
    session_file: Path | None = None
    write_caption: bool = False
    write_thumbnail: bool = False
    print_info: bool = False
    verbose: bool = False
    include_profile_reels: bool = True
    include_profile_pic: bool = True
    profile_limit: int | None = None
    fast_update: bool = False


@dataclass(slots=True)
class ProfileAuth:
    login_user: str
    session_file: Path | None = None
    source: Literal["explicit", "stored", "discovered"] = "explicit"


@dataclass(slots=True)
class DownloadResult:
    downloaded_files: list[Path] = field(default_factory=list)
    downloaded_profiles: list[str] = field(default_factory=list)
    inspected_items: int = 0


class DownloadTracker:
    def __init__(self) -> None:
        self._files: list[Path] = []

    @property
    def files(self) -> list[Path]:
        return self._files

    def hook(self, status: dict) -> None:
        filename = status.get("filename")
        if status.get("status") != "finished" or not filename:
            return

        file_path = Path(filename).resolve()
        if file_path not in self._files:
            self._files.append(file_path)


class YtDlpLogger:
    def __init__(self, verbose: bool) -> None:
        self.verbose = verbose

    def debug(self, message: str) -> None:
        if self.verbose:
            print(message)

    def info(self, message: str) -> None:
        if self.verbose:
            print(message)

    def warning(self, message: str) -> None:
        print(f"[warning] {message}")

    def error(self, message: str) -> None:
        print(f"[error] {message}")


def _load_yt_dlp():
    try:
        import yt_dlp
        from yt_dlp.utils import DownloadError
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "yt-dlp chua duoc cai dat. Hay chay `python -m pip install -e .` hoac `python -m pip install yt-dlp`."
        ) from exc

    return yt_dlp, DownloadError


def _load_instaloader():
    try:
        import instaloader
        from instaloader import Profile
        from instaloader.instaloader import get_default_session_filename, get_legacy_session_filename
        from instaloader.exceptions import (
            ConnectionException,
            InstaloaderException,
            LoginException,
            PrivateProfileNotFollowedException,
            ProfileNotExistsException,
        )
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "instaloader chua duoc cai dat. Hay chay `python -m pip install -e .` hoac `python -m pip install instaloader`."
        ) from exc

    return (
        instaloader,
        Profile,
        get_default_session_filename,
        get_legacy_session_filename,
        ConnectionException,
        InstaloaderException,
        LoginException,
        PrivateProfileNotFollowedException,
        ProfileNotExistsException,
    )


def build_ydl_options(options: DownloadOptions, tracker: DownloadTracker) -> dict:
    ydl_options = {
        "paths": {"home": str(options.output_dir)},
        "logger": YtDlpLogger(options.verbose),
        "progress_hooks": [tracker.hook],
        "quiet": not options.verbose,
        "no_warnings": False,
        "writedescription": options.write_caption,
        "writethumbnail": options.write_thumbnail,
        "skip_download": options.print_info,
    }

    if options.filename_template:
        ydl_options["outtmpl"] = options.filename_template

    if options.cookies_file:
        ydl_options["cookiefile"] = str(options.cookies_file)

    return ydl_options


def _profile_info(profile) -> dict:
    return {
        "username": profile.username,
        "userid": profile.userid,
        "full_name": profile.full_name,
        "biography": profile.biography,
        "followers": profile.followers,
        "followees": profile.followees,
        "mediacount": profile.mediacount,
        "igtvcount": profile.igtvcount,
        "is_private": profile.is_private,
        "is_verified": profile.is_verified,
        "profile_pic_url": str(profile.profile_pic_url),
        "external_url": profile.external_url,
    }


def _collect_files(directory: Path) -> set[Path]:
    if not directory.exists():
        return set()

    return {path.resolve() for path in directory.rglob("*") if path.is_file()}


def _merge_results(target: DownloadResult, source: DownloadResult) -> None:
    existing_files = set(target.downloaded_files)
    for file_path in source.downloaded_files:
        if file_path not in existing_files:
            target.downloaded_files.append(file_path)
            existing_files.add(file_path)

    existing_profiles = set(target.downloaded_profiles)
    for profile_name in source.downloaded_profiles:
        if profile_name not in existing_profiles:
            target.downloaded_profiles.append(profile_name)
            existing_profiles.add(profile_name)

    target.inspected_items += source.inspected_items


def _auth_state_path() -> Path:
    base_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".config"))
    return base_dir / "instadow" / "auth.json"


def _save_auth_state(auth: ProfileAuth) -> None:
    state_path = _auth_state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "login_user": auth.login_user,
        "session_file": str(auth.session_file) if auth.session_file else None,
    }
    state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_saved_auth_state() -> ProfileAuth | None:
    state_path = _auth_state_path()
    if not state_path.is_file():
        return None

    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    login_user = payload.get("login_user")
    if not login_user or not isinstance(login_user, str):
        return None

    session_value = payload.get("session_file")
    session_file = Path(session_value).resolve() if isinstance(session_value, str) and session_value else None
    return ProfileAuth(login_user=login_user, session_file=session_file, source="stored")


def _discover_single_session_auth() -> ProfileAuth | None:
    session_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".config")) / "Instaloader"
    if not session_dir.is_dir():
        return None

    session_files = [path.resolve() for path in session_dir.glob("session-*") if path.is_file()]
    if len(session_files) != 1:
        return None

    session_file = session_files[0]
    login_user = session_file.name.removeprefix("session-").strip()
    if not login_user:
        return None

    return ProfileAuth(login_user=login_user, session_file=session_file, source="discovered")


def _resolve_profile_auth(options: DownloadOptions) -> ProfileAuth | None:
    if options.login_user:
        return ProfileAuth(
            login_user=options.login_user,
            session_file=options.session_file,
            source="explicit",
        )

    saved_auth = _load_saved_auth_state()
    if saved_auth:
        if options.session_file:
            saved_auth.session_file = options.session_file
        return saved_auth

    discovered_auth = _discover_single_session_auth()
    if discovered_auth:
        if options.session_file:
            discovered_auth.session_file = options.session_file
        return discovered_auth

    if options.session_file:
        raise RuntimeError("`--session-file` can di kem `--login <instagram_username>` o lan dau de biet session nay thuoc tai khoan nao.")

    return None


def _resolve_session_file(auth: ProfileAuth):
    (
        _instaloader,
        _profile_class,
        get_default_session_filename,
        get_legacy_session_filename,
        _connection_exception,
        _instaloader_exception,
        _login_exception,
        _private_profile_exception,
        _profile_not_exists_exception,
    ) = _load_instaloader()

    if auth.session_file:
        return auth.session_file.resolve()

    default_path = Path(get_default_session_filename(auth.login_user)).resolve()
    if default_path.exists():
        return default_path

    legacy_path = Path(get_legacy_session_filename(auth.login_user)).resolve()
    if legacy_path.exists():
        return legacy_path

    return default_path


def _login_instaloader(loader, options: DownloadOptions) -> str | None:
    auth = _resolve_profile_auth(options)
    if not auth:
        return None

    session_path = _resolve_session_file(auth)
    session_filename = str(session_path)
    if auth.source == "explicit":
        session_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        loader.load_session_from_file(auth.login_user, session_filename)
        active_user = loader.test_login()
        if active_user is None:
            raise RuntimeError(
                f"Da nap session cho `{auth.login_user}` nhung Instagram tam thoi tu choi yeu cau hoac dang gioi han toc do. "
                "Thu lai sau vai phut, han che spam request, hoac login lai de lam moi session."
            )
        if active_user != auth.login_user:
            raise RuntimeError(
                f"Session dang duoc gan voi tai khoan `{active_user}` thay vi `{auth.login_user}`."
            )
        if options.verbose:
            print(f"Da nap session cho {active_user}")
        _save_auth_state(ProfileAuth(login_user=auth.login_user, session_file=session_path, source="stored"))
        return active_user
    except FileNotFoundError:
        if auth.source == "stored":
            if options.verbose:
                print(f"Khong tim thay saved session cho `{auth.login_user}`, se thu anonymous mode.")
            return None
        if options.verbose:
            print("Chua co session file, se dang nhap tuong tac de tao moi.")
    except RuntimeError:
        raise
    except Exception as exc:
        if auth.source == "stored":
            if options.verbose:
                print(f"Khong the nap saved session cho `{auth.login_user}`: {exc}. Se thu anonymous mode.")
            return None
        if options.verbose:
            print(f"Khong the nap session hien co cho `{auth.login_user}`: {exc}. Se login lai.")

    if auth.source != "explicit":
        return None

    try:
        loader.interactive_login(auth.login_user)
        loader.save_session_to_file(session_filename)
        _save_auth_state(ProfileAuth(login_user=auth.login_user, session_file=session_path, source="stored"))
        return auth.login_user
    except Exception as exc:
        raise RuntimeError(f"Dang nhap Instagram that bai: {exc}") from exc


def _download_media_targets(targets: list[DownloadTarget], options: DownloadOptions) -> DownloadResult:
    yt_dlp, DownloadError = _load_yt_dlp()

    tracker = DownloadTracker()
    ydl_options = build_ydl_options(options, tracker)
    urls = [target.value for target in targets]

    try:
        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            if options.print_info:
                inspected_items = 0
                for url in urls:
                    info = ydl.extract_info(url, download=False)
                    print(json.dumps(ydl.sanitize_info(info), ensure_ascii=False, indent=2))
                    inspected_items += 1
                return DownloadResult(inspected_items=inspected_items)

            error_code = ydl.download(urls)
            if error_code:
                raise RuntimeError(f"yt-dlp tra ve ma loi {error_code}.")
    except DownloadError as exc:
        raise RuntimeError(str(exc)) from exc

    return DownloadResult(downloaded_files=tracker.files)


def _build_instaloader(options: DownloadOptions):
    instaloader, *_ = _load_instaloader()

    return instaloader.Instaloader(
        quiet=not options.verbose and not options.login_user,
        dirname_pattern=str(options.output_dir / "{target}"),
        filename_pattern=options.profile_template,
        download_pictures=True,
        download_videos=True,
        download_video_thumbnails=options.write_thumbnail,
        save_metadata=False,
        compress_json=False,
        post_metadata_txt_pattern="{caption}" if options.write_caption else "",
        sanitize_paths=True,
    )


def _download_profile_targets(targets: list[DownloadTarget], options: DownloadOptions) -> DownloadResult:
    (
        _instaloader,
        Profile,
        _get_default_session_filename,
        _get_legacy_session_filename,
        ConnectionException,
        InstaloaderException,
        LoginException,
        PrivateProfileNotFollowedException,
        ProfileNotExistsException,
    ) = _load_instaloader()

    loader = _build_instaloader(options)
    result = DownloadResult()

    try:
        active_login_user = _login_instaloader(loader, options)

        for target in targets:
            profile_name = target.value

            try:
                profile = Profile.from_username(loader.context, profile_name)
            except ProfileNotExistsException as exc:
                if active_login_user:
                    raise RuntimeError(
                        f"Profile `{profile_name}` khong ton tai hoac khong the truy cap ngay ca khi dang nhap bang `{active_login_user}`."
                    ) from exc
                raise RuntimeError(
                    f"Khong the truy cap profile `{profile_name}` khi chua dang nhap. "
                    "Profile co the khong ton tai hoac Instagram dang chan anonymous access. "
                    "Thu lai voi `--login <instagram_username>`."
                ) from exc
            except (ConnectionException, InstaloaderException) as exc:
                raise RuntimeError(f"Khong the doc thong tin profile `{profile_name}`: {exc}") from exc

            if options.print_info:
                print(json.dumps(_profile_info(profile), ensure_ascii=False, indent=2))
                result.inspected_items += 1
                result.downloaded_profiles.append(profile.username)
                continue

            target_directory = options.output_dir / profile.username
            before_files = _collect_files(target_directory)

            try:
                loader.download_profiles(
                    {profile},
                    profile_pic=options.include_profile_pic,
                    posts=True,
                    fast_update=options.fast_update,
                    raise_errors=True,
                    max_count=options.profile_limit,
                    reels=options.include_profile_reels,
                )
            except PrivateProfileNotFollowedException as exc:
                raise RuntimeError(
                    f"Profile `{profile.username}` la private hoac can dang nhap. Thu lai voi `--login <instagram_username>`."
                ) from exc
            except (LoginException, ConnectionException, InstaloaderException) as exc:
                raise RuntimeError(f"Tai profile `{profile.username}` that bai: {exc}") from exc

            after_files = _collect_files(target_directory)
            result.downloaded_profiles.append(profile.username)
            result.downloaded_files.extend(sorted(after_files - before_files))
    finally:
        loader.close()

    return result


def download(targets: Iterable[DownloadTarget], options: DownloadOptions) -> DownloadResult:
    target_list = list(targets)
    if not target_list:
        return DownloadResult()

    if options.cookies_file and not options.cookies_file.is_file():
        raise RuntimeError(f"Khong tim thay cookies file: {options.cookies_file}")

    if not options.print_info:
        options.output_dir.mkdir(parents=True, exist_ok=True)

    media_targets = [target for target in target_list if target.kind == "media"]
    profile_targets = [target for target in target_list if target.kind == "profile"]

    if profile_targets and options.filename_template:
        print("[warning] --template chi ap dung cho media URL truc tiep. Profile downloads dung --profile-template.")

    result = DownloadResult()

    if media_targets:
        _merge_results(result, _download_media_targets(media_targets, options))

    if profile_targets:
        _merge_results(result, _download_profile_targets(profile_targets, options))

    return result
