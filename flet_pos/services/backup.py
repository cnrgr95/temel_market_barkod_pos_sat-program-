import os
import shutil
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BackupResult:
    local_path: str
    drive_path: str = ""
    error: str = ""


class BackupManager:
    def __init__(
        self,
        *,
        base_dir: str,
        db_path: str,
        backup_dir: str,
        interval_seconds: int = 7200,
        google_drive_dir: str = "",
    ) -> None:
        self.base_dir = base_dir
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.interval_seconds = max(300, int(interval_seconds or 7200))
        self.google_drive_dir = google_drive_dir or self.detect_google_drive_dir()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        os.makedirs(self.backup_dir, exist_ok=True)

    def detect_google_drive_dir(self) -> str:
        env_dir = os.environ.get("GOOGLE_DRIVE_BACKUP_DIR", "").strip()
        if env_dir and os.path.isdir(env_dir):
            return env_dir

        user_profile = os.environ.get("USERPROFILE", "")
        candidates = [
            os.path.join(user_profile, "Google Drive"),
            os.path.join(user_profile, "My Drive"),
            os.path.join(user_profile, "GoogleDrive"),
            os.path.join(user_profile, "Drive", "My Drive"),
            "G:\\My Drive",
            "G:\\Google Drive",
        ]
        for path in candidates:
            if path and os.path.isdir(path):
                return path
        return ""

    def google_backup_dir(self) -> str:
        if not self.google_drive_dir:
            return ""
        return os.path.join(self.google_drive_dir, "TemelMarketYedek")

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            try:
                self.backup_now(prefix="auto")
            except Exception:
                pass

    def _sqlite_backup_copy(self, src_path: str, dst_path: str) -> None:
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        src = sqlite3.connect(src_path, timeout=15)
        dst = sqlite3.connect(dst_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

    def backup_now(self, prefix: str = "manual") -> BackupResult:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"market_{prefix}_{stamp}.db"
        local_path = os.path.join(self.backup_dir, name)
        self._sqlite_backup_copy(self.db_path, local_path)

        drive_path = ""
        if self.google_drive_dir:
            try:
                drive_dir = self.google_backup_dir()
                os.makedirs(drive_dir, exist_ok=True)
                drive_path = os.path.join(drive_dir, name)
                last_error = None
                for _ in range(3):
                    try:
                        shutil.copy2(local_path, drive_path)
                        last_error = None
                        break
                    except OSError as ex:
                        last_error = ex
                        time.sleep(0.1)
                        os.makedirs(drive_dir, exist_ok=True)
                if last_error:
                    raise last_error
            except Exception as ex:
                return BackupResult(local_path=local_path, error=f"Google Drive kopyasi alinamadi: {ex}")

        return BackupResult(local_path=local_path, drive_path=drive_path)
