import flet as ft


class StockPage(ft.Container):
    def __init__(self, db):
        super().__init__(expand=True)
        self.db = db
        self.dd_product = ft.Dropdown(label="Urun Sec *", expand=True, options=[])
        self.dd_type = ft.Dropdown(
            label="Islem Tipi",
            width=160,
            value="IN",
            options=[
                ft.dropdown.Option("IN", "Giris (+)"),
                ft.dropdown.Option("OUT", "Cikis (-)"),
            ],
        )
        self.txt_qty = ft.TextField(label="Miktar", width=130, value="1")
        self.txt_note = ft.TextField(label="Not / Aciklama", expand=True)
        self.txt_search = ft.TextField(
            label="Urun Ara",
            prefix_icon=ft.Icons.SEARCH,
            width=260,
            on_change=lambda _: self._filter_products(),
        )

        self.products_table = ft.DataTable(
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            heading_row_color=ft.Colors.INDIGO_50,
            column_spacing=24,
            columns=[
                ft.DataColumn(ft.Text("Urun Adi", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Barkod", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Birim", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Stok", weight=ft.FontWeight.W_600), numeric=True),
                ft.DataColumn(ft.Text("Durum", weight=ft.FontWeight.W_600)),
            ],
            rows=[],
        )
        self.moves_table = ft.DataTable(
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            heading_row_color=ft.Colors.INDIGO_50,
            column_spacing=18,
            columns=[
                ft.DataColumn(ft.Text("Tarih/Saat", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Urun", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Tip", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Miktar", weight=ft.FontWeight.W_600), numeric=True),
                ft.DataColumn(ft.Text("Not", weight=ft.FontWeight.W_600)),
            ],
            rows=[],
        )

        self._all_products = []

        # Tarih filtreleri
        from datetime import date, timedelta
        self.txt_move_from = ft.TextField(
            label="Başlangıç", width=130,
            value=(date.today() - timedelta(days=30)).strftime("%Y-%m-%d"),
            hint_text="YYYY-AA-GG",
        )
        self.txt_move_to = ft.TextField(
            label="Bitiş", width=130,
            value=date.today().strftime("%Y-%m-%d"),
            hint_text="YYYY-AA-GG",
        )

        self.content = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=14,
            controls=[
                ft.Text("Stok Yönetimi", size=26, weight=ft.FontWeight.BOLD),
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    padding=14,
                    content=ft.Column(
                        controls=[
                            ft.Text("Stok Hareketi Ekle", size=15, weight=ft.FontWeight.W_600, color=ft.Colors.INDIGO_700),
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Container(col={"sm": 12, "md": 5}, content=self.dd_product),
                                    ft.Container(col={"sm": 6, "md": 2}, content=self.dd_type),
                                    ft.Container(col={"sm": 6, "md": 2}, content=self.txt_qty),
                                    ft.Container(col={"sm": 12, "md": 3}, content=self.txt_note),
                                ]
                            ),
                            ft.ElevatedButton("Hareketi Kaydet", icon=ft.Icons.SAVE, on_click=self._save_move),
                        ],
                        spacing=10,
                    ),
                ),
                ft.Row(
                    [
                        ft.Text("Anlik Stok Durumu", size=16, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_GREY_700),
                        self.txt_search,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    wrap=True,
                ),
                ft.Container(
                    content=ft.Column([self.products_table], scroll=ft.ScrollMode.AUTO),
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    padding=10,
                ),
                ft.Row([
                    ft.Text("Stok Hareketleri", size=16,
                            weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_GREY_700),
                    self.txt_move_from,
                    ft.Text("—", size=13),
                    self.txt_move_to,
                    ft.ElevatedButton(
                        "Filtrele", icon=ft.Icons.FILTER_ALT,
                        style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_600,
                                             color=ft.Colors.WHITE),
                        height=38,
                        on_click=lambda _: self._refresh_moves(),
                    ),
                ], spacing=8, wrap=True),
                ft.Container(
                    content=ft.Column([self.moves_table], scroll=ft.ScrollMode.AUTO),
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    padding=10,
                ),
            ],
        )
        self.refresh()

    def _safe_update(self):
        try:
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

    def _save_move(self, _e: ft.ControlEvent):
        if not self.dd_product.value:
            self._snack("Lutfen urun seciniz")
            return
        qty = self._to_float(self.txt_qty.value)
        if qty <= 0:
            self._snack("Lutfen gecerli bir miktar giriniz")
            return
        pid = int(self.dd_product.value.split(" - ")[0])
        try:
            self.db.add_stock_move(pid, self.dd_type.value or "IN", qty, (self.txt_note.value or "").strip())
        except ValueError as ex:
            self._snack(str(ex))
            return
        self.txt_qty.value = "1"
        self.txt_note.value = ""
        self.refresh()
        self._safe_update()

    def _filter_products(self):
        search = (self.txt_search.value or "").strip().lower()
        rows = [r for r in self._all_products if search in (r[1] or "").lower() or search in (r[2] or "").lower()] if search else self._all_products
        self._render_products_table(rows)
        self._safe_update()

    def _render_products_table(self, products):
        self.products_table.rows = []
        for r in products:
            stock = float(r[6] or 0)
            # r[9] = critical_stock (list_products 10. kolonu)
            critical = float(r[9] if len(r) > 9 else 5)
            if stock <= 0:
                status = ft.Text("Stok Yok", color=ft.Colors.RED_700, weight=ft.FontWeight.W_600)
            elif stock <= critical:
                status = ft.Text(f"Kritik (<={critical:.0f})", color=ft.Colors.ORANGE_700, weight=ft.FontWeight.W_600)
            else:
                status = ft.Text("Yeterli", color=ft.Colors.GREEN_700)
            self.products_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(r[1] or "", weight=ft.FontWeight.W_500)),
                        ft.DataCell(ft.Text(r[2] or "")),
                        ft.DataCell(ft.Text(r[3] or "")),
                        ft.DataCell(ft.Text(f"{stock:.2f}", weight=ft.FontWeight.W_600)),
                        ft.DataCell(status),
                    ]
                )
            )

    def _refresh_moves(self):
        date_from = (self.txt_move_from.value or "").strip()
        date_to = (self.txt_move_to.value or "").strip()
        try:
            moves = self.db.list_stock_moves(date_from=date_from, date_to=date_to)
        except TypeError:
            moves = self.db.list_stock_moves()
        self.moves_table.rows = []
        for m in moves:
            tip_color = ft.Colors.GREEN_700 if m[2] == "IN" else ft.Colors.RED_700
            self.moves_table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(m[0])),
                    ft.DataCell(ft.Text(m[1])),
                    ft.DataCell(ft.Text(m[2], color=tip_color, weight=ft.FontWeight.W_600)),
                    ft.DataCell(ft.Text(f"{float(m[3]):.2f}")),
                    ft.DataCell(ft.Text(m[4] or "")),
                ])
            )
        self._safe_update()

    def refresh(self):
        products = self.db.list_products()
        self._all_products = products
        self.dd_product.options = [ft.dropdown.Option(f"{r[0]} - {r[1]}") for r in products]
        self._render_products_table(products)
        self._refresh_moves()
