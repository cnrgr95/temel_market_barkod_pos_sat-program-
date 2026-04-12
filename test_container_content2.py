import flet as ft
class MyContainer(ft.Container):
    def __init__(self):
        super().__init__(expand=True)
        self.content = ft.Text("Hello")

mc = MyContainer()
print("Children are:", mc._get_children())
