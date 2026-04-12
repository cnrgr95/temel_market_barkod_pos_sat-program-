import flet as ft
import time
import sys

class MyPage(ft.Container):
    def __init__(self):
        super().__init__(expand=True, bgcolor=ft.Colors.YELLOW)
        self.content = ft.Text("Hello World!", size=40)

def main(page: ft.Page):
    mp = MyPage()
    page.add(mp)
    page.update()
    
    # Intentionally let it run for 2 seconds to see if anything prints or fails
    time.sleep(2)
    print("FINISHED")
    sys.exit(0)

ft.app(target=main)
