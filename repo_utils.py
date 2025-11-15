from pathlib import Path
import json
import re
from urllib.parse import urlparse

BASE_DIR = Path.home() / "Gitea Repos"
REPO_STORAGE = Path.home() / ".gitea_repos.json"
DEFAULT_SERVER_LABEL = "Unknown Server"

def _sanitize_folder_name(name: str) -> str:
    sanitized = re.sub(r"[\\/]+", "_", name.strip())
    sanitized = re.sub(r"\s+", "_", sanitized)
    return sanitized or "server"

def _extract_host(server_source: str | None) -> str | None:
    if not server_source:
        return None
    server_source = server_source.strip()
    # Handle full URLs (ssh:// or https://, etc.)
    if "://" in server_source:
        parsed = urlparse(server_source)
        return parsed.hostname
    # Handle scp-like ssh syntax git@host:owner/repo.git
    if "@" in server_source and ":" in server_source.split("@")[-1]:
        return server_source.split("@", 1)[1].split(":", 1)[0]
    # Handle git@host syntax without colon
    if "@" in server_source:
        return server_source.split("@", 1)[1]
    # Fallback: remove path portion if present
    if "/" in server_source:
        return server_source.split("/", 1)[0]
    return server_source or None

def derive_server_info(server_source: str | None):
    """
    Given a repository URL or server string, return a tuple of
    (server_label, server_folder). The label is used for UI, the folder
    name is used to build the filesystem path under BASE_DIR. For legacy
    repos without a known server this will fall back to DEFAULT_SERVER_LABEL
    and a None folder to keep the flat layout compatible.
    """
    host = _extract_host(server_source)
    if not host:
        return DEFAULT_SERVER_LABEL, None
    host = host.lower()
    return host, _sanitize_folder_name(host)

def build_repo_path(repo_name: str, server_folder: str | None):
    if server_folder:
        return BASE_DIR / server_folder / repo_name
    return BASE_DIR / repo_name

def _normalize_repo_entry(entry):
    if isinstance(entry, str):
        entry = {"name": entry}
    name = entry.get("name")
    if not name:
        return None
    server = entry.get("server") or DEFAULT_SERVER_LABEL
    server_folder = entry.get("server_folder")
    path = entry.get("path")
    if not path:
        path = str(build_repo_path(name, server_folder))
    return {
        "name": name,
        "server": server,
        "server_folder": server_folder,
        "path": path
    }

def load_repos():
    """Return list of repo dicts from .gitea_repos.json"""
    if not REPO_STORAGE.exists():
        return []
    try:
        with open(REPO_STORAGE, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    normalized = []
    if isinstance(data, list):
        for entry in data:
            normalized_entry = _normalize_repo_entry(entry)
            if normalized_entry:
                normalized.append(normalized_entry)
    return normalized

def update_repo_json():
    """Scan BASE_DIR and write repository metadata to .gitea_repos.json"""
    BASE_DIR.mkdir(exist_ok=True)
    repos: list[dict] = []

    for entry in sorted(BASE_DIR.iterdir()):
        if not entry.is_dir():
            continue

        repo_git = entry / ".git"
        if repo_git.exists():
            repos.append({
                "name": entry.name,
                "server": DEFAULT_SERVER_LABEL,
                "server_folder": None,
                "path": str(entry)
            })
            continue

        for repo_dir in sorted(entry.iterdir()):
            if not repo_dir.is_dir():
                continue
            if not (repo_dir / ".git").exists():
                continue
            repos.append({
                "name": repo_dir.name,
                "server": entry.name,
                "server_folder": entry.name,
                "path": str(repo_dir)
            })

    with open(REPO_STORAGE, "w") as f:
        json.dump(repos, f, indent=2)

def repo_exists(repo_name, server_folder=None):
    """Check if a repository already exists for a given server folder."""
    repo_path = build_repo_path(repo_name, server_folder)
    return repo_path.exists()

def get_existing_repo_names(server_folder=None):
    """Get list of repository names, optionally scoped to a server folder."""
    repos = load_repos()
    if server_folder is None:
        return [r["name"] for r in repos]
    return [r["name"] for r in repos if r.get("server_folder") == server_folder]

