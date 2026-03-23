from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.cookiejar import MozillaCookieJar
import json
import mimetypes
import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import requests


INSTAGRAM_WEB_APP_ID = "936619743392459"
SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
SUPPORTED_VIDEO_SUFFIXES = {".mp4", ".m4v", ".mov", ".webm"}
SUPPORTED_MEDIA_SUFFIXES = SUPPORTED_IMAGE_SUFFIXES | SUPPORTED_VIDEO_SUFFIXES


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
class ProfileMediaCandidate:
    file_stem: str
    media_kind: Literal["image", "video"]
    media_url: str
    thumbnail_url: str | None = None
    caption_text: str | None = None


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


def _print_json(payload: dict) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        print(text)
    except UnicodeEncodeError:
        print(json.dumps(payload, ensure_ascii=True, indent=2))


def _extract_best_image_url(image_versions: dict | None) -> str | None:
    if not isinstance(image_versions, dict):
        return None

    candidates = image_versions.get("candidates")
    if not isinstance(candidates, list):
        return None

    usable_candidates = [
        candidate
        for candidate in candidates
        if isinstance(candidate, dict) and candidate.get("url")
    ]
    if not usable_candidates:
        return None

    best_candidate = max(
        usable_candidates,
        key=lambda candidate: (
            int(candidate.get("width") or 0) * int(candidate.get("height") or 0),
            int(candidate.get("width") or 0),
            int(candidate.get("height") or 0),
        ),
    )
    return str(best_candidate["url"])


def _extract_best_video_url(video_versions: list | None) -> str | None:
    if not isinstance(video_versions, list):
        return None

    usable_candidates = [
        candidate
        for candidate in video_versions
        if isinstance(candidate, dict) and candidate.get("url")
    ]
    if not usable_candidates:
        return None

    best_candidate = max(
        usable_candidates,
        key=lambda candidate: (
            int(candidate.get("width") or 0) * int(candidate.get("height") or 0),
            int(candidate.get("type") or 0),
            int(candidate.get("width") or 0),
            int(candidate.get("height") or 0),
        ),
    )
    return str(best_candidate["url"])


def _extract_caption_text(item: dict) -> str | None:
    caption = item.get("caption")
    if isinstance(caption, dict):
        text = caption.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return None


def _build_profile_post_url(shortcode: str, product_type: str | None) -> str:
    if str(product_type or "").lower() == "clips":
        return f"https://www.instagram.com/reel/{shortcode}/"
    return f"https://www.instagram.com/p/{shortcode}/"


def _build_feed_media_candidate(
    node: dict,
    file_stem: str,
    caption_text: str | None,
) -> ProfileMediaCandidate | None:
    media_type = node.get("media_type")
    if media_type == 1:
        media_url = _extract_best_image_url(node.get("image_versions2"))
        if not media_url:
            return None
        return ProfileMediaCandidate(
            file_stem=file_stem,
            media_kind="image",
            media_url=media_url,
            caption_text=caption_text,
        )

    if media_type == 2:
        media_url = _extract_best_video_url(node.get("video_versions"))
        if not media_url:
            return None
        return ProfileMediaCandidate(
            file_stem=file_stem,
            media_kind="video",
            media_url=media_url,
            thumbnail_url=_extract_best_image_url(node.get("image_versions2")),
            caption_text=caption_text,
        )

    return None


def _iter_feed_item_media(item: dict, include_reels: bool) -> list[ProfileMediaCandidate]:
    shortcode = item.get("code")
    if not shortcode:
        return []

    product_type = str(item.get("product_type") or "").lower()
    if product_type == "clips" and not include_reels:
        return []

    taken_at = item.get("taken_at")
    if isinstance(taken_at, (int, float)):
        taken_at_dt = datetime.fromtimestamp(float(taken_at), tz=timezone.utc)
    else:
        taken_at_dt = datetime.now(timezone.utc)

    timestamp = taken_at_dt.strftime("%Y%m%d_%H%M%S")
    caption_text = _extract_caption_text(item)
    media_type = item.get("media_type")

    if media_type == 8:
        candidates: list[ProfileMediaCandidate] = []
        for media_index, node in enumerate(item.get("carousel_media") or [], start=1):
            candidate = _build_feed_media_candidate(
                node=node,
                file_stem=f"{timestamp}_{shortcode}_{media_index:02d}",
                caption_text=caption_text,
            )
            if candidate is not None:
                candidates.append(candidate)
        return candidates

    candidate = _build_feed_media_candidate(
        node=item,
        file_stem=f"{timestamp}_{shortcode}_01",
        caption_text=caption_text,
    )
    return [candidate] if candidate is not None else []


