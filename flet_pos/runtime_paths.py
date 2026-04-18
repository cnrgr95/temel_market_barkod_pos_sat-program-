import os
import shutil
import sys
from dataclasses import dataclass

APP_DATA_DIR_NAME = "TemelMarket"


@dataclass(frozen=True)
class RuntimePaths:
    install_dir: str
    data_dir: str
    db_path: str
    media_dir: str
    backup_dir: str
    barcode_dir: str
    startup_log_path: str
    asset_dirs: tuple[str, ...]


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_install_dir() -> str:
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return _project_root()


def get_data_dir() -> str:
    if not is_frozen():
        return get_install_dir()

    local_appdata = (os.environ.get("LOCALAPPDATA") or "").strip()
    if local_appdata:
        return os.path.join(local_appdata, APP_DATA_DIR_NAME)

    roaming_appdata = (os.environ.get("APPDATA") or "").strip()
    if roaming_appdata:
        appdata_root = os.path.dirname(roaming_appdata)
        if appdata_root:
            return os.path.join(appdata_root, "Local", APP_DATA_DIR_NAME)

    return os.path.join(os.path.expanduser("~"), f".{APP_DATA_DIR_NAME.lower()}")


def _copy_file_if_missing(src_path: str, dst_path: str) -> bool:
    if not os.path.isfile(src_path) or os.path.exists(dst_path):
        return False
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    shutil.copy2(src_path, dst_path)
    return True


def _merge_tree_missing_files(src_dir: str, dst_dir: str) -> None:
    if not os.path.isdir(src_dir):
        return

    for root, dirs, files in os.walk(src_dir):
        rel_path = os.path.relpath(root, src_dir)
        target_root = dst_dir if rel_path == "." else os.path.join(dst_dir, rel_path)
        os.makedirs(target_root, exist_ok=True)

        for directory in dirs:
            os.makedirs(os.path.join(target_root, directory), exist_ok=True)

        for file_name in files:
            src_file = os.path.join(root, file_name)
            dst_file = os.path.join(target_root, file_name)
            if not os.path.exists(dst_file):
                shutil.copy2(src_file, dst_file)


def migrate_legacy_runtime_data(install_dir: str, data_dir: str) -> None:
    if not is_frozen():
        return
    if os.path.abspath(install_dir) == os.path.abspath(data_dir):
        return

    os.makedirs(data_dir, exist_ok=True)

    copied_main_db = _copy_file_if_missing(
        os.path.join(install_dir, "market.db"),
        os.path.join(data_dir, "market.db"),
    )
    if copied_main_db:
        for suffix in ("-wal", "-shm"):
            _copy_file_if_missing(
                os.path.join(install_dir, f"market.db{suffix}"),
                os.path.join(data_dir, f"market.db{suffix}"),
            )

    for folder_name in ("product_images", "backups", "barcode_labels"):
        _merge_tree_missing_files(
            os.path.join(install_dir, folder_name),
            os.path.join(data_dir, folder_name),
        )

    _copy_file_if_missing(
        os.path.join(install_dir, "startup_error.log"),
        os.path.join(data_dir, "startup_error.log"),
    )


def _get_asset_dirs(install_dir: str) -> tuple[str, ...]:
    dirs: list[str] = []
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            dirs.append(os.path.join(meipass, "assets"))
        dirs.append(os.path.join(install_dir, "_internal", "assets"))
    dirs.append(os.path.join(install_dir, "assets"))

    result: list[str] = []
    for path in dirs:
        normalized = os.path.abspath(path)
        if normalized not in result:
            result.append(normalized)
    return tuple(result)


def get_runtime_paths() -> RuntimePaths:
    install_dir = get_install_dir()
    data_dir = get_data_dir()
    migrate_legacy_runtime_data(install_dir, data_dir)

    media_dir = os.path.join(data_dir, "product_images")
    backup_dir = os.path.join(data_dir, "backups")
    barcode_dir = os.path.join(data_dir, "barcode_labels")

    for path in (data_dir, media_dir, backup_dir, barcode_dir):
        os.makedirs(path, exist_ok=True)

    return RuntimePaths(
        install_dir=install_dir,
        data_dir=data_dir,
        db_path=os.path.join(data_dir, "market.db"),
        media_dir=media_dir,
        backup_dir=backup_dir,
        barcode_dir=barcode_dir,
        startup_log_path=os.path.join(data_dir, "startup_error.log"),
        asset_dirs=_get_asset_dirs(install_dir),
    )
