from datetime import date, timedelta
import flet as ft


class StockPage(ft.Container):
    def __init__(self, db, on_stock_changed=None):
        self.db = db
        self.on_stock_changed = on_stock_changed

        # ── Tab 1: Add movement ───────────────────────────────────────────────
        self.dd_product = ft.Dropdown(label="Ürün Seç *", expand=True, options=[], dense=True)
        self.txt_product_search = ft.TextField(
            label="Ürün Ara",
            expand=True,
            prefix_icon=ft.Icons.SEARCH,
            on_change=lambda _: self._schedule_product_picker_refresh(),
            dense=True,
        )
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
            on_change=lambda _: self._schedule_filter_products(),
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

        self._table_page_index = 0
        self._table_page_size = 150
        self._table_total = 0
        self._table_query_key = ("", "ALL")
        self._search_timer = None
        self._product_search_timer = None
        self.lbl_page_info = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_600)
        self.btn_page_prev = ft.IconButton(
            ft.Icons.ARROW_BACK,
            tooltip="Önceki sayfa",
            on_click=lambda _: self._goto_prev_page(),
        )
        self.btn_page_next = ft.IconButton(
            ft.Icons.ARROW_FORWARD,
            tooltip="Sonraki sayfa",
            on_click=lambda _: self._goto_next_page(),
        )

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
                ft.DataColumn(
                    ft.Text("Kritik", weight=ft.FontWeight.W_600), numeric=True
                ),
                ft.DataColumn(ft.Text("Durum", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Islem", weight=ft.FontWeight.W_600)),
            ],
            rows=[],
        )

        self.dd_bulk_mode = ft.Dropdown(
            label="Toplu mod",
            width=150,
            value="SET",
            dense=True,
            options=[
                ft.dropdown.Option("SET", "Stok Ata (=)"),
                ft.dropdown.Option("ADD", "Stok Ekle (+/-)"),
            ],
        )
        self.txt_bulk_rows = ft.TextField(
            label="Toplu stok girisi (barkod, miktar)",
            multiline=True,
            min_lines=4,
            max_lines=8,
            expand=True,
            dense=True,
            hint_text="Ornek:\n8690000000001, 12\n8690000000002, -3\n",
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
                            ft.Row([self.txt_product_search], spacing=10),
                            ft.Row([self.dd_product, self.dd_type, self.txt_qty],
                                   spacing=10),
                            ft.Row([self.txt_note,
                                    ft.ElevatedButton("Hareketi Kaydet",
                                                      icon=ft.Icons.SAVE,
                                                      on_click=self._save_move)],
                                   spacing=10),
                        ], spacing=10),
                    ),
                    ft.Container(
                        bgcolor=ft.Colors.WHITE, border_radius=12, padding=14,
                        content=ft.Column(controls=[
                            ft.Text("Toplu Stok Girisi", size=14,
                                    weight=ft.FontWeight.W_600, color=ft.Colors.TEAL_700),
                            ft.Row([self.dd_bulk_mode, ft.Text("Her satir: barkod, miktar")], spacing=10),
                            self.txt_bulk_rows,
                            ft.ElevatedButton(
                                "Toplu Uygula",
                                icon=ft.Icons.PLAYLIST_ADD_CHECK,
                                style=ft.ButtonStyle(bgcolor=ft.Colors.TEAL_600, color=ft.Colors.WHITE),
                                on_click=self._apply_bulk_stock,
                            ),
                        ], spacing=10),
                    ),
                    ft.Row([
                        ft.Text("Anlık Stok Durumu", size=15,
                                weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_GREY_700),
                        ft.Container(expand=True),
                        self.lbl_stock_summary,
                        self.dd_stock_filter,
                        self.txt_search,
                    ], spacing=8,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row(
                        [self.btn_page_prev, self.lbl_page_info, self.btn_page_next],
                        alignment=ft.MainAxisAlignment.END,
                        spacing=6,
                    ),
                    ft.Container(
                        content=ft.Column([self.products_table], scroll=ft.ScrollMode.AUTO),
                        bgcolor=ft.Colors.WHITE, border_radius=12, padding=10, expand=True),
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
                    ], spacing=8,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(
                        content=ft.Column([self.moves_table], scroll=ft.ScrollMode.AUTO),
                        bgcolor=ft.Colors.WHITE, border_radius=12, padding=10, expand=True),
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

    def _open_dialog(self, dlg: ft.AlertDialog):
        if self.page is None:
            return
        if dlg not in self.page.overlay:
            self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _close_dialog(self, dlg: ft.AlertDialog):
        dlg.open = False
        if self.page:
            self.page.update()

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
        if self.on_stock_changed:
            self.on_stock_changed()

    # ── Product stock table ───────────────────────────────────────────────────

    def _apply_bulk_stock(self, _e):
        raw = (self.txt_bulk_rows.value or "").strip()
        if not raw:
            self._snack("Toplu liste bos")
            return
        rows = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            parts = [p.strip() for p in line.replace(";", ",").split(",") if p.strip()]
            if len(parts) < 2:
                continue
            barcode = parts[0]
            try:
                qty = float(parts[1].replace(",", "."))
            except ValueError:
                continue
            prod = self.db.get_product_by_barcode(barcode)
            if not prod:
                continue
            rows.append((int(prod[0]), qty))
        if not rows:
            self._snack("Uygulanacak satir bulunamadi")
            return
        mode = self.dd_bulk_mode.value or "SET"
        updated = self.db.bulk_update_stock_levels(rows, mode=mode, note="Toplu stok girisi")
        self.txt_bulk_rows.value = ""
        self.refresh()
        if self.on_stock_changed:
            self.on_stock_changed()
        self._snack(f"Toplu stok guncellendi: {updated} urun")

    def _refresh_product_picker_options(self):
        query = (self.txt_product_search.value or "").strip()
        rows = self.db.search_products(search=query, limit=100, offset=0)
        self.dd_product.options = [ft.dropdown.Option(f"{r[0]} - {r[1]}") for r in rows]
        self._safe_update()

    def _schedule_product_picker_refresh(self, delay: float = 0.25):
        try:
            if self._product_search_timer:
                self._product_search_timer.cancel()
        except Exception:
            pass
        import threading
        self._product_search_timer = threading.Timer(delay, self._refresh_product_picker_options)
        self._product_search_timer.daemon = True
        self._product_search_timer.start()

    def _schedule_filter_products(self, delay: float = 0.25):
        try:
            if self._search_timer:
                self._search_timer.cancel()
        except Exception:
            pass
        import threading
        self._search_timer = threading.Timer(delay, self._filter_products)
        self._search_timer.daemon = True
        self._search_timer.start()

    def _goto_prev_page(self):
        if self._table_page_index <= 0:
            return
        self._table_page_index -= 1
        self._filter_products()

    def _goto_next_page(self):
        max_page = max(0, (self._table_total - 1) // self._table_page_size)
        if self._table_page_index >= max_page:
            return
        self._table_page_index += 1
        self._filter_products()

    def _filter_products(self):
        search = (self.txt_search.value or "").strip().lower()
        stock_filter = self.dd_stock_filter.value or "ALL"
        query_key = (search, stock_filter)
        if query_key != self._table_query_key:
            self._table_query_key = query_key
            self._table_page_index = 0

        self._table_total = self.db.count_products(search=search, stock_filter=stock_filter)
        max_page = max(0, (self._table_total - 1) // self._table_page_size) if self._table_total else 0
        if self._table_page_index > max_page:
            self._table_page_index = max_page
        offset = self._table_page_index * self._table_page_size
        rows = self.db.search_products(
            search=search,
            stock_filter=stock_filter,
            limit=self._table_page_size,
            offset=offset,
        )

        self._render_products_table(rows)
        if not rows:
            self.lbl_page_info.value = "0 urun"
            self.btn_page_prev.disabled = True
            self.btn_page_next.disabled = True
        else:
            total_pages = max_page + 1 if self._table_total else 1
            self.lbl_page_info.value = (
                f"Sayfa {self._table_page_index + 1}/{total_pages} | Toplam {self._table_total}"
            )
            self.btn_page_prev.disabled = self._table_page_index <= 0
            self.btn_page_next.disabled = self._table_page_index >= max_page
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
                        ft.DataCell(
                            ft.Text(f"{critical:.2f}", size=11, color=ft.Colors.BLUE_GREY_700)
                        ),
                        ft.DataCell(status),
                        ft.DataCell(
                            ft.IconButton(
                                ft.Icons.EDIT,
                                icon_size=16,
                                tooltip="Duzenle",
                                on_click=lambda _, row=r: self._open_edit_dialog(row),
                            )
                        ),
                    ],
                )
            )

        # Summary is refreshed in refresh() using DB counts.

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

    def _open_edit_dialog(self, row):
        pid, name, _barcode, _unit, sell_price, _vat_rate, stock, _image, _scale, critical, *_ = row
        txt_buy = ft.TextField(label="Alis Fiyati", value=str(row[7] or 0), width=140)
        txt_sell = ft.TextField(label="Satis Fiyati", value=str(sell_price or 0), width=140)
        txt_stock = ft.TextField(label="Stok", value=str(stock or 0), width=120)
        txt_critical = ft.TextField(label="Kritik Stok", value=str(critical or 0), width=120)
        msg = ft.Text("", size=11, color=ft.Colors.RED_600)

        def _save(_e):
            try:
                buy = float((txt_buy.value or "0").replace(",", "."))
                sell = float((txt_sell.value or "0").replace(",", "."))
                new_stock = float((txt_stock.value or "0").replace(",", "."))
                crit = float((txt_critical.value or "0").replace(",", "."))
            except ValueError:
                msg.value = "Gecersiz sayi"
                self._safe_update()
                return
            try:
                self.db.update_product_stock_pricing(
                    pid,
                    buy_price=buy,
                    sell_price_incl=sell,
                    stock=new_stock,
                    critical_stock=crit,
                )
            except Exception as ex:
                msg.value = str(ex)
                self._safe_update()
                return
            self._close_dialog(dlg)
            self.refresh()
            if self.on_stock_changed:
                self.on_stock_changed()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Stok / Fiyat Duzenle - {name}"),
            content=ft.Column(
                [
                    ft.Row([txt_buy, txt_sell], spacing=10),
                    ft.Row([txt_stock, txt_critical], spacing=10),
                    msg,
                ],
                tight=True,
                spacing=10,
            ),
            actions=[
                ft.TextButton("Vazgec", on_click=lambda _: self._close_dialog(dlg)),
                ft.ElevatedButton("Kaydet", icon=ft.Icons.SAVE, on_click=_save),
            ],
        )
        self._open_dialog(dlg)

    def refresh(self):
        total = self.db.count_products()
        out_count = self.db.count_products(stock_filter="OUT")
        low_count = self.db.count_products(stock_filter="LOW")
        self.lbl_stock_summary.value = f"Toplam: {total} | Kritik: {low_count} | Stok yok: {out_count}"
        self._refresh_product_picker_options()
        self._filter_products()
        self._refresh_moves()
        self._safe_update()



