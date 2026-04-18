import os
import shutil
import sqlite3
import threading
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BackupResult:
    local_path: str = ""
    drive_path: str = ""
    error: str = ""
    target_mode: str = "BOTH"
    created_at: str = ""


class BackupManager:
    def __init__(
        self,
        *,
        base_dir: str,
        db_path: str,
        backup_dir: str,
        interval_seconds: int = 7200,
        google_drive_dir: str = "",
        target_mode: str = "BOTH",
    ) -> None:
        self.base_dir = base_dir
        self.db_path = db_path
        self.backup_dir = backup_dir or os.path.join(base_dir, "backups")
        self.interval_seconds = max(300, int(interval_seconds or 7200))
        self.google_drive_dir = google_drive_dir or self.detect_google_drive_dir()
        self.target_mode = self._normalize_target_mode(target_mode)
        self.log_path = os.path.join(self.backup_dir, "backup_log.csv")
        self.last_result: BackupResult | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._next_backup_at = time.time() + self.interval_seconds
        os.makedirs(self.backup_dir, exist_ok=True)

    def _normalize_target_mode(self, value: str) -> str:
        mode = (value or "BOTH").strip().upper()
        if mode in {"LOCAL", "DRIVE", "BOTH"}:
            return mode
        return "BOTH"

    def set_interval_minutes(self, minutes: int) -> None:
        with self._lock:
            self.interval_seconds = max(300, int(minutes or 120) * 60)
            self._next_backup_at = time.time() + self.interval_seconds

    def set_target_mode(self, mode: str) -> None:
        with self._lock:
            self.target_mode = self._normalize_target_mode(mode)

    def set_backup_dir(self, backup_dir: str) -> None:
        path = (backup_dir or "").strip() or os.path.join(self.base_dir, "backups")
        os.makedirs(path, exist_ok=True)
        with self._lock:
            self.backup_dir = path
            self.log_path = os.path.join(path, "backup_log.csv")

    def seconds_until_next_backup(self) -> int:
        with self._lock:
            remaining = int(round(self._next_backup_at - time.time()))
        return max(0, remaining)

    def next_backup_label(self) -> str:
        seconds = self.seconds_until_next_backup()
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    @property
    def next_backup_time(self):
        """Return next backup time as a datetime object."""
        from datetime import datetime
        with self._lock:
            ts = self._next_backup_at
        return datetime.fromtimestamp(ts)

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
        self._stop.clear()
        with self._lock:
            self._next_backup_at = time.time() + self.interval_seconds
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _schedule_next_backup(self) -> None:
        with self._lock:
            self._next_backup_at = time.time() + self.interval_seconds

    def _run(self) -> None:
        while not self._stop.is_set():
            remaining = self.seconds_until_next_backup()
            if remaining > 0:
                self._stop.wait(min(1.0, remaining))
                continue
            try:
                self.backup_now(prefix="auto")
            except Exception as ex:
                self._write_log("ERROR", f"auto:{self.target_mode.lower()}", "", "", str(ex))
            finally:
                self._schedule_next_backup()

    def _write_log(self, status: str, prefix: str, local_path: str, drive_path: str, message: str = "") -> None:
        os.makedirs(self.backup_dir, exist_ok=True)
        is_new = not os.path.exists(self.log_path)
        with open(self.log_path, "a", encoding="utf-8") as f:
            if is_new:
                f.write("time,status,type,local_path,drive_path,message\n")
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            def clean(v):
                return str(v or "").replace("\n", " ").replace(",", ";")

            f.write(
                f"{stamp},{clean(status)},{clean(prefix)},{clean(local_path)},"
                f"{clean(drive_path)},{clean(message)}\n"
            )

    def list_logs(self, limit: int = 50) -> list[tuple[str, str, str, str, str, str]]:
        if not os.path.exists(self.log_path):
            return []
        with open(self.log_path, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\n") for line in f.readlines()[1:] if line.strip()]
        rows = []
        for line in lines[-limit:]:
            parts = line.split(",", 5)
            if len(parts) < 6:
                parts += [""] * (6 - len(parts))
            rows.append(tuple(parts[:6]))
        return list(reversed(rows))

    def _sqlite_backup_copy(self, src_path: str, dst_path: str) -> None:
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        src = sqlite3.connect(src_path, timeout=15)
        dst = sqlite3.connect(dst_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

    def _copy_to_drive_with_retry(self, src_path: str, dst_path: str) -> None:
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        last_error = None
        for _ in range(3):
            try:
                shutil.copy2(src_path, dst_path)
                return
            except OSError as ex:
                last_error = ex
                time.sleep(0.1)
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        if last_error:
            raise last_error

    def create_zip_backup(self, prefix: str = "manual") -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_db_path = os.path.join(self.backup_dir, f"market_zip_{stamp}.db")
        zip_path = os.path.join(self.backup_dir, f"market_zip_{stamp}.zip")
        try:
            self._sqlite_backup_copy(self.db_path, temp_db_path)
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(temp_db_path, arcname="market.db")
            self._write_log("SUCCESS", f"{prefix}:zip", zip_path, "", "")
            return zip_path
        except Exception as ex:
            self._write_log("ERROR", f"{prefix}:zip", zip_path, "", str(ex))
            raise
        finally:
            try:
                if os.path.exists(temp_db_path):
                    os.remove(temp_db_path)
            except OSError:
                pass

    def backup_now(self, prefix: str = "manual", target_mode: str | None = None) -> BackupResult:
        target = self._normalize_target_mode(target_mode or self.target_mode)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        name = f"market_{prefix}_{stamp}.db"
        local_path = ""
        drive_path = ""

        try:
            if target in {"LOCAL", "BOTH"}:
                local_path = os.path.join(self.backup_dir, name)
                self._sqlite_backup_copy(self.db_path, local_path)

            if target in {"DRIVE", "BOTH"}:
                drive_dir = self.google_backup_dir()
                if not drive_dir:
                    raise ValueError("Google Drive klasoru ayarlanamadi")
                drive_path = os.path.join(drive_dir, name)
                if local_path and target == "BOTH":
                    self._copy_to_drive_with_retry(local_path, drive_path)
                else:
                    self._sqlite_backup_copy(self.db_path, drive_path)
        except Exception as ex:
            result = BackupResult(
                local_path=local_path,
                drive_path=drive_path,
                error=str(ex),
                target_mode=target,
                created_at=created_at,
            )
            self.last_result = result
            self._write_log("ERROR", f"{prefix}:{target.lower()}", local_path, drive_path, result.error)
            raise

        result = BackupResult(
            local_path=local_path,
            drive_path=drive_path,
            target_mode=target,
            created_at=created_at,
        )
        self.last_result = result
        self._write_log("SUCCESS", f"{prefix}:{target.lower()}", local_path, drive_path, "")
        return result
