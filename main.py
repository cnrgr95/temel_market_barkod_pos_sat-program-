import os
import sys
import traceback
import flet as ft
from flet_pos.app import main as flet_main


def _runtime_base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _show_error_messagebox(title: str, message: str) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
    except Exception:
        pass


def _write_startup_error_log(err_text: str) -> str:
    base = _runtime_base_dir()
    log_path = os.path.join(base, "startup_error.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("\n" + "=" * 70 + "\n")
        f.write(err_text)
        f.write("\n")
    return log_path

if __name__ == "__main__":
    try:
        ft.run(flet_main, port=0, view=ft.AppView.FLET_APP)
    except Exception:
        details = traceback.format_exc()
        log_file = _write_startup_error_log(details)
        _show_error_messagebox(
            "Temel Market Baslatma Hatasi",
            "Uygulama baslatilirken bir hata olustu.\n\n"
            f"Hata gunlugu:\n{log_file}",
        )
        raise
    finally:
        exit_code = 1 if sys.exc_info()[0] else 0
        sys.exit(exit_code)
