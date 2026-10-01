"""Application settings configuration and persistent storage for AG Printers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.paths import DATA_DIR, ensure_data_dirs

SETTINGS_FILE = DATA_DIR / "app_settings.json"
DEFAULT_BACKUP_DIR = Path.home() / "Documents" / "AG Printers" / "Backups"


def _default_settings() -> dict[str, Any]:
    return {
        "backup_dir": str(DEFAULT_BACKUP_DIR),
        "auto_backup": True,
        "retention_count": 10,
        "last_backup_time": "",
        "last_backup_file": "",
    }


def load_settings() -> dict[str, Any]:
    """Read the JSON configuration file, falling back to sensible defaults."""
    ensure_data_dirs()
    if not SETTINGS_FILE.exists():
        settings = _default_settings()
        save_settings(settings)
        return settings

    try:
        content = SETTINGS_FILE.read_text(encoding="utf-8")
        data = json.loads(content)
        # Merge with defaults in case new keys were added
        defaults = _default_settings()
        for k, v in defaults.items():
            if k not in data:
                data[k] = v
        return data
    except Exception:
        return _default_settings()


def save_settings(settings: dict[str, Any]) -> None:
    """Save configuration dictionary to app_settings.json."""
    ensure_data_dirs()
    try:
        content = json.dumps(settings, indent=2, ensure_ascii=False)
        SETTINGS_FILE.write_text(content, encoding="utf-8")
    except Exception as exc:
        print(f"Error saving settings: {exc}")


def get_backup_dir() -> Path:
    """Return the designated backup directory path, ensuring it exists."""
    settings = load_settings()
    raw = settings.get("backup_dir") or str(DEFAULT_BACKUP_DIR)
    path = Path(raw).resolve()
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Fallback to local data folder if Windows Documents is restricted
        fallback = DATA_DIR / "backups"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
    return path


def set_backup_dir(path: Path | str) -> Path:
    """Update and persist the backup directory location."""
    p = Path(path).resolve()
    p.mkdir(parents=True, exist_ok=True)
    settings = load_settings()
    settings["backup_dir"] = str(p)
    save_settings(settings)
    return p


def is_auto_backup_enabled() -> bool:
    """Return whether automatic daily backups are enabled."""
    return bool(load_settings().get("auto_backup", True))


def set_auto_backup_enabled(enabled: bool) -> None:
    """Toggle the automatic daily backup preference."""
    settings = load_settings()
    settings["auto_backup"] = bool(enabled)
    save_settings(settings)


def get_retention_count() -> int:
    """Return the maximum number of automatic backups to retain (default 10)."""
    val = load_settings().get("retention_count", 10)
    try:
        return max(1, int(val))
    except (ValueError, TypeError):
        return 10


def set_retention_count(count: int) -> None:
    """Update the backup retention count."""
    settings = load_settings()
    settings["retention_count"] = max(1, int(count))
    save_settings(settings)


def get_last_backup_info() -> tuple[str, str]:
    """Return (last_backup_time, last_backup_file)."""
    settings = load_settings()
    return (
        str(settings.get("last_backup_time", "")),
        str(settings.get("last_backup_file", "")),
    )


def record_backup_success(filename: str, timestamp_str: str) -> None:
    """Record a successful backup timestamp and file name."""
    settings = load_settings()
    settings["last_backup_time"] = timestamp_str
    settings["last_backup_file"] = filename
    save_settings(settings)
