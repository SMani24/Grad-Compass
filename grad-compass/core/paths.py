"""Explicit runtime storage for isolated development; legacy desktop defaults remain."""
import os
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
LEGACY_DATA_DIR = APP_ROOT / "data"
LEGACY_DB_PATH = LEGACY_DATA_DIR / "grad_compass.db"

def validate_data_directory(path):
    directory_path = Path(path).expanduser().resolve()
    protected = (
        LEGACY_DATA_DIR,
        APP_ROOT / "ui" / "cache",
        APP_ROOT.parent / "grad-compass-research-engine",
        APP_ROOT.parent / "grad-compass-exchange",
    )
    for directory in protected:
        directory = directory.resolve()
        if directory_path.is_relative_to(directory) or directory.is_relative_to(directory_path):
            raise ValueError("Development storage must be separate from production and research storage")
    return directory_path


_configured = os.environ.get("GRAD_COMPASS_DATA_DIR", "").strip()
ISOLATED_RUNTIME = bool(_configured)
DATA_DIR = validate_data_directory(_configured) if _configured else LEGACY_DATA_DIR

DB_PATH = DATA_DIR / "grad_compass.db"
CONFIG_PATH = DATA_DIR / "config.json"
VAULT_DIR = DATA_DIR / "vault"
CACHE_DIR = (DATA_DIR / "cache" / "images") if ISOLATED_RUNTIME else APP_ROOT / "ui" / "cache" / "images"
FILE_ROOT = DATA_DIR if ISOLATED_RUNTIME else APP_ROOT
OFFLINE = os.environ.get("GRAD_COMPASS_OFFLINE", "").strip().lower() in {"1", "true", "yes"}


def validate_runtime_path(path):
    path = Path(path)
    if ISOLATED_RUNTIME:
        if not path.resolve().is_relative_to(DATA_DIR):
            raise ValueError("Path is outside development storage")
        if any(part.is_symlink() for part in (path, *path.parents) if part.is_relative_to(DATA_DIR)):
            raise ValueError("Linked development storage paths are not supported")
        if path.is_file() and path.stat().st_nlink > 1:
            raise ValueError("Hard-linked development files are not supported")
    return path


def validate_database_path(path):
    """Reject development-path substitutions before sqlite can create/open a file."""
    path = validate_runtime_path(path)
    if ISOLATED_RUNTIME:
        if not path.resolve().is_relative_to(DATA_DIR) or path.is_symlink():
            raise ValueError("Database is outside development storage")
        if path.exists() and LEGACY_DB_PATH.exists() and os.path.samefile(path, LEGACY_DB_PATH):
            raise ValueError("Development database aliases the production database")
    return path


def cached_image_url(path):
    path = Path(path)
    return path.as_uri() if ISOLATED_RUNTIME else "cache/images/" + path.name
