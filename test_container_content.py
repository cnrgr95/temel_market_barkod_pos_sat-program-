import flet as ft
class MyContainer(ft.Container):
    def __init__(self):
        super().__init__(expand=True)
        self.content = ft.Text("Hello")

mc = MyContainer()
print("Content is:", mc.content)
print("Children are:", mc.get_children())
