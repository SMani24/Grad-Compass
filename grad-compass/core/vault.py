import os
import sys
import shutil
import subprocess
import uuid
from pathlib import Path
from core.paths import VAULT_DIR, FILE_ROOT, validate_runtime_path


def resolve_stored_file(relative_path: str) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Invalid vault path")
    candidate = validate_runtime_path(FILE_ROOT / relative)
    root = VAULT_DIR.resolve()
    if not candidate.resolve().is_relative_to(root) or candidate.resolve() == root:
        raise ValueError("File is outside the document vault")
    # Refuse linked files/directories even if their target is currently inside the vault.
    if VAULT_DIR.is_symlink() or any(part.is_symlink() for part in (candidate, *candidate.parents) if part != FILE_ROOT and part.is_relative_to(FILE_ROOT)):
        raise ValueError("Linked vault paths are not supported")
    return candidate


def delete_stored_file(relative_path: str) -> bool:
    try:
        target = resolve_stored_file(relative_path)
        if target.is_file():
            target.unlink()
        return True
    except (ValueError, OSError):
        # Retain files if cleanup cannot be performed safely; never expose private paths.
        return False

def store_file(source_path: str, parent_type: str, parent_id: str) -> dict:
    source = Path(source_path)
    if parent_type not in {"university", "professor"} or not str(parent_id).isdigit() or int(parent_id) < 1:
        raise ValueError("Invalid attachment parent")
    if not source.is_file():
        return None

    # Each attachment has its own directory, preserving the human-readable basename.
    target_dir = VAULT_DIR / parent_type / str(int(parent_id)) / uuid.uuid4().hex
    target_path = target_dir / source.name
    rel_path = target_path.relative_to(FILE_ROOT)
    resolve_stored_file(str(rel_path))
    target_dir.mkdir(parents=True, mode=0o700, exist_ok=False)
    try:
        descriptor = os.open(target_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as output, source.open("rb") as input_file:
            shutil.copyfileobj(input_file, output)
    except Exception:
        target_path.unlink(missing_ok=True)
        target_dir.rmdir()
        raise
    return {
        "file_name": source.name,
        "stored_path": str(rel_path)
    }

def open_system_file(relative_path: str) -> bool:
    try:
        full_path = resolve_stored_file(relative_path)
    except ValueError:
        return False
    if not full_path.is_file():
        return False

    target = str(full_path)
    try:
        if sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", target], check=True)
        elif sys.platform.startswith("win"):
            os.startfile(target)
        elif sys.platform.startswith("darwin"):
            subprocess.run(["open", target], check=True)
        else:
            return False
        return True
    except Exception:
        print("[Vault Error] Failed to launch file")
        return False
