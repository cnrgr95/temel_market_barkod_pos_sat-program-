import flet as ft


class CustomersPage(ft.Container):
    def __init__(self, db):
        self.db = db
        self._edit_id: int | None = None
        self._selected_customer = None  # currently shown in history

        # ── Form fields ───────────────────────────────────────────────────────
        self.txt_name = ft.TextField(label="Müşteri Adı *", expand=True, dense=True)
        self.txt_phone = ft.TextField(label="Telefon", width=180, dense=True)
        self.txt_address = ft.TextField(label="Adres", expand=True, dense=True)
        self.txt_notes = ft.TextField(
            label="Açıklama / Not",
            multiline=True,
            min_lines=2,
            max_lines=3,
            expand=True,
            dense=True,
        )
        self.btn_save = ft.ElevatedButton(
            "Müşteri Ekle", icon=ft.Icons.PERSON_ADD, on_click=self._save_customer
        )
        self.btn_cancel = ft.TextButton(
            "İptal", icon=ft.Icons.CANCEL, on_click=self._reset_form, visible=False
        )

        # ── Payment fields ────────────────────────────────────────────────────
        self.txt_payment = ft.TextField(label="Tahsilat Tutarı", width=160, value="0", dense=True)
        self.dd_customer = ft.Dropdown(
            label="Tahsilat — Müşteri Seç", expand=True, options=[], dense=True
        )
        self.dd_customer.on_select = self._on_customer_select
        self.lbl_customer_balance = ft.Text("Bakiye: -", size=13, color=ft.Colors.RED_700)

        # ── Left panel: search + list ─────────────────────────────────────────
        self.txt_search = ft.TextField(
            label="Müşteri Ara",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            on_change=lambda _: self._safe_refresh_list(),
            dense=True,
        )
        self.lbl_total_debt = ft.Text(
            "Toplam Alacak: 0.00 ₺",
            size=12,
            weight=ft.FontWeight.W_600,
            color=ft.Colors.RED_700,
        )
        self.customer_list_col = ft.Column(
            spacing=2,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        # ── Right panel: history ──────────────────────────────────────────────
        self.lbl_history_title = ft.Text(
            "Geçmişi görmek için soldaki listeden müşteri seçin",
            size=13,
            color=ft.Colors.BLUE_GREY_400,
            italic=True,
        )
        self.lbl_selected_balance = ft.Text(
            "", size=13, weight=ft.FontWeight.W_600
        )
        self.history_col = ft.Column(
            spacing=4,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        content = self._build_layout()
        super().__init__(expand=True, content=content)

    # ── Dialog helpers ────────────────────────────────────────────────────────

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

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_layout(self):
        # ── Left panel: compact customer list ────────────────────────────────
        form_card = ft.Container(
            bgcolor=ft.Colors.WHITE,
            border_radius=12,
            padding=14,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Text(
                        "Müşteri Bilgileri",
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.INDIGO_700,
                    ),
                    ft.Row([self.txt_name, self.txt_phone], spacing=10),
                    self.txt_address,
                    self.txt_notes,
                    ft.Row([self.btn_save, self.btn_cancel], spacing=8),
                ],
            ),
        )

        payment_card = ft.Container(
            bgcolor=ft.Colors.WHITE,
            border_radius=12,
            padding=14,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Text(
                        "Tahsilat Al",
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.GREEN_700,
                    ),
                    ft.Row(
                        [self.dd_customer, self.lbl_customer_balance],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        [
                            self.txt_payment,
                            ft.ElevatedButton(
                                "Tahsilat Al",
                                icon=ft.Icons.PAYMENTS,
                                on_click=self._take_payment,
                            ),
                        ],
                        spacing=10,
                    ),
                ],
            ),
        )

        history_card = ft.Container(
            bgcolor=ft.Colors.WHITE,
            border_radius=12,
            padding=14,
            expand=True,
            content=ft.Column(
                spacing=8,
                expand=True,
                controls=[
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.HISTORY, color=ft.Colors.INDIGO_500, size=16),
                            self.lbl_history_title,
                            ft.Container(expand=True),
                            self.lbl_selected_balance,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Divider(height=1),
                    self.history_col,
                ],
            ),
        )

        top_list = ft.Container(
            bgcolor=ft.Colors.WHITE,
            border_radius=12,
            padding=12,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.PEOPLE, color=ft.Colors.INDIGO_600, size=18),
                            ft.Text("Musteri Listesi", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_700),
                            ft.Container(expand=True),
                            ft.ElevatedButton(
                                "Yeni",
                                icon=ft.Icons.PERSON_ADD,
                                on_click=self._reset_form,
                                height=32,
                                style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=10)),
                            ),
                        ],
                        spacing=6,
                    ),
                    ft.Row([self.txt_search, self.lbl_total_debt], spacing=10),
                    ft.Container(
                        height=220,
                        bgcolor=ft.Colors.GREY_50,
                        border_radius=10,
                        border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                        padding=6,
                        content=self.customer_list_col,
                    ),
                ],
            ),
        )

        right_panel = ft.Column(
            spacing=10,
            expand=True,
            controls=[
                ft.Text(
                    "Cari Hesap (Veresiye)",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.INDIGO_700,
                ),
                form_card,
                payment_card,
                history_card,
            ],
        )

        return ft.Column(
            expand=True,
            spacing=12,
            controls=[
                top_list,
                right_panel,
            ],
        )

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

    def _customer_option_value(self, row) -> str:
        return f"{row[0]} - {row[1]}"

    def _parse_customer_id(self, value: str | None) -> int | None:
        if not value:
            return None
        try:
            return int(str(value).split(" - ")[0])
        except (ValueError, IndexError):
            return None

    def _find_customer(self, customer_id: int | None):
        if customer_id is None:
            return None
        return next((r for r in self.db.list_customers() if r[0] == customer_id), None)

    def _set_payment_customer(self, row):
        if not row:
            self.dd_customer.value = None
            self.lbl_customer_balance.value = "Bakiye: -"
            self.lbl_customer_balance.color = ft.Colors.RED_700
            return
        balance = float(row[4] or 0)
        self.dd_customer.value = self._customer_option_value(row)
        self.lbl_customer_balance.value = f"Bakiye: {balance:.2f} TL"
        self.lbl_customer_balance.color = ft.Colors.RED_700 if balance > 0 else ft.Colors.GREEN_700

    def _safe_refresh_list(self):
        self._render_list()
        self._safe_update()

    # ── Form ─────────────────────────────────────────────────────────────────

    def _reset_form(self, _e=None):
        self._edit_id = None
        self.txt_name.value = ""
        self.txt_phone.value = ""
        self.txt_address.value = ""
        self.txt_notes.value = ""
        self.btn_save.text = "Müşteri Ekle"
        self.btn_save.icon = ft.Icons.PERSON_ADD
        self.btn_cancel.visible = False
        self._safe_update()

    def _load_customer(self, r):
        """Listeden seçilen müşteriyi forma yükle."""
        # r: (id, name, phone, address, balance, notes)
        self._edit_id = r[0]
        self.txt_name.value = r[1] or ""
        self.txt_phone.value = r[2] or ""
        self.txt_address.value = r[3] or ""
        self.txt_notes.value = r[5] if len(r) > 5 else ""
        self.btn_save.text = "Kaydet"
        self.btn_save.icon = ft.Icons.SAVE
        self.btn_cancel.visible = True
        self._safe_update()

    def _save_customer(self, _e: ft.ControlEvent):
        name = (self.txt_name.value or "").strip()
        if not name:
            self._snack("Müşteri adı giriniz")
            return
        phone = (self.txt_phone.value or "").strip()
        address = (self.txt_address.value or "").strip()
        notes = (self.txt_notes.value or "").strip()
        if self._edit_id:
            self.db.update_customer(self._edit_id, name, phone, address, notes)
            self._snack(f"{name} güncellendi")
        else:
            self.db.add_customer(name, phone, address, notes=notes)
            self._snack(f"{name} eklendi")
        self._reset_form()
        self.refresh()

    # ── Delete dialog ─────────────────────────────────────────────────────────

    def _confirm_delete(self, customer_id: int, name: str):
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Müşteri Sil"),
            content=ft.Text(f'"{name}" silinsin mi?\nBu işlem geri alınamaz.'),
        )

        def do_delete(_e):
            try:
                self.db.delete_customer(customer_id)
                self._snack(f"{name} silindi")
            except Exception as ex:
                self._snack(f"Silinemedi: {ex}")
            self._close_dialog(dlg)
            self.refresh()

        def cancel(_e):
            self._close_dialog(dlg)

        dlg.actions = [
            ft.TextButton("İptal", on_click=cancel),
            ft.ElevatedButton(
                "Sil", icon=ft.Icons.DELETE, on_click=do_delete, color=ft.Colors.RED_700
            ),
        ]
        self._open_dialog(dlg)

    # ── Payment ───────────────────────────────────────────────────────────────

    # ── Customer list (left panel) ────────────────────────────────────────────

    def _on_customer_select(self, _e):
        cid = self._parse_customer_id(self.dd_customer.value)
        if cid is None:
            self.lbl_customer_balance.value = "Bakiye: -"
            self._safe_update()
            return
        row = self._find_customer(cid)
        if row:
            self._set_payment_customer(row)
            self._safe_update()

    def _take_payment(self, _e: ft.ControlEvent):
        cid = self._parse_customer_id(self.dd_customer.value)
        if cid is None:
            self._snack("Musteri seciniz")
            return
        amount = self._to_float(self.txt_payment.value)
        if amount <= 0:
            self._snack("Gecerli bir tutar giriniz")
            return

        row = self._find_customer(cid)
        if row:
            balance = float(row[4] or 0)
            if amount > balance + 0.01:
                self._snack(f"Uyari: Tahsilat borcu asiyor ({balance:.2f} TL)")
        self.db.add_customer_payment(cid, amount)
        self.txt_payment.value = "0"
        updated = self._find_customer(cid)
        self._set_payment_customer(updated)
        if self._selected_customer is not None and self._selected_customer[0] == cid and updated:
            self._show_history(updated)
        else:
            self.refresh()

    def _render_list(self):
        search = (self.txt_search.value or "").strip().lower()
        all_rows = self.db.list_customers()
        filtered = [
            r
            for r in all_rows
            if not search
            or search in (r[1] or "").lower()
            or search in (r[2] or "").lower()
        ]

        total_debt = sum(float(r[4] or 0) for r in all_rows if float(r[4] or 0) > 0)
        self.lbl_total_debt.value = f"Toplam Alacak: {total_debt:.2f} ₺"
        current_customer_value = self.dd_customer.value
        valid_values = {self._customer_option_value(r) for r in all_rows}
        self.dd_customer.options = [
            ft.dropdown.Option(self._customer_option_value(r), f"{r[1]} | {float(r[4] or 0):.2f} TL") for r in all_rows
        ]
        self.dd_customer.value = current_customer_value if current_customer_value in valid_values else None

        self.customer_list_col.controls = []
        for r in filtered:
            balance = float(r[4] or 0)
            bal_color = ft.Colors.RED_700 if balance > 0 else ft.Colors.GREEN_700
            is_selected = (
                self._selected_customer is not None
                and r[0] == self._selected_customer[0]
            )

            tile = ft.Container(
                bgcolor=ft.Colors.INDIGO_50 if is_selected else ft.Colors.TRANSPARENT,
                border_radius=8,
                padding=ft.padding.symmetric(vertical=6, horizontal=8),
                content=ft.Row(
                    controls=[
                        ft.Column(
                            spacing=1,
                            expand=True,
                            controls=[
                                ft.Text(
                                    r[1] or "",
                                    size=13,
                                    weight=ft.FontWeight.W_600,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(
                                    r[2] or "—",
                                    size=11,
                                    color=ft.Colors.BLUE_GREY_400,
                                    max_lines=1,
                                ),
                            ],
                        ),
                        ft.Text(
                            f"{balance:.2f} ₺",
                            size=12,
                            color=bal_color,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Row(
                            [
                                ft.IconButton(
                                    ft.Icons.EDIT,
                                    icon_color=ft.Colors.INDIGO_400,
                                    icon_size=15,
                                    tooltip="Düzenle",
                                    on_click=lambda _, row=r: self._load_customer(row),
                                ),
                                ft.IconButton(
                                    ft.Icons.DELETE,
                                    icon_color=ft.Colors.RED_400,
                                    icon_size=15,
                                    tooltip="Sil",
                                    on_click=lambda _, row=r: self._confirm_delete(
                                        row[0], row[1]
                                    ),
                                ),
                            ],
                            spacing=0,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                on_click=lambda _, row=r: self._show_history(row),
                ink=True,
            )
            self.customer_list_col.controls.append(tile)

    # ── History (right panel) ─────────────────────────────────────────────────

    def _show_history(self, customer_row):
        self._selected_customer = customer_row
        cid = customer_row[0]
        cname = customer_row[1]
        balance = float(customer_row[4] or 0)

        self.lbl_history_title.value = f"{cname} — İşlem Geçmişi"
        self.lbl_history_title.italic = False
        self.lbl_history_title.color = ft.Colors.INDIGO_700
        self.lbl_selected_balance.value = f"Bakiye: {balance:.2f} ₺"
        self.lbl_selected_balance.color = (
            ft.Colors.RED_700 if balance > 0 else ft.Colors.GREEN_700
        )

        self._set_payment_customer(customer_row)
        sales = self.db.list_customer_sales(cid)
        self.history_col.controls = []

        if not sales:
            self.history_col.controls.append(
                ft.Container(
                    padding=20,
                    content=ft.Text(
                        "Henüz işlem kaydı yok",
                        color=ft.Colors.BLUE_GREY_300,
                        italic=True,
                        size=13,
                    ),
                )
            )
        else:
            for s in sales:
                sid, stime, pay, total, disc, is_ret = s
                self.history_col.controls.append(
                    self._build_history_row(sid, stime, pay, total, disc, is_ret)
                )

        # Re-render list to update selection highlight
        self._render_list()
        self._safe_update()

    def _build_history_row(self, sid, stime, pay, total, disc, is_ret):
        if is_ret == 2 or pay == "TAHSILAT":
            typ_text = "TAHSİLAT"
            typ_color = ft.Colors.BLUE_700
        elif is_ret:
            typ_text = "İADE"
            typ_color = ft.Colors.ORANGE_700
        else:
            typ_text = "SATIŞ"
            typ_color = ft.Colors.GREEN_700

        pay_colors = {
            "NAKIT": ft.Colors.GREEN_700,
            "POS": ft.Colors.BLUE_700,
            "VERESIYE": ft.Colors.PURPLE_700,
            "HAVALE": ft.Colors.TEAL_700,
            "NAKIT+POS": ft.Colors.CYAN_700,
            "TAHSILAT": ft.Colors.INDIGO_700,
        }
        pay_color = pay_colors.get(pay, ft.Colors.BLUE_GREY_600)

        return ft.Container(
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            border_radius=8,
            padding=ft.padding.symmetric(vertical=8, horizontal=12),
            margin=ft.margin.only(bottom=4),
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.UNDO if is_ret else ft.Icons.SHOPPING_CART,
                        color=typ_color,
                        size=16,
                    ),
                    ft.Column(
                        spacing=3,
                        expand=True,
                        controls=[
                            ft.Text(
                                str(stime or "")[:16],
                                size=11,
                                color=ft.Colors.BLUE_GREY_500,
                            ),
                            ft.Row(
                                [
                                    ft.Container(
                                        bgcolor=ft.Colors.PURPLE_50
                                        if pay == "VERESIYE"
                                        else ft.Colors.GREEN_50,
                                        border_radius=4,
                                        padding=ft.padding.symmetric(
                                            vertical=2, horizontal=6
                                        ),
                                        content=ft.Text(
                                            pay or "",
                                            size=10,
                                            color=pay_color,
                                            weight=ft.FontWeight.W_600,
                                        ),
                                    ),
                                    ft.Container(
                                        bgcolor=ft.Colors.ORANGE_50
                                        if is_ret
                                        else ft.Colors.BLUE_50,
                                        border_radius=4,
                                        padding=ft.padding.symmetric(
                                            vertical=2, horizontal=6
                                        ),
                                        content=ft.Text(
                                            typ_text,
                                            size=10,
                                            color=typ_color,
                                            weight=ft.FontWeight.W_600,
                                        ),
                                    ),
                                ],
                                spacing=4,
                            ),
                        ],
                    ),
                    ft.Column(
                        spacing=2,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                        controls=[
                            ft.Text(
                                f"{float(total or 0):,.2f} ₺",
                                size=13,
                                weight=ft.FontWeight.W_700,
                            ),
                            ft.Text(
                                f"İnd: {float(disc or 0):,.2f} ₺",
                                size=10,
                                color=ft.Colors.ORANGE_600,
                            ),
                        ],
                    ),
                    ft.IconButton(
                        ft.Icons.LIST_ALT,
                        icon_color=ft.Colors.INDIGO_400,
                        icon_size=18,
                        tooltip="Ürünleri Göster",
                        on_click=lambda _, sale_id=sid, t=stime, tot=total: self._show_sale_items(
                            sale_id, t, tot
                        ),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _show_sale_items(self, sale_id: int, stime, total):
        items = self.db.get_sale_items_full(sale_id)
        if items:
            rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(pname or "(silinmiş)", size=12)),
                        ft.DataCell(
                            ft.Text(f"{float(qty or 0):.2f} {unit}", size=12)
                        ),
                        ft.DataCell(
                            ft.Text(f"{float(unit_price or 0):.2f} ₺", size=12),
                        ),
                        ft.DataCell(
                            ft.Text(
                                f"{float(line_total or 0):.2f} ₺",
                                size=12,
                                weight=ft.FontWeight.W_600,
                            ),
                        ),
                    ]
                )
                for pname, qty, unit_price, item_disc, vat_rate, line_total, unit in items
            ]
            body = ft.Column(
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.DataTable(
                        border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                        border_radius=8,
                        heading_row_color=ft.Colors.INDIGO_50,
                        column_spacing=16,
                        columns=[
                            ft.DataColumn(
                                ft.Text("Ürün", weight=ft.FontWeight.W_600)
                            ),
                            ft.DataColumn(
                                ft.Text("Miktar", weight=ft.FontWeight.W_600)
                            ),
                            ft.DataColumn(
                                ft.Text("Birim Fiyat", weight=ft.FontWeight.W_600),
                                numeric=True,
                            ),
                            ft.DataColumn(
                                ft.Text("Toplam", weight=ft.FontWeight.W_600),
                                numeric=True,
                            ),
                        ],
                        rows=rows,
                    ),
                    ft.Divider(),
                    ft.Text(
                        f"Genel Toplam: {float(total or 0):,.2f} ₺",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.RIGHT,
                    ),
                ],
            )
        else:
            body = ft.Text(
                "Bu satışa ait kalem bulunamadı",
                color=ft.Colors.BLUE_GREY_300,
                italic=True,
            )

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Satış Kalemleri — {str(stime or '')[:16]}"),
            content=ft.Container(width=500, content=body),
        )
        dlg.actions = [
            ft.TextButton("Kapat", on_click=lambda _: self._close_dialog(dlg))
        ]
        self._open_dialog(dlg)

    # ── Main refresh ──────────────────────────────────────────────────────────

    def refresh(self):
        selected_id = self._selected_customer[0] if self._selected_customer else None
        if selected_id:
            updated = self._find_customer(selected_id)
            if updated:
                self._show_history(updated)
                return
            self._selected_customer = None
            self.lbl_history_title.value = "Gecmisi gormek icin soldaki listeden musteri secin"
            self.lbl_history_title.italic = True
            self.lbl_history_title.color = ft.Colors.BLUE_GREY_400
            self.lbl_selected_balance.value = ""
            self.history_col.controls = []
        self._render_list()
        self._safe_update()

