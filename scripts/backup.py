"""Create and rotate FaceLens SQLite/FAISS backups."""

import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
BACKUPS_DIR = PROJECT_ROOT / "backups"
DB_PATH = DATA_DIR / "facelens.db"
INDEX_PATH = DATA_DIR / "facelens.index"
BACKUP_NAME_PATTERN = re.compile(r"^\d{8}_\d{6}$")
MAX_BACKUPS = 5


def _remove_backup_dir(path: Path) -> None:
    resolved = path.resolve()
    if resolved.parent != BACKUPS_DIR.resolve():
        raise RuntimeError(f"Refusing to remove path outside backups: {resolved}")
    shutil.rmtree(resolved)


def _prune_old_backups() -> list[Path]:
    backups = sorted(
        (
            path
            for path in BACKUPS_DIR.iterdir()
            if path.is_dir() and BACKUP_NAME_PATTERN.fullmatch(path.name)
        ),
        key=lambda path: path.name,
        reverse=True,
    )
    removed = []
    for old_backup in backups[MAX_BACKUPS:]:
        _remove_backup_dir(old_backup)
        removed.append(old_backup)
    return removed


def create_backup() -> Path:
    missing = [path for path in (DB_PATH, INDEX_PATH) if not path.is_file()]
    if missing:
        missing_text = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Missing backup source(s): {missing_text}")

    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    backup_dir = BACKUPS_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir.mkdir(exist_ok=False)

    try:
        with sqlite3.connect(DB_PATH) as source:
            with sqlite3.connect(backup_dir / DB_PATH.name) as destination:
                source.backup(destination)
        shutil.copy2(INDEX_PATH, backup_dir / INDEX_PATH.name)
    except Exception:
        _remove_backup_dir(backup_dir)
        raise

    total_bytes = sum(
        path.stat().st_size for path in backup_dir.iterdir() if path.is_file()
    )
    print(f"Backup created: {backup_dir}")
    print(f"Backup size: {total_bytes / (1024 * 1024):.3f} MiB ({total_bytes} bytes)")

    for removed in _prune_old_backups():
        print(f"Removed old backup: {removed}")

    return backup_dir


if __name__ == "__main__":
    create_backup()
