from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from typing import Any


CONFIG_FILENAME = "config.json"


@dataclass(slots=True)
class AppConfig:
    output_dir: str | None = None
    filename_template: str | None = None
    profile_template: str | None = None
    cookies_file: str | None = None
    login_user: str | None = None
    session_file: str | None = None
    write_caption: bool | None = None
    write_thumbnail: bool | None = None
    max_posts: int | None = None
    no_reels: bool | None = None
    reels_only: bool | None = None
    no_profile_pic: bool | None = None
    fast_update: bool | None = None
    verbose: bool | None = None


def default_config_path() -> Path:
    base_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".config"))
    return (base_dir / "instadow" / CONFIG_FILENAME).resolve()


def _normalize_config_value(key: str, value: Any) -> Any:
    if value is None:
        return None

    if key in {"write_caption", "write_thumbnail", "no_reels", "reels_only", "no_profile_pic", "fast_update", "verbose"}:
        if isinstance(value, bool):
            return value
        return None

    if key == "max_posts":
        if isinstance(value, int) and value > 0:
            return value
        return None

    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    return None


def load_config(path: Path) -> AppConfig:
    if not path.is_file():
        return AppConfig()

    try:
        raw_payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AppConfig()

    if not isinstance(raw_payload, dict):
        return AppConfig()

    values: dict[str, Any] = {}
    for field_name in AppConfig.__dataclass_fields__:
        values[field_name] = _normalize_config_value(field_name, raw_payload.get(field_name))

    return AppConfig(**values)


def config_to_dict(config: AppConfig) -> dict[str, Any]:
    return {key: value for key, value in asdict(config).items() if value is not None}


def save_config(path: Path, config: AppConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = config_to_dict(config)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def delete_config(path: Path) -> bool:
    if not path.exists():
        return False
    path.unlink()
    return True
