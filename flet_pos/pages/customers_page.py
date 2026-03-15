import flet as ft


class CustomersPage(ft.Container):
    def __init__(self, db):
        super().__init__(expand=True)
        self.db = db
        self._edit_id: int | None = None  # Duzenleme modunda musteri id'si

        self.txt_name = ft.TextField(label="Musteri Adi *", expand=True)
        self.txt_phone = ft.TextField(label="Telefon", width=180)
        self.txt_address = ft.TextField(label="Adres", expand=True)
        self.btn_save = ft.ElevatedButton(
            "Musteri Ekle", icon=ft.Icons.PERSON_ADD, on_click=self._save_customer
        )
        self.btn_cancel = ft.TextButton(
            "Iptal", icon=ft.Icons.CANCEL, on_click=self._reset_form, visible=False
        )

        self.txt_payment = ft.TextField(label="Tahsilat Tutari", width=160, value="0")
        self.dd_customer = ft.Dropdown(label="Tahsilat Yapilacak Musteri", expand=True, options=[])
        self.lbl_customer_balance = ft.Text("Bakiye: -", size=13, color=ft.Colors.RED_700)

        self.txt_search = ft.TextField(
            label="Musteri Ara",
            prefix_icon=ft.Icons.SEARCH,
            width=280,
            on_change=lambda _: self._safe_refresh_table(),
        )

        self.table = ft.DataTable(
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            heading_row_color=ft.Colors.INDIGO_50,
            column_spacing=20,
            columns=[
                ft.DataColumn(ft.Text("Musteri", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Telefon", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Adres", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Bakiye (TL)", weight=ft.FontWeight.W_600), numeric=True),
                ft.DataColumn(ft.Text("Islemler", weight=ft.FontWeight.W_600)),
            ],
            rows=[],
        )

        self.lbl_total_debt = ft.Text(
            "Toplam Alacak: 0.00 TL", size=15, weight=ft.FontWeight.W_600, color=ft.Colors.RED_700
        )

        # Set on_select after creation (Flet API)
        self.dd_customer.on_select = self._on_customer_select

        self.content = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=14,
            controls=[
                ft.Text("Cari Hesap (Veresiye)", size=26, weight=ft.FontWeight.BOLD),
                # Musteri ekleme / duzenleme formu
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    padding=14,
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "Musteri Bilgileri",
                                size=15,
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.INDIGO_700,
                            ),
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Container(col={"sm": 12, "md": 5}, content=self.txt_name),
                                    ft.Container(col={"sm": 6, "md": 3}, content=self.txt_phone),
                                    ft.Container(col={"sm": 6, "md": 4}, content=self.txt_address),
                                ]
                            ),
                            ft.Row([self.btn_save, self.btn_cancel]),
                        ],
                        spacing=10,
                    ),
                ),
                # Tahsilat
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    padding=14,
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "Tahsilat Al",
                                size=15,
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.GREEN_700,
                            ),
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Container(col={"sm": 12, "md": 6}, content=self.dd_customer),
                                    ft.Container(col={"sm": 6, "md": 2}, content=self.lbl_customer_balance),
                                    ft.Container(col={"sm": 6, "md": 2}, content=self.txt_payment),
                                    ft.Container(
                                        col={"sm": 6, "md": 2},
                                        content=ft.ElevatedButton(
                                            "Tahsilat Al",
                                            icon=ft.Icons.PAYMENTS,
                                            on_click=self._take_payment,
                                        ),
                                    ),
                                ]
                            ),
                        ],
                        spacing=10,
                    ),
                ),
                # Arama + ozet
                ft.Row(
                    [
                        ft.Text(
                            "Musteri Listesi",
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.BLUE_GREY_700,
                        ),
                        self.lbl_total_debt,
                        self.txt_search,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    wrap=True,
                ),
                ft.Container(
                    content=ft.Column([self.table], scroll=ft.ScrollMode.AUTO),
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    padding=10,
                ),
                # İşlem geçmişi paneli (müşteri seçilince açılır)
                self._build_history_panel(),
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

    def _safe_refresh_table(self):
        self._render_table()
        self._safe_update()

    # ── Form ─────────────────────────────────────────────────────────────────

    def _reset_form(self, _e=None):
        self._edit_id = None
        self.txt_name.value = ""
        self.txt_phone.value = ""
        self.txt_address.value = ""
        self.btn_save.text = "Musteri Ekle"
        self.btn_save.icon = ft.Icons.PERSON_ADD
        self.btn_cancel.visible = False
        self._safe_update()

    def _load_customer(self, r):
        """Tablodan tiklanan musteri verilerini forma yukle."""
        self._edit_id = r[0]
        self.txt_name.value = r[1] or ""
        self.txt_phone.value = r[2] or ""
        self.txt_address.value = r[3] or ""
        self.btn_save.text = "Kaydet"
        self.btn_save.icon = ft.Icons.SAVE
        self.btn_cancel.visible = True
        self._safe_update()

    def _save_customer(self, _e: ft.ControlEvent):
        name = (self.txt_name.value or "").strip()
        if not name:
            self._snack("Musteri adi giriniz")
            return
        phone = (self.txt_phone.value or "").strip()
        address = (self.txt_address.value or "").strip()
        if self._edit_id:
            self.db.update_customer(self._edit_id, name, phone, address)
            self._snack(f"{name} guncellendi")
        else:
            self.db.add_customer(name, phone, address)
            self._snack(f"{name} eklendi")
        self._reset_form()
        self.refresh()

    # ── Silme Onay Diyalogu ───────────────────────────────────────────────────

    def _confirm_delete(self, customer_id: int, name: str):
        def do_delete(_e):
            try:
                self.db.delete_customer(customer_id)
                self._snack(f"{name} silindi")
            except Exception as ex:
                self._snack(f"Silinemedi: {ex}")
            self.page.dialog.open = False
            self.page.update()
            self.refresh()
            self._safe_update()

        def cancel(_e):
            self.page.dialog.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Musteri Sil"),
            content=ft.Text(f'"{name}" silinsin mi?'),
            actions=[
                ft.TextButton("Iptal", on_click=cancel),
                ft.ElevatedButton("Sil", icon=ft.Icons.DELETE, on_click=do_delete, color=ft.Colors.RED_700),
            ],
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    # ── Tahsilat ─────────────────────────────────────────────────────────────

    def _build_history_panel(self):
        """Müşteri işlem geçmişi paneli — başlangıçta gizli."""
        self.lbl_history_title = ft.Text(
            "", size=14, weight=ft.FontWeight.W_600, color=ft.Colors.INDIGO_700,
        )
        self.history_table = ft.DataTable(
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            border_radius=8,
            heading_row_color=ft.Colors.INDIGO_50,
            heading_row_height=36,
            data_row_min_height=40,
            column_spacing=16,
            columns=[
                ft.DataColumn(ft.Text("Tarih", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Tip", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Toplam", weight=ft.FontWeight.W_600), numeric=True),
                ft.DataColumn(ft.Text("İndirim", weight=ft.FontWeight.W_600), numeric=True),
                ft.DataColumn(ft.Text("Tür", weight=ft.FontWeight.W_600)),
            ],
            rows=[],
        )
        self._history_container = ft.Container(
            key="history_panel",
            visible=False,
            bgcolor=ft.Colors.WHITE,
            border_radius=12,
            padding=14,
            content=ft.Column([
                self.lbl_history_title,
                ft.Container(content=self.history_table, bgcolor=ft.Colors.WHITE),
            ], spacing=8),
        )
        return self._history_container

    def _show_history(self, customer_row):
        cid = customer_row[0]
        cname = customer_row[1]
        sales = self.db.list_customer_sales(cid)
        self.lbl_history_title.value = f"İşlem Geçmişi: {cname} ({len(sales)} kayıt)"
        self.history_table.rows = []
        for s in sales:
            sid, stime, pay, total, disc, is_ret = s
            typ_text = "İADE" if is_ret else "SATIŞ"
            typ_color = ft.Colors.ORANGE_700 if is_ret else ft.Colors.GREEN_700
            pay_colors = {
                "NAKIT": ft.Colors.GREEN_700,
                "POS": ft.Colors.BLUE_700,
                "VERESIYE": ft.Colors.PURPLE_700,
                "HAVALE": ft.Colors.TEAL_700,
            }
            self.history_table.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(stime or "")[:16], size=12)),
                ft.DataCell(ft.Text(pay or "", size=12,
                                    color=pay_colors.get(pay, ft.Colors.BLUE_GREY_600))),
                ft.DataCell(ft.Text(f"{float(total or 0):,.2f}", size=12,
                                    weight=ft.FontWeight.W_600)),
                ft.DataCell(ft.Text(f"{float(disc or 0):,.2f}", size=12,
                                    color=ft.Colors.ORANGE_600)),
                ft.DataCell(ft.Text(typ_text, size=12, color=typ_color,
                                    weight=ft.FontWeight.W_600)),
            ]))
        self._history_container.visible = True
        self._safe_update()
        # Geçmiş paneline scroll et
        try:
            self.content.scroll_to(key="history_panel", duration=300)
        except Exception:
            pass

    def _on_customer_select(self, e):
        if not self.dd_customer.value:
            self.lbl_customer_balance.value = "Bakiye: -"
            self._safe_update()
            return
        try:
            cid = int(self.dd_customer.value.split(" - ")[0])
        except (ValueError, IndexError):
            return
        rows = self.db.list_customers()
        row = next((r for r in rows if r[0] == cid), None)
        if row:
            balance = float(row[4] or 0)
            color = ft.Colors.RED_700 if balance > 0 else ft.Colors.GREEN_700
            self.lbl_customer_balance.value = f"Bakiye: {balance:.2f} TL"
            self.lbl_customer_balance.color = color
            self._safe_update()

    def _take_payment(self, _e: ft.ControlEvent):
        if not self.dd_customer.value:
            self._snack("Musteri seciniz")
            return
        amount = self._to_float(self.txt_payment.value)
        if amount <= 0:
            self._snack("Gecerli bir tutar giriniz")
            return
        cid = int(self.dd_customer.value.split(" - ")[0])
        # Asiri tahsilat uyarisi
        rows = self.db.list_customers()
        row = next((r for r in rows if r[0] == cid), None)
        if row:
            balance = float(row[4] or 0)
            if amount > balance + 0.01:
                self._snack(f"Uyari: Tahsilat borcu asiyor ({balance:.2f} TL)")
        self.db.add_customer_payment(cid, amount)
        self.txt_payment.value = "0"
        self.dd_customer.value = None
        self.lbl_customer_balance.value = "Bakiye: -"
        self.refresh()
        self._safe_update()

    # ── Tablo ─────────────────────────────────────────────────────────────────

    def _render_table(self):
        search = (self.txt_search.value or "").strip().lower()
        all_rows = self.db.list_customers()
        rows = [r for r in all_rows if not search or search in (r[1] or "").lower() or search in (r[2] or "").lower()]

        total_debt = sum(float(r[4] or 0) for r in all_rows if float(r[4] or 0) > 0)
        self.lbl_total_debt.value = f"Toplam Alacak: {total_debt:.2f} TL"
        self.dd_customer.options = [ft.dropdown.Option(f"{r[0]} - {r[1]}") for r in all_rows]

        self.table.rows = []
        for r in rows:
            balance = float(r[4] or 0)
            bal_color = ft.Colors.RED_700 if balance > 0 else ft.Colors.GREEN_700
            self.table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(r[1] or "", weight=ft.FontWeight.W_500)),
                        ft.DataCell(ft.Text(r[2] or "")),
                        ft.DataCell(ft.Text(r[3] or "")),
                        ft.DataCell(
                            ft.Text(f"{balance:.2f}", color=bal_color, weight=ft.FontWeight.W_600)
                        ),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        ft.Icons.HISTORY,
                                        tooltip="İşlem Geçmişi",
                                        icon_color=ft.Colors.TEAL_600,
                                        icon_size=18,
                                        on_click=lambda _, row=r: self._show_history(row),
                                    ),
                                    ft.IconButton(
                                        ft.Icons.EDIT,
                                        tooltip="Duzenle",
                                        icon_color=ft.Colors.INDIGO_600,
                                        icon_size=18,
                                        on_click=lambda _, row=r: self._load_customer(row),
                                    ),
                                    ft.IconButton(
                                        ft.Icons.DELETE,
                                        tooltip="Sil",
                                        icon_color=ft.Colors.RED_600,
                                        icon_size=18,
                                        on_click=lambda _, row=r: self._confirm_delete(row[0], row[1]),
                                    ),
                                ],
                                spacing=0,
                            )
                        ),
                    ]
                )
            )

    def refresh(self):
        self._render_table()
        self._safe_update()
