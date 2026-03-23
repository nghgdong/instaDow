from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class DownloadOptions:
    output_dir: Path
    filename_template: str | None = None
    cookies_file: Path | None = None
    write_caption: bool = False
    write_thumbnail: bool = False
    print_info: bool = False
    verbose: bool = False


@dataclass(slots=True)
class DownloadResult:
    downloaded_files: list[Path] = field(default_factory=list)
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


def download(urls: Iterable[str], options: DownloadOptions) -> DownloadResult:
    yt_dlp, DownloadError = _load_yt_dlp()

    url_list = list(urls)
    if options.cookies_file and not options.cookies_file.is_file():
        raise RuntimeError(f"Khong tim thay cookies file: {options.cookies_file}")

    if not options.print_info:
        options.output_dir.mkdir(parents=True, exist_ok=True)

    tracker = DownloadTracker()
    ydl_options = build_ydl_options(options, tracker)

    try:
        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            if options.print_info:
                inspected_items = 0
                for url in url_list:
                    info = ydl.extract_info(url, download=False)
                    print(json.dumps(ydl.sanitize_info(info), ensure_ascii=False, indent=2))
                    inspected_items += 1
                return DownloadResult(inspected_items=inspected_items)

            error_code = ydl.download(url_list)
            if error_code:
                raise RuntimeError(f"yt-dlp tra ve ma loi {error_code}.")
    except DownloadError as exc:
        raise RuntimeError(str(exc)) from exc

    return DownloadResult(downloaded_files=tracker.files)
