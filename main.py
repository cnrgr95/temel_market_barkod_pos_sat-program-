import sys
import flet as ft
from flet_pos.app import main as flet_main

if __name__ == "__main__":
    try:
        ft.run(flet_main, port=0, view=ft.AppView.FLET_APP)
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        sys.exit(0)
