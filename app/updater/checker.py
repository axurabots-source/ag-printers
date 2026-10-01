"""GitHub Releases update checker for AG Printers."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from PySide6.QtCore import QThread, Signal

from app import __version__

GITHUB_REPO = "axurabots-source/ag-printers"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


@dataclass
class UpdateInfo:
    """Information about a newly available release."""

    version: str
    name: str
    notes: str
    download_url: str
    html_url: str
    published_at: str


def parse_version(v_str: str) -> tuple[int, ...]:
    """Parse version string like 'v1.2.3' or '1.0' into a tuple of ints."""
    clean = re.sub(r"^[^\d]*", "", str(v_str).strip())
    parts = []
    for p in clean.split("."):
        num_match = re.match(r"^\d+", p)
        if num_match:
            parts.append(int(num_match.group(0)))
        else:
            break
    return tuple(parts) if parts else (0,)


def check_github_update(repo: str = GITHUB_REPO) -> UpdateInfo | None:
    """Check GitHub Releases API for a newer version than current __version__."""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AG-Printers-Desktop-App",
            "Accept": "application/vnd.github.v3+json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status != 200:
                return None
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as http_err:
        # 404 means no releases published yet for the repo
        if http_err.code == 404:
            return None
        return None
    except Exception:
        return None

    remote_tag = data.get("tag_name", "").strip()
    if not remote_tag:
        return None

    remote_ver = parse_version(remote_tag)
    current_ver = parse_version(__version__)

    # Check if remote version is strictly newer
    if remote_ver <= current_ver:
        return None

    # Find download url: prefer a attached .zip asset, fallback to zipball_url
    download_url = data.get("zipball_url", "")
    assets = data.get("assets", [])
    for a in assets:
        name = a.get("name", "").lower()
        if name.endswith(".zip"):
            download_url = a.get("browser_download_url", download_url)
            break

    return UpdateInfo(
        version=remote_tag,
        name=data.get("name", remote_tag),
        notes=data.get("body", "No release notes provided.").strip(),
        download_url=download_url,
        html_url=data.get("html_url", f"https://github.com/{repo}/releases"),
        published_at=data.get("published_at", ""),
    )


class UpdateCheckerThread(QThread):
    """Asynchronous background worker to check for GitHub releases without freezing UI."""

    update_available = Signal(object)  # Emits UpdateInfo
    up_to_date = Signal()
    check_failed = Signal(str)

    def __init__(self, repo: str = GITHUB_REPO, parent=None) -> None:
        super().__init__(parent)
        self._repo = repo

    def run(self) -> None:
        try:
            info = check_github_update(self._repo)
            if info is not None:
                self.update_available.emit(info)
            else:
                self.up_to_date.emit()
        except Exception as exc:
            self.check_failed.emit(str(exc))