def _build_profile_requests_session(loader) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/133.0.0.0 Safari/537.36"
            ),
            "X-IG-App-ID": INSTAGRAM_WEB_APP_ID,
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "*/*",
        }
    )

    loader_session = getattr(loader.context, "_session", None)
    if loader_session is not None:
        user_agent = loader_session.headers.get("User-Agent")
        if user_agent:
            session.headers["User-Agent"] = user_agent

        for cookie in loader_session.cookies:
            session.cookies.set(
                cookie.name,
                cookie.value,
                domain=cookie.domain,
                path=cookie.path,
            )

        for cookie in loader_session.cookies:
            if cookie.name == "csrftoken" and "instagram" in (cookie.domain or ""):
                session.headers["X-CSRFToken"] = cookie.value
                break

    return session


def _collect_files(directory: Path) -> set[Path]:
    if not directory.exists():
        return set()

    return {path.resolve() for path in directory.rglob("*") if path.is_file()}


def _iter_profile_feed_items(
    session: requests.Session,
    profile_name: str,
    profile_url: str,
    limit_posts: int | None,
) -> Iterable[dict]:
    fetched_posts = 0
    next_max_id: str | None = None
    seen_shortcodes: set[str] = set()

    while True:
        remaining = (limit_posts - fetched_posts) if limit_posts else 12
        page_size = min(12, remaining) if limit_posts else 12
        if page_size <= 0:
            return

        params = {"count": page_size}
        if next_max_id:
            params["max_id"] = next_max_id

        response = session.get(
            f"https://www.instagram.com/api/v1/feed/user/{profile_name}/username/",
            params=params,
            headers={"Referer": profile_url},
            timeout=120,
        )

        if response.status_code == 429:
            raise RuntimeError(
                "Instagram dang gioi han toc do profile feed API (429 Too Many Requests). Thu lai sau it phut."
            )
        if response.status_code in {401, 403}:
            raise RuntimeError(
                "Instagram tu choi profile feed API. Thu cookie/session khac hoac doi mot luc roi thu lai."
            )
        response.raise_for_status()

        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError("Instagram tra ve JSON khong hop le cho profile feed.") from exc

        status = str(payload.get("status") or "").lower()
        if status == "fail":
            message = str(payload.get("message") or "Instagram profile feed API failed.")
            raise RuntimeError(message)

        items = payload.get("items") or []
        if not isinstance(items, list):
            raise RuntimeError("Instagram profile feed API tra ve du lieu khong nhu mong doi.")

        for item in items:
            shortcode = item.get("code")
            if not shortcode or shortcode in seen_shortcodes:
                continue
            seen_shortcodes.add(shortcode)
            fetched_posts += 1
            yield item

            if limit_posts and fetched_posts >= limit_posts:
                return

        next_max_id = payload.get("next_max_id")
        if not payload.get("more_available") or not next_max_id:
            return


def _detect_existing_media_file(directory: Path, file_stem: str) -> Path | None:
    for file_path in sorted(directory.glob(f"{file_stem}.*")):
        if file_path.suffix.lower() in SUPPORTED_MEDIA_SUFFIXES and file_path.is_file():
            return file_path.resolve()
    return None


def _choose_media_extension(content_type: str, media_url: str, media_kind: str) -> str:
    mime_type = content_type.split(";", 1)[0].strip().lower()
    extension = mimetypes.guess_extension(mime_type) if mime_type else None
    if extension == ".jpe":
        extension = ".jpg"
    if extension in SUPPORTED_MEDIA_SUFFIXES:
        return extension

    parsed_extension = Path(urlparse(media_url).path).suffix.lower()
    if parsed_extension in SUPPORTED_MEDIA_SUFFIXES:
        return ".jpg" if parsed_extension == ".jpeg" else parsed_extension

    return ".mp4" if media_kind == "video" else ".jpg"


def _download_http_asset(
    session: requests.Session,
    asset_url: str,
    directory: Path,
    file_stem: str,
    media_kind: str,
) -> tuple[Path, bool]:
    existing_file = _detect_existing_media_file(directory, file_stem)
    if existing_file is not None:
        return existing_file, False

    directory.mkdir(parents=True, exist_ok=True)
    response = session.get(asset_url, stream=True, timeout=120)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    extension = _choose_media_extension(content_type, asset_url, media_kind)
    output_path = (directory / f"{file_stem}{extension}").resolve()
    temp_path = output_path.with_suffix(output_path.suffix + ".part")

    try:
        with temp_path.open("wb") as file_handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file_handle.write(chunk)
        temp_path.replace(output_path)
    finally:
        response.close()
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)

    return output_path, True


