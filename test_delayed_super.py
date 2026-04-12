import flet as ft
class MyContainer(ft.Container):
    def __init__(self):
        content = ft.Text("Hello World!", size=40)
        super().__init__(expand=True, bgcolor=ft.Colors.YELLOW, content=content)

def main(page: ft.Page):
    mp = MyContainer()
    page.add(mp)
    page.update()
    import time; time.sleep(2)
