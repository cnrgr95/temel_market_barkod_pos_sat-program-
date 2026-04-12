import flet as ft
import time

class MyPage(ft.Container):
    def __init__(self):
        super().__init__(expand=True, bgcolor=ft.Colors.RED)
        self.content = ft.Text("Hello World!", size=40)

def main(page: ft.Page):
    mp = MyPage()
    page.add(mp)
    page.update()
    time.sleep(2)  # give it time
    print(f'MyPage children length: {len(mp.controls if hasattr(mp, "controls") else [])}')
    try:
        children = mp.get_children()
        print(f'MyPage get_children: {children}')
    except:
        pass

ft.app(target=main)