def _write_caption_file(directory: Path, file_stem: str, caption_text: str | None) -> Path | None:
    if not caption_text:
        return None

    directory.mkdir(parents=True, exist_ok=True)
    caption_path = (directory / f"{file_stem}.txt").resolve()
    if caption_path.is_file():
        try:
            if caption_path.read_text(encoding="utf-8") == caption_text:
                return None
        except OSError:
            pass
    caption_path.write_text(caption_text, encoding="utf-8")
    return caption_path


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


def _load_instaloader_cookies(cookies_file: Path):
    cookie_jar = MozillaCookieJar()
    try:
        cookie_jar.load(str(cookies_file), ignore_discard=True, ignore_expires=True)
    except OSError as exc:
        raise RuntimeError(f"Khong the doc cookies file `{cookies_file}`: {exc}") from exc

    return cookie_jar


def _login_instaloader(loader, options: DownloadOptions) -> str | None:
    if options.cookies_file:
        cookie_jar = _load_instaloader_cookies(options.cookies_file)
        loader.context.update_cookies(cookie_jar)
        active_user = loader.test_login()
        if active_user is None:
            raise RuntimeError(
                f"Da nap cookies tu `{options.cookies_file}` nhung Instagram khong chap nhan session nay. "
                "Hay export lai cookies moi hoac thu login/session khac."
            )
        if options.verbose:
            print(f"Da nap cookies cho {active_user}")
        return active_user

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
                    _print_json(ydl.sanitize_info(info))
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
        feed_session = _build_profile_requests_session(loader)

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
                _print_json(_profile_info(profile))
                result.inspected_items += 1
                result.downloaded_profiles.append(profile.username)
                continue

            target_directory = options.output_dir / profile.username
            before_files = _collect_files(target_directory)

            try:
                if options.include_profile_pic:
                    loader.download_profilepic(profile)

                profile_url = f"https://www.instagram.com/{profile.username}/"
                for item in _iter_profile_feed_items(
                    session=feed_session,
                    profile_name=profile.username,
                    profile_url=profile_url,
                    limit_posts=options.profile_limit,
                ):
                    candidates = _iter_feed_item_media(item, options.include_profile_reels)
                    if not candidates:
                        continue

                    downloaded_any_for_post = False
                    for candidate in candidates:
                        _, downloaded_new_media = _download_http_asset(
                            session=feed_session,
                            asset_url=candidate.media_url,
                            directory=target_directory,
                            file_stem=candidate.file_stem,
                            media_kind=candidate.media_kind,
                        )
                        downloaded_any_for_post = downloaded_any_for_post or downloaded_new_media

                        if options.write_thumbnail and candidate.thumbnail_url:
                            _, downloaded_thumbnail = _download_http_asset(
                                session=feed_session,
                                asset_url=candidate.thumbnail_url,
                                directory=target_directory,
                                file_stem=f"{candidate.file_stem}_thumbnail",
                                media_kind="image",
                            )
                            downloaded_any_for_post = downloaded_any_for_post or downloaded_thumbnail

                    if options.write_caption:
                        caption_path = _write_caption_file(
                            directory=target_directory,
                            file_stem=candidates[0].file_stem.rsplit("_", 1)[0],
                            caption_text=candidates[0].caption_text,
                        )
                        downloaded_any_for_post = downloaded_any_for_post or caption_path is not None

                    if options.fast_update and not downloaded_any_for_post:
                        break
            except PrivateProfileNotFollowedException as exc:
                raise RuntimeError(
                    f"Profile `{profile.username}` la private hoac can dang nhap. Thu lai voi `--login <instagram_username>`."
                ) from exc
            except requests.HTTPError as exc:
                raise RuntimeError(f"Tai profile `{profile.username}` that bai: {exc}") from exc
            except RuntimeError:
                raise
            except (LoginException, ConnectionException, InstaloaderException) as exc:
                raise RuntimeError(f"Tai profile `{profile.username}` that bai: {exc}") from exc
            except Exception as exc:
                raise RuntimeError(
                    f"Tai profile `{profile.username}` that bai do Instagram tra ve du lieu khong day du hoac dang gioi han toc do: {exc}"
                ) from exc

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
