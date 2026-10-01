"""Settings, backup, recovery, and data lifecycle module for AG Printers."""

from app.settings.backup_service import (
    check_and_run_auto_backup,
    clear_business_data,
    create_backup,
    restore_backup,
    validate_backup,
)
from app.settings.config import (
    get_backup_dir,
    is_auto_backup_enabled,
    load_settings,
    set_backup_dir,
)
from app.settings.page import SettingsPage

__all__ = [
    "SettingsPage",
    "create_backup",
    "restore_backup",
    "clear_business_data",
    "validate_backup",
    "check_and_run_auto_backup",
    "load_settings",
    "get_backup_dir",
    "set_backup_dir",
    "is_auto_backup_enabled",
]
