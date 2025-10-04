from pathlib import Path
import json

BASE_DIR = Path.home() / "Gitea Repos"
REPO_STORAGE = Path.home() / ".gitea_repos.json"

def load_repos():
    """Return list of repo dicts from .gitea_repos.json"""
    if REPO_STORAGE.exists():
        with open(REPO_STORAGE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def update_repo_json():
    """Update .gitea_repos.json with current folders in BASE_DIR"""
    BASE_DIR.mkdir(exist_ok=True)
    repos = [{"name": p.name} for p in BASE_DIR.iterdir() if p.is_dir()]
    with open(REPO_STORAGE, "w") as f:
        json.dump(repos, f, indent=2)

def repo_exists(repo_name):
    """Check if a repository already exists in BASE_DIR"""
    return (BASE_DIR / repo_name).exists()

def get_existing_repo_names():
    """Get list of existing repository names"""
    if not BASE_DIR.exists():
        return []
    return [p.name for p in BASE_DIR.iterdir() if p.is_dir()]

