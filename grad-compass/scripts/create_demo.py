"""Create an invented, offline desktop workspace at an explicit empty location."""
import argparse
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="new or empty synthetic runtime directory")
    args = parser.parse_args()
    raw = args.directory.expanduser()
    if raw.is_symlink() or (raw.exists() and (not raw.is_dir() or any(raw.iterdir()))):
        parser.error("Use a new or empty directory; existing data will not be replaced")
    root = raw.resolve()
    os.environ["GRAD_COMPASS_DATA_DIR"] = str(root)
    os.environ["GRAD_COMPASS_OFFLINE"] = "1"
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    # Import validates storage boundaries before creating anything.
    from core.paths import DATA_DIR
    from core import database as db

    DATA_DIR.mkdir(parents=True, mode=0o700, exist_ok=True)
    db.init_db()
    from contextlib import closing
    with closing(db._connect()) as connection, connection:
        connection.execute("CREATE TABLE app_synthetic_demo_guard(marker TEXT NOT NULL)")
        connection.execute("INSERT INTO app_synthetic_demo_guard VALUES('grad-compass-app-demo-v1')")
    first = db.db_add_university("CAN", "Northbridge Example University", "Example City", 43.65, -79.38, "2027-01-15", "https://example.invalid/northbridge")
    second = db.db_add_university("DEU", "Rivergate Example Institute", "Example City", 52.52, 13.40, "2027-02-01", "https://example.invalid/rivergate")
    db.db_add_university("CAN", "Unlocated Example University", "Unknown", None, None, "", "")
    db.db_update_university_status(second, "Applying")
    prof = db.db_add_professor(first, "Dr. Example Researcher", "researcher@example.invalid", "Invented research focus", "Cold Emailed")
    db.db_add_task("Review the example program", "2027-01-10", uni_id=first)
    db.db_add_task("Prepare an example follow-up", "2027-01-12", prof_id=prof)
    print("Created synthetic offline workspace:", DATA_DIR)
    print("Use GRAD_COMPASS_DATA_DIR with this directory and GRAD_COMPASS_OFFLINE=1 to preview.")


if __name__ == "__main__":
    main()
