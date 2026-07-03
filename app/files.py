from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil


class FileManager:
    def __init__(self, failed_dir: Path) -> None:
        self.failed_dir = failed_dir
        self.failed_dir.mkdir(parents=True, exist_ok=True)

    def delete_file(self, path: Path) -> None:
        if path.exists():
            path.unlink()

    def move_to_failed(self, path: Path) -> Path:
        self.failed_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = self.failed_dir / f"{timestamp}-{path.name}"
        shutil.move(str(path), str(destination))
        return destination
