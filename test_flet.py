import os
import sys
sys.path.insert(0, os.path.abspath('.'))

import flet as ft
from flet_pos.app import FletMarketApp

def test_pos(page: ft.Page):
    try:
        app = FletMarketApp(page)
        app.current_user = {"role": "ADMIN", "id": 1, "username": "admin"}
        app._start_main_shell()
        print("Main shell built")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("ERRORED OUT!")
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)

ft.app(target=test_pos)
