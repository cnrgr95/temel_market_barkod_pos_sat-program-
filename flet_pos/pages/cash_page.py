from datetime import date, timedelta
import flet as ft


class CashPage(ft.Container):
    def __init__(self, db):
        super().__init__(expand=True)
        self.db = db

        self.txt_cash_from = ft.TextField(
            label="Başlangıç", width=130,
            value=(date.today() - timedelta(days=30)).strftime("%Y-%m-%d"),
            hint_text="YYYY-AA-GG",
        )
        self.txt_cash_to = ft.TextField(
            label="Bitiş", width=130,
            value=date.today().strftime("%Y-%m-%d"),
            hint_text="YYYY-AA-GG",
        )

        self.dd_type = ft.Dropdown(
            label="Islem Tipi",
            value="IN",
            width=160,
            options=[
                ft.dropdown.Option("IN", "Giris (IN)"),
                ft.dropdown.Option("OUT", "Cikis (OUT)"),
            ],
        )
        self.txt_amount = ft.TextField(label="Tutar (TL)", value="0", width=140)
        self.txt_note = ft.TextField(label="Aciklama", expand=True)

        self.lbl_balance = ft.Text(
            "Kasa Bakiyesi: -.-- TL",
            size=18,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.GREEN_700,
        )

        self.table = ft.DataTable(
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            heading_row_color=ft.Colors.INDIGO_50,
            column_spacing=20,
            columns=[
                ft.DataColumn(ft.Text("Tarih/Saat", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Tip", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Tutar (TL)", weight=ft.FontWeight.W_600), numeric=True),
                ft.DataColumn(ft.Text("Not", weight=ft.FontWeight.W_600)),
            ],
            rows=[],
        )

        self.content = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=14,
            controls=[
                ft.Text("Kasa Yonetimi", size=26, weight=ft.FontWeight.BOLD),
                # Bakiye karti
                ft.Container(
                    bgcolor=ft.Colors.GREEN_50,
                    border_radius=12,
                    padding=ft.padding.symmetric(horizontal=20, vertical=14),
                    border=ft.border.all(2, ft.Colors.GREEN_200),
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, color=ft.Colors.GREEN_700, size=32),
                            self.lbl_balance,
                        ],
                        spacing=12,
                    ),
                ),
                # Yeni hareket formu
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    padding=14,
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "Yeni Kasa Hareketi",
                                size=15,
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.INDIGO_700,
                            ),
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Container(col={"sm": 6, "md": 2}, content=self.dd_type),
                                    ft.Container(col={"sm": 6, "md": 2}, content=self.txt_amount),
                                    ft.Container(col={"sm": 12, "md": 6}, content=self.txt_note),
                                    ft.Container(
                                        col={"sm": 12, "md": 2},
                                        content=ft.ElevatedButton(
                                            "Kaydet",
                                            icon=ft.Icons.SAVE,
                                            on_click=self._save,
                                        ),
                                    ),
                                ]
                            ),
                        ],
                        spacing=10,
                    ),
                ),
                # Hareket listesi — tarih filtresi
                ft.Row([
                    ft.Text("Kasa Hareketleri", size=15,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.BLUE_GREY_700),
                    self.txt_cash_from,
                    ft.Text("—", size=13),
                    self.txt_cash_to,
                    ft.ElevatedButton(
                        "Filtrele", icon=ft.Icons.FILTER_ALT,
                        style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_600,
                                             color=ft.Colors.WHITE),
                        height=38,
                        on_click=lambda _: self._refresh_moves(),
                    ),
                ], spacing=8, wrap=True),
                ft.Container(
                    content=ft.Column([self.table], scroll=ft.ScrollMode.AUTO),
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    padding=10,
                ),
            ],
        )
        self.refresh()

    # ── Yardimci ─────────────────────────────────────────────────────────────

    def _safe_update(self):
        try:
            _ = self.page
            self.update()
        except RuntimeError:
            pass

    def _snack(self, text: str):
        try:
            self.page.snack_bar = ft.SnackBar(ft.Text(text), open=True)
            self.page.update()
        except RuntimeError:
            pass

    def _to_float(self, value: str) -> float:
        try:
            return float((value or "").replace(",", "."))
        except ValueError:
            return 0.0

    # ── Islemler ─────────────────────────────────────────────────────────────

    def _save(self, _e: ft.ControlEvent):
        amt = self._to_float(self.txt_amount.value)
        if amt <= 0:
            self._snack("Gecerli bir tutar giriniz")
            return
        self.db.add_cash_move(
            self.dd_type.value or "IN",
            amt,
            (self.txt_note.value or "").strip(),
        )
        self.txt_amount.value = "0"
        self.txt_note.value = ""
        self.refresh()
        self._safe_update()

    def _refresh_moves(self):
        date_from = (self.txt_cash_from.value or "").strip()
        date_to = (self.txt_cash_to.value or "").strip()
        try:
            rows = self.db.list_cash_moves(date_from=date_from, date_to=date_to)
        except TypeError:
            rows = self.db.list_cash_moves()
        self.table.rows = []
        for r in rows:
            move_type = r[1] or ""
            amt = float(r[2] or 0)
            type_color = ft.Colors.GREEN_700 if move_type == "IN" else ft.Colors.RED_700
            self.table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(r[0] or "")),
                    ft.DataCell(ft.Text(move_type, color=type_color, weight=ft.FontWeight.W_600)),
                    ft.DataCell(ft.Text(f"{amt:,.2f}", color=type_color)),
                    ft.DataCell(ft.Text(r[3] or "")),
                ])
            )
        self._safe_update()

    def refresh(self):
        balance = self.db.get_cash_balance()
        color = ft.Colors.GREEN_700 if balance >= 0 else ft.Colors.RED_700
        self.lbl_balance.value = f"Kasa Bakiyesi: {balance:,.2f} TL"
        self.lbl_balance.color = color
        self._refresh_moves()
