"""
Flet uygulamaları için arka plan thread yardımcısı.
UI thread'ini bloke etmeden DB işlemlerini çalıştırır (Ajax mantığı).

Kullanım:
    run_bg(
        fn=lambda: db.search_products(...),
        on_done=lambda rows: apply_rows(rows),
    )
"""
import threading


def run_bg(fn, on_done=None, on_error=None):
    """
    fn'i daemon thread'de çalıştır.
    Sonuç on_done(result) ile UI thread'ine döner.
    Hata olursa on_error(exception) çağrılır.
    """
    def _worker():
        try:
            result = fn()
            if on_done:
                on_done(result)
        except Exception as exc:
            if on_error:
                on_error(exc)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t
