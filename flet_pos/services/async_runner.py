"""
Flet uygulamalari icin arka plan thread yardimcisi.
UI thread'ini bloke etmeden isleri calistirir.
"""

import inspect
import threading


def _resolve_ui_page(ui_host):
    if ui_host is None:
        return None
    if hasattr(ui_host, "run_task") and hasattr(ui_host, "update"):
        return ui_host
    return getattr(ui_host, "page", None)


def _dispatch_ui_callback(ui_host, callback, *args):
    if callback is None:
        return

    page = _resolve_ui_page(ui_host)
    if page is None:
        callback(*args)
        return

    async def _runner():
        result = callback(*args)
        if inspect.isawaitable(result):
            await result

    try:
        page.run_task(_runner)
    except Exception:
        callback(*args)


def run_bg(fn, on_done=None, on_error=None, ui_host=None):
    """
    fn'i daemon thread'de calistir.
    Sonucu varsa on_done(result) ile UI thread'ine dondur.
    Hata olursa on_error(exception) cagrilir.
    """

    def _worker():
        try:
            result = fn()
            if on_done:
                _dispatch_ui_callback(ui_host, on_done, result)
        except Exception as exc:
            if on_error:
                _dispatch_ui_callback(ui_host, on_error, exc)

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()
    return worker
