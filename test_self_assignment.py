import flet as ft
class MyContainer(ft.Container):
    def __init__(self):
        self.txt = ft.Text("Test")
        super().__init__(expand=True, content=self.txt)

mc = MyContainer()
print("Success:", mc.content.value)
