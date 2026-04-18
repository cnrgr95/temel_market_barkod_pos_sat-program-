import os
import subprocess
import sys
import traceback

import flet as ft

from flet_pos.app import main as flet_main
from flet_pos.runtime_paths import get_runtime_paths


_WEBVIEW2_CLIENT_ID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"


def _message_box(title: str, message: str, flags: int) -> int:
    try:
        import ctypes

        return int(ctypes.windll.user32.MessageBoxW(None, message, title, flags))
    except Exception:
        return 0


def _show_error_messagebox(title: str, message: str) -> None:
    _message_box(title, message, 0x10)


def _ask_yes_no(title: str, message: str) -> bool:
    return _message_box(title, message, 0x24) == 6


def _write_startup_error_log(err_text: str) -> str:
    log_path = get_runtime_paths().startup_log_path
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("\n" + "=" * 70 + "\n")
        f.write(err_text)
        f.write("\n")
    return log_path


def _is_webview2_installed() -> bool:
    if os.name != "nt":
        return True

    try:
        import winreg
    except Exception:
        return True

    access_modes = [winreg.KEY_READ]
    wow64_64 = getattr(winreg, "KEY_WOW64_64KEY", 0)
    wow64_32 = getattr(winreg, "KEY_WOW64_32KEY", 0)
    if wow64_64:
        access_modes.append(winreg.KEY_READ | wow64_64)
    if wow64_32:
        access_modes.append(winreg.KEY_READ | wow64_32)

    key_paths = [
        rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{_WEBVIEW2_CLIENT_ID}",
        rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{_WEBVIEW2_CLIENT_ID}",
    ]
    hives = [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]

    for hive in hives:
        for key_path in key_paths:
            for access in access_modes:
                try:
                    with winreg.OpenKey(hive, key_path, 0, access) as key:
                        version, _ = winreg.QueryValueEx(key, "pv")
                        if str(version).strip():
                            return True
                except OSError:
                    continue
    return False


def _find_webview2_installer_script() -> str:
    runtime_paths = get_runtime_paths()
    candidates = [
        os.path.join(runtime_paths.install_dir, "install_webview2.ps1"),
        os.path.join(runtime_paths.install_dir, "_internal", "install_webview2.ps1"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "install_webview2.ps1"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "installer", "install_webview2.ps1"),
    ]

    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        candidates.append(os.path.join(meipass, "install_webview2.ps1"))

    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return ""


def _run_webview2_installer(script_path: str) -> bool:
    if not script_path:
        return False

    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        script_path,
    ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        completed = subprocess.run(
            command,
            check=False,
            creationflags=creationflags,
        )
    except Exception:
        return False

    return completed.returncode == 0 and _is_webview2_installed()


def _configure_embedded_flet_view_path() -> None:
    if os.environ.get("FLET_VIEW_PATH"):
        return

    runtime_paths = get_runtime_paths()
    candidates = [
        os.path.join(runtime_paths.install_dir, "_internal", "flet_desktop", "app", "flet"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "_internal", "flet_desktop", "app", "flet"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "flet_desktop", "app", "flet"),
    ]

    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        candidates.insert(0, os.path.join(meipass, "flet_desktop", "app", "flet"))

    for candidate in candidates:
        exe_path = os.path.join(candidate, "flet.exe")
        if candidate and os.path.isfile(exe_path):
            os.environ["FLET_VIEW_PATH"] = candidate
            return


def _ensure_webview2_runtime() -> bool:
    if _is_webview2_installed():
        return True

    script_path = _find_webview2_installer_script()
    if script_path and _ask_yes_no(
        "Temel Market Gereksinimi",
        "Microsoft Edge WebView2 Runtime bulunamadi.\n\n"
        "Bu bilesen olmadan uygulama acilamaz.\n\n"
        "Simdi otomatik kurulumu baslatmak ister misiniz?",
    ):
        if _run_webview2_installer(script_path):
            return True

    extra_note = (
        f"Kurulum yardimci dosyasi:\n{script_path}"
        if script_path
        else "Kurulum yardimci dosyasi bulunamadi."
    )
    _show_error_messagebox(
        "WebView2 Eksik",
        "Microsoft Edge WebView2 Runtime kurulmadan uygulama baslatilamaz.\n\n"
        "Lutfen internet baglantisi olan bir ortamda kurulumu tamamlayin.\n\n"
        f"{extra_note}",
    )
    return False


if __name__ == "__main__":
    exit_code = 0

    try:
        _configure_embedded_flet_view_path()
        if not _ensure_webview2_runtime():
            raise SystemExit(1)
        ft.run(flet_main, port=0, view=ft.AppView.FLET_APP)
    except SystemExit as exc:
        exit_code = int(exc.code or 0)
    except Exception:
        exit_code = 1
        details = traceback.format_exc()
        log_file = _write_startup_error_log(details)
        _show_error_messagebox(
            "Temel Market Baslatma Hatasi",
            "Uygulama baslatilirken bir hata olustu.\n\n"
            f"Hata gunlugu:\n{log_file}",
        )

    raise SystemExit(exit_code)
