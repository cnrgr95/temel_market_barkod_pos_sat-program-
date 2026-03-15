import flet as ft


class HardwarePage(ft.Container):
    def __init__(self):
        super().__init__(expand=True)
        self.content = ft.Column(
            expand=True,
            controls=[
                ft.Text("Donanim Entegrasyonu", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("Bu cihazlari etkinlestirip test edebilirsiniz:"),
                ft.Switch(label="Barkod okuyucu", value=True),
                ft.Switch(label="Fis yazici", value=False),
                ft.Switch(label="Para cekmecesi", value=False),
                ft.Switch(label="Terazi", value=False),
                ft.Switch(label="Dokunmatik ekran modu", value=True),
                ft.Text("Not: Gercek surucu/port baglantilari bir sonraki asamada eklenecek.", color=ft.Colors.BLUE_GREY_700),
            ],
        )
