import os
import sys
import shutil
import subprocess
from pathlib import Path

VAULT_DIR = Path(__file__).resolve().parent.parent / "data" / "vault"

def store_file(source_path: str, parent_type: str, parent_id: str) -> dict:
    source = Path(source_path)
    if not source.exists():
        return None

    target_dir = VAULT_DIR / parent_type / str(parent_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / source.name

    shutil.copy2(source, target_path)

    # Return relative path for database storage
    app_root = VAULT_DIR.parent.parent
    rel_path = target_path.relative_to(app_root)
    return {
        "file_name": source.name,
        "stored_path": str(rel_path)
    }

def open_system_file(relative_path: str) -> bool:
    app_root = Path(__file__).resolve().parent.parent
    full_path = (app_root / relative_path).resolve()

    if not full_path.exists():
        print(f"[Vault Error] Missing file: {full_path}")
        return False

    target = str(full_path)
    try:
        if sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", target])
        elif sys.platform.startswith("win"):
            os.startfile(target)
        elif sys.platform.startswith("darwin"):
            subprocess.run(["open", target])
        return True
    except Exception as e:
        print(f"[Vault Error] Failed to launch file: {e}")
        return False