import os
import sqlite3
import threading
import time
from datetime import datetime


class BackupService:
    def __init__(self, db_path: str, backup_dir: str, interval_seconds: int = 300) -> None:
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.interval_seconds = interval_seconds
        os.makedirs(self.backup_dir, exist_ok=True)

    def start(self) -> None:
        worker = threading.Thread(target=self._run, daemon=True)
        worker.start()

    def set_interval(self, interval_seconds: int) -> None:
        if interval_seconds < 30:
            interval_seconds = 30
        self.interval_seconds = interval_seconds

    def _run(self) -> None:
        while True:
            time.sleep(self.interval_seconds)
            try:
                self.backup_now()
            except Exception:
                # Keep app running even if backup fails.
                pass

    def backup_now(self) -> None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = os.path.join(self.backup_dir, f"market_{stamp}.db")
        src = sqlite3.connect(self.db_path)
        dst = sqlite3.connect(target)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
