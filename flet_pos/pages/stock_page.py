from datetime import date, timedelta
import flet as ft


class StockPage(ft.Container):
    def __init__(self, db):
        self.db = db
        self._all_products = []

        # ── Tab 1: Add movement ───────────────────────────────────────────────
        self.dd_product = ft.Dropdown(label="Ürün Seç *", expand=True, options=[], dense=True)
        self.dd_type = ft.Dropdown(
            label="İşlem Tipi",
            width=160,
            value="IN",
            dense=True,
            options=[
                ft.dropdown.Option("IN", "Giriş (+)"),
                ft.dropdown.Option("OUT", "Çıkış (-)"),
                ft.dropdown.Option("ADJUST", "Düzeltme (=)"),
            ],
        )
        self.txt_qty = ft.TextField(label="Miktar", width=130, value="1", dense=True)
        self.txt_note = ft.TextField(label="Not / Açıklama", expand=True, dense=True)

        # ── Tab 1: Detailed stock status ─────────────────────────────────────
        self.txt_search = ft.TextField(
            label="Ürün Ara",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            on_change=lambda _: self._filter_products(),
            dense=True,
        )
        self.dd_stock_filter = ft.Dropdown(
            label="Stok Durumu",
            width=170,
            value="ALL",
            dense=True,
            options=[
                ft.dropdown.Option("ALL", "Tümü"),
                ft.dropdown.Option("LOW", "Kritik / Düşük"),
                ft.dropdown.Option("OUT", "Stok Yok"),
            ],
            on_select=lambda _: self._filter_products(),
        )
        self.lbl_stock_summary = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_600)

        self.products_table = ft.DataTable(
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            heading_row_color=ft.Colors.INDIGO_50,
            column_spacing=16,
            columns=[
                ft.DataColumn(ft.Text("Ürün Adı", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Barkod", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Kategori", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Birim", weight=ft.FontWeight.W_600)),
                ft.DataColumn(
                    ft.Text("Alış Fiyatı", weight=ft.FontWeight.W_600), numeric=True
                ),
                ft.DataColumn(
                    ft.Text("Satış Fiyatı", weight=ft.FontWeight.W_600), numeric=True
                ),
                ft.DataColumn(
                    ft.Text("Stok", weight=ft.FontWeight.W_600), numeric=True
                ),
                ft.DataColumn(ft.Text("Durum", weight=ft.FontWeight.W_600)),
            ],
            rows=[],
        )

        # ── Tab 2: Movement history ───────────────────────────────────────────
        self.txt_move_from = ft.TextField(
            label="Başlangıç",
            width=130,
            value=(date.today() - timedelta(days=30)).strftime("%Y-%m-%d"),
            hint_text="YYYY-AA-GG",
            dense=True,
        )
        self.txt_move_to = ft.TextField(
            label="Bitiş",
            width=130,
            value=date.today().strftime("%Y-%m-%d"),
            hint_text="YYYY-AA-GG",
            dense=True,
        )
        self.moves_table = ft.DataTable(
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            heading_row_color=ft.Colors.INDIGO_50,
            column_spacing=18,
            columns=[
                ft.DataColumn(ft.Text("Tarih/Saat", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Ürün", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Tip", weight=ft.FontWeight.W_600)),
                ft.DataColumn(
                    ft.Text("Miktar", weight=ft.FontWeight.W_600), numeric=True
                ),
                ft.DataColumn(ft.Text("Not", weight=ft.FontWeight.W_600)),
            ],
            rows=[],
        )

        _tab1 = ft.Container(
            padding=ft.padding.only(top=12),
            expand=True,
            content=ft.Column(
                expand=True, scroll=ft.ScrollMode.AUTO, spacing=14,
                controls=[
                    ft.Text("Stok Yönetimi", size=22, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        bgcolor=ft.Colors.WHITE, border_radius=12, padding=14,
                        content=ft.Column(controls=[
                            ft.Text("Stok Hareketi Ekle", size=14,
                                    weight=ft.FontWeight.W_600, color=ft.Colors.INDIGO_700),
                            ft.Row([self.dd_product, self.dd_type, self.txt_qty],
                                   spacing=10, wrap=True),
                            ft.Row([self.txt_note,
                                    ft.ElevatedButton("Hareketi Kaydet",
                                                      icon=ft.Icons.SAVE,
                                                      on_click=self._save_move)],
                                   spacing=10),
                        ], spacing=10),
                    ),
                    ft.Row([
                        ft.Text("Anlık Stok Durumu", size=15,
                                weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_GREY_700),
                        ft.Container(expand=True),
                        self.lbl_stock_summary,
                        self.dd_stock_filter,
                        self.txt_search,
                    ], spacing=8, wrap=True,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(
                        content=ft.Column([self.products_table], scroll=ft.ScrollMode.AUTO),
                        bgcolor=ft.Colors.WHITE, border_radius=12, padding=10),
                ],
            ),
        )
        _tab2 = ft.Container(
            padding=ft.padding.only(top=12),
            expand=True,
            content=ft.Column(
                expand=True, scroll=ft.ScrollMode.AUTO, spacing=10,
                controls=[
                    ft.Row([
                        ft.Text("Stok Hareketleri", size=22, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        self.txt_move_from, ft.Text("—", size=13), self.txt_move_to,
                        ft.ElevatedButton("Filtrele", icon=ft.Icons.FILTER_ALT,
                                          style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_600,
                                                               color=ft.Colors.WHITE),
                                          height=38,
                                          on_click=lambda _: self._refresh_moves()),
                    ], spacing=8, wrap=True,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(
                        content=ft.Column([self.moves_table], scroll=ft.ScrollMode.AUTO),
                        bgcolor=ft.Colors.WHITE, border_radius=12, padding=10),
                ],
            ),
        )
        content = ft.Tabs(
            selected_index=0,
            length=2,
            content=ft.Column(
                expand=True, spacing=0,
                controls=[
                    ft.TabBar(tabs=[
                        ft.Tab(label="Stok Girişi / Durumu", icon=ft.Icons.WAREHOUSE),
                        ft.Tab(label="Stok Hareketleri", icon=ft.Icons.HISTORY),
                    ]),
                    ft.TabBarView(controls=[_tab1, _tab2], expand=True),
                ],
            ),
        )
        super().__init__(expand=True, content=content)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _safe_update(self):
        if self.page is None:
            return
        try:
            self.update()
        except Exception:
            pass

    def _snack(self, text: str):
        if self.page is None:
            return
        try:
            self.page.snack_bar = ft.SnackBar(ft.Text(text), open=True)
            self.page.update()
        except Exception:
            pass

    def _to_float(self, value: str) -> float:
        try:
            return float((value or "").replace(",", "."))
        except ValueError:
            return 0.0

    # ── Stock movement ────────────────────────────────────────────────────────

    def _save_move(self, _e: ft.ControlEvent):
        if not self.dd_product.value:
            self._snack("Lütfen ürün seçiniz")
            return
        qty = self._to_float(self.txt_qty.value)
        if qty <= 0:
            self._snack("Lütfen geçerli bir miktar giriniz")
            return
        pid = int((self.dd_product.value or "").split(" - ")[0])
        try:
            self.db.add_stock_move(
                pid,
                self.dd_type.value or "IN",
                qty,
                (self.txt_note.value or "").strip(),
            )
        except ValueError as ex:
            self._snack(str(ex))
            return
        self.txt_qty.value = "1"
        self.txt_note.value = ""
        self.refresh()

    # ── Product stock table ───────────────────────────────────────────────────

    def _filter_products(self):
        search = (self.txt_search.value or "").strip().lower()
        stock_filter = self.dd_stock_filter.value or "ALL"

        rows = self._all_products
        if search:
            rows = [
                r
                for r in rows
                if search in (r[1] or "").lower() or search in (r[2] or "").lower()
            ]
        if stock_filter == "LOW":
            rows = [
                r
                for r in rows
                if float(r[6] or 0) <= float(r[9] if len(r) > 9 else 5) and float(r[6] or 0) > 0
            ]
        elif stock_filter == "OUT":
            rows = [r for r in rows if float(r[6] or 0) <= 0]

        self._render_products_table(rows)
        self._safe_update()

    def _render_products_table(self, products):
        # list_products returns:
        # id, name, barcode, unit, sell_price_incl_vat, vat_rate, stock,
        # image_path, is_scale_product, critical_stock, category, sub_category
        self.products_table.rows = []
        for r in products:
            stock = float(r[6] or 0)
            critical = float(r[9] if len(r) > 9 else 5)
            category = r[10] if len(r) > 10 else ""
            sell_price = float(r[4] or 0)

            # Get buy_price from product full if needed - but list_products doesn't include it
            # We use sell_price_incl_vat (r[4]) as the selling price display
            if stock <= 0:
                status = ft.Text(
                    "Stok Yok", color=ft.Colors.RED_700, weight=ft.FontWeight.W_600, size=12
                )
                row_color = ft.Colors.RED_50
            elif stock <= critical:
                status = ft.Text(
                    f"Kritik (≤{critical:.0f})",
                    color=ft.Colors.ORANGE_700,
                    weight=ft.FontWeight.W_600,
                    size=12,
                )
                row_color = ft.Colors.ORANGE_50
            else:
                status = ft.Text("Yeterli", color=ft.Colors.GREEN_700, size=12)
                row_color = None

            self.products_table.rows.append(
                ft.DataRow(
                    color=row_color,
                    cells=[
                        ft.DataCell(
                            ft.Text(r[1] or "", weight=ft.FontWeight.W_500, size=12)
                        ),
                        ft.DataCell(ft.Text(r[2] or "", size=11)),
                        ft.DataCell(
                            ft.Text(category or "—", size=11, color=ft.Colors.BLUE_GREY_500)
                        ),
                        ft.DataCell(ft.Text(r[3] or "", size=11)),
                        ft.DataCell(
                            ft.Text("—", size=11, color=ft.Colors.BLUE_GREY_300)
                        ),
                        ft.DataCell(
                            ft.Text(
                                f"{sell_price:.2f} ₺",
                                size=11,
                                color=ft.Colors.BLUE_700,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                f"{stock:.2f}",
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.RED_700
                                if stock <= 0
                                else (
                                    ft.Colors.ORANGE_700
                                    if stock <= critical
                                    else ft.Colors.GREEN_800
                                ),
                            )
                        ),
                        ft.DataCell(status),
                    ],
                )
            )

        # Summary
        total = len(self._all_products)
        out_count = sum(1 for r in self._all_products if float(r[6] or 0) <= 0)
        low_count = sum(
            1
            for r in self._all_products
            if 0 < float(r[6] or 0) <= float(r[9] if len(r) > 9 else 5)
        )
        self.lbl_stock_summary.value = (
            f"Toplam: {total}  |  Stok Yok: {out_count}  |  Kritik: {low_count}"
        )

    # ── Movement history ──────────────────────────────────────────────────────

    def _refresh_moves(self):
        date_from = (self.txt_move_from.value or "").strip()
        date_to = (self.txt_move_to.value or "").strip()
        try:
            moves = self.db.list_stock_moves(date_from=date_from, date_to=date_to)
        except TypeError:
            moves = self.db.list_stock_moves()

        type_colors = {
            "IN": ft.Colors.GREEN_700,
            "OUT": ft.Colors.RED_700,
            "ADJUST": ft.Colors.BLUE_700,
        }
        self.moves_table.rows = []
        for m in moves:
            tip_color = type_colors.get(m[2], ft.Colors.BLUE_GREY_600)
            self.moves_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(m[0])[:16], size=11)),
                        ft.DataCell(ft.Text(m[1] or "", size=12)),
                        ft.DataCell(
                            ft.Text(
                                m[2] or "",
                                color=tip_color,
                                weight=ft.FontWeight.W_600,
                                size=12,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(f"{float(m[3]):.2f}", size=12, weight=ft.FontWeight.W_500)
                        ),
                        ft.DataCell(ft.Text(m[4] or "", size=11)),
                    ]
                )
            )
        self._safe_update()

    # ── Main refresh ──────────────────────────────────────────────────────────

    def refresh(self):
        products = self.db.list_products()
        self._all_products = products
        self.dd_product.options = [
            ft.dropdown.Option(f"{r[0]} - {r[1]}") for r in products
        ]
        self._render_products_table(products)
        self._refresh_moves()
        self._safe_update()
