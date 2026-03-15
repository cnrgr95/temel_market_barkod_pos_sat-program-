import flet as ft


def section_page(title: str, bullets: list[str]) -> ft.Container:
    return ft.Container(
        expand=True,
        padding=ft.padding.all(12),
        content=ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Text(title, size=24, weight=ft.FontWeight.BOLD),
                ft.Text("Bu modul canli gelistirme asamasinda, temel ekran hazirlandi.", color=ft.Colors.BLUE_GREY_600),
                ft.Card(
                    content=ft.Container(
                        padding=16,
                        content=ft.Column(
                            spacing=8,
                            controls=[ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN), ft.Text(item)]) for item in bullets],
                        ),
                    )
                ),
            ],
        ),
    )
