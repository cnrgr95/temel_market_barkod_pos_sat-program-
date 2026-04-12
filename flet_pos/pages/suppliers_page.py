import flet as ft


class SuppliersPage(ft.Container):
    def __init__(self, db):
        self.db = db
        self._editing_id: int | None = None

        # ── Form alanları ──────────────────────────────────────────────────
        self.lbl_form_title = ft.Text(
            "Yeni Tedarikçi", size=15, weight=ft.FontWeight.W_600,
            color=ft.Colors.INDIGO_700,
        )
        self.txt_name = ft.TextField(label="Tedarikçi Adı *", expand=True)
        self.txt_phone = ft.TextField(label="Telefon", width=180)
        self.txt_address = ft.TextField(label="Adres", expand=True)
        self.btn_save = ft.ElevatedButton(
            "Kaydet",
            icon=ft.Icons.SAVE,
            style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_600, color=ft.Colors.WHITE),
            on_click=self._save_supplier,
        )
        self.btn_cancel = ft.TextButton(
            "İptal", icon=ft.Icons.CANCEL,
            visible=False, on_click=lambda _: self._reset_form(),
        )

        # ── Borç/Ödeme işlemleri ──────────────────────────────────────────
        self.dd_supplier = ft.Dropdown(
            label="Tedarikçi Seç", expand=True, options=[],
        )
        self.dd_supplier.on_select = lambda _: self._on_supplier_selected()
        self.lbl_balance = ft.Text("Borç: 0,00 ₺", size=13,
                                   color=ft.Colors.RED_600, weight=ft.FontWeight.W_600)
        self.txt_amount = ft.TextField(
            label="Tutar (₺)", width=150,
            keyboard_type=ft.KeyboardType.NUMBER, value="",
        )
        self.txt_note = ft.TextField(label="Not", expand=True)
        self.dd_move_type = ft.Dropdown(
            label="İşlem Tipi", width=180,
            value="BORC",
            options=[
                ft.dropdown.Option("BORC", "Alış Borcu Ekle"),
                ft.dropdown.Option("ODEME", "Ödeme Yap"),
            ],
        )

        # ── Arama ─────────────────────────────────────────────────────────
        self.txt_search = ft.TextField(
            label="Tedarikçi Ara...",
            prefix_icon=ft.Icons.SEARCH,
            width=260,
            on_change=lambda _: self._filter_table(),
        )

        # ── Tablo ─────────────────────────────────────────────────────────
        self.table = ft.DataTable(
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            border_radius=8,
            heading_row_color=ft.Colors.INDIGO_50,
            heading_row_height=40,
            data_row_min_height=44,
            column_spacing=16,
            columns=[
                ft.DataColumn(ft.Text("Ad", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Telefon", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Adres", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Borç (₺)", weight=ft.FontWeight.W_600),
                              numeric=True),
                ft.DataColumn(ft.Text("İşlemler", weight=ft.FontWeight.W_600)),
            ],
            rows=[],
        )

        self._all_rows = []

        # ── Layout ────────────────────────────────────────────────────────
        content = ft.Column(
            expand=True,
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                # Başlık
                ft.Row([
                    ft.Icon(ft.Icons.LOCAL_SHIPPING, color=ft.Colors.INDIGO_700, size=26),
                    ft.Text("Tedarikçi Yönetimi", size=22, weight=ft.FontWeight.BOLD,
                            color=ft.Colors.INDIGO_800),
                ], spacing=8),

                # Form kartı
                ft.Card(
                    elevation=2,
                    content=ft.Container(
                        padding=ft.padding.all(14),
                        content=ft.Column([
                            self.lbl_form_title,
                            ft.Row([self.txt_name, self.txt_phone], spacing=8),
                            ft.Row([self.txt_address], spacing=8),
                            ft.Row([self.btn_save, self.btn_cancel], spacing=8),
                        ], spacing=10),
                    ),
                ),

                # Borç / Ödeme kartı
                ft.Card(
                    elevation=2,
                    content=ft.Container(
                        padding=ft.padding.all(14),
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.CURRENCY_LIRA,
                                        color=ft.Colors.ORANGE_700, size=18),
                                ft.Text("Borç / Ödeme İşlemi", size=14,
                                        weight=ft.FontWeight.W_600,
                                        color=ft.Colors.ORANGE_800),
                            ], spacing=6),
                            ft.Row([self.dd_supplier, self.lbl_balance], spacing=10),
                            ft.Row([self.dd_move_type, self.txt_amount, self.txt_note], spacing=8),
                            ft.ElevatedButton(
                                "İşlemi Uygula",
                                icon=ft.Icons.CHECK_CIRCLE,
                                style=ft.ButtonStyle(
                                    bgcolor=ft.Colors.ORANGE_700,
                                    color=ft.Colors.WHITE,
                                ),
                                on_click=self._apply_move,
                            ),
                        ], spacing=10),
                    ),
                ),

                # Liste kartı
                ft.Card(
                    elevation=2,
                    content=ft.Container(
                        padding=ft.padding.all(14),
                        content=ft.Column([
                            ft.Row([
                                ft.Text("Tedarikçi Listesi", size=14,
                                        weight=ft.FontWeight.W_600,
                                        color=ft.Colors.INDIGO_700),
                                self.txt_search,
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Container(
                                content=self.table,
                                bgcolor=ft.Colors.WHITE,
                            ),
                        ], spacing=10),
                    ),
                ),
            ],
        )

        super().__init__(expand=True, padding=10, content=content)

    # ── Yardımcı ──────────────────────────────────────────────────────────

    def _safe_update(self):
        try:
            if self.page is None:
                return
            self.update()
        except Exception:
            pass

    def _snack(self, text: str, color=ft.Colors.INDIGO_700):
        try:
            self.page.snack_bar = ft.SnackBar(
                ft.Text(text, color=ft.Colors.WHITE),
                bgcolor=color, open=True,
            )
            self.page.update()
        except RuntimeError:
            pass

    def _to_float(self, v) -> float:
        try:
            return float((str(v) or "").replace(",", "."))
        except (ValueError, TypeError):
            return 0.0

    # ── Form ──────────────────────────────────────────────────────────────

    def _reset_form(self):
        self._editing_id = None
        self.txt_name.value = ""
        self.txt_phone.value = ""
        self.txt_address.value = ""
        self.lbl_form_title.value = "Yeni Tedarikçi"
        self.lbl_form_title.color = ft.Colors.INDIGO_700
        self.btn_save.text = "Kaydet"
        self.btn_cancel.visible = False
        self._safe_update()

    def _load_for_edit(self, row):
        self._editing_id = row[0]
        self.txt_name.value = row[1] or ""
        self.txt_phone.value = row[2] or ""
        self.txt_address.value = row[3] or ""
        self.lbl_form_title.value = f"Düzenle: {row[1]}"
        self.lbl_form_title.color = ft.Colors.ORANGE_700
        self.btn_save.text = "Güncelle"
        self.btn_cancel.visible = True
        # Sayfanın üstüne scroll et
        try:
            self.content.scroll_to(offset=0, duration=300)
        except Exception:
            pass
        self._safe_update()

    def _save_supplier(self, _e):
        name = (self.txt_name.value or "").strip()
        if not name:
            self._snack("Tedarikçi adı boş olamaz!", ft.Colors.RED_600)
            return
        phone = (self.txt_phone.value or "").strip()
        address = (self.txt_address.value or "").strip()
        if self._editing_id is not None:
            self.db.update_supplier(self._editing_id, name, phone, address)
            self._snack(f"'{name}' güncellendi")
        else:
            self.db.add_supplier(name, phone, address)
            self._snack(f"'{name}' eklendi")
        self._reset_form()
        self.refresh()

    # ── Borç / Ödeme ──────────────────────────────────────────────────────

    def _on_supplier_selected(self):
        sid = self._get_dd_id()
        if sid is None:
            self.lbl_balance.value = "Borç: —"
            self.lbl_balance.color = ft.Colors.BLUE_GREY_400
            self._safe_update()
            return
        rows = self.db.list_suppliers()
        row = next((r for r in rows if r[0] == sid), None)
        if row:
            debt = float(row[3] or 0)
            self.lbl_balance.value = f"Borç: {debt:,.2f} ₺"
            self.lbl_balance.color = ft.Colors.RED_700 if debt > 0 else ft.Colors.GREEN_600
            self._safe_update()

    def _get_dd_id(self):
        if not self.dd_supplier.value:
            return None
        try:
            return int(self.dd_supplier.value.split(" - ")[0])
        except (ValueError, IndexError):
            return None

    def _apply_move(self, _e):
        sid = self._get_dd_id()
        if sid is None:
            self._snack("Tedarikçi seçin!", ft.Colors.ORANGE_700)
            return
        amt = self._to_float(self.txt_amount.value)
        if amt <= 0:
            self._snack("Geçerli bir tutar girin!", ft.Colors.ORANGE_700)
            return
        move = self.dd_move_type.value or "BORC"
        if move == "BORC":
            self.db.add_supplier_debt(sid, amt)
            self._snack(f"{amt:,.2f} ₺ borç eklendi", ft.Colors.ORANGE_700)
        else:
            self.db.add_supplier_payment(sid, amt)
            self._snack(f"{amt:,.2f} ₺ ödeme kaydedildi", ft.Colors.GREEN_700)
        self.txt_amount.value = ""
        self.txt_note.value = ""
        self.refresh()
        self._on_supplier_selected()

    # ── Silme onayı ───────────────────────────────────────────────────────

    def _confirm_delete(self, row):
        def _do_delete(_e):
            dlg.open = False
            self.page.update()
            self.db.delete_supplier(row[0])
            self._snack(f"'{row[1]}' silindi")
            self.refresh()

        def _cancel(_e):
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Tedarikçiyi Sil"),
            content=ft.Text(
                f"'{row[1]}' tedarikçisini silmek istediğinizden emin misiniz?\n"
                f"Borç bakiyesi: {float(row[3] or 0):,.2f} ₺",
            ),
            actions=[
                ft.TextButton("İptal", on_click=_cancel),
                ft.ElevatedButton(
                    "Sil",
                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED_600, color=ft.Colors.WHITE),
                    on_click=_do_delete,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    # ── Tablo ─────────────────────────────────────────────────────────────

    def _filter_table(self):
        q = (self.txt_search.value or "").strip().lower()
        rows = [r for r in self._all_rows
                if not q or q in (r[1] or "").lower() or q in (r[2] or "").lower()]
        self._render_rows(rows)
        self._safe_update()

    def _render_rows(self, rows):
        def _make_row(r):
            debt = float(r[3] or 0)
            debt_color = ft.Colors.RED_700 if debt > 0 else ft.Colors.GREEN_600
            return ft.DataRow(cells=[
                ft.DataCell(ft.Text(r[1] or "", size=13)),
                ft.DataCell(ft.Text(r[2] or "", size=13)),
                ft.DataCell(ft.Text(r[4] or "", size=12, color=ft.Colors.BLUE_GREY_500)),
                ft.DataCell(
                    ft.Text(f"{debt:,.2f}", weight=ft.FontWeight.W_600,
                            color=debt_color, size=13)
                ),
                ft.DataCell(ft.Row([
                    ft.IconButton(
                        ft.Icons.EDIT, icon_color=ft.Colors.INDIGO_600,
                        tooltip="Düzenle", icon_size=18,
                        on_click=lambda _, row=r: self._load_for_edit(row),
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE, icon_color=ft.Colors.RED_400,
                        tooltip="Sil", icon_size=18,
                        on_click=lambda _, row=r: self._confirm_delete(row),
                    ),
                ], spacing=0)),
            ])
        self.table.rows = [_make_row(r) for r in rows]

    def refresh(self):
        # suppliers tablosunda address sütunu var mı kontrol et
        try:
            with self.db.conn() as conn:
                rows = conn.execute(
                    "SELECT id, name, phone, debt, address FROM suppliers ORDER BY name"
                ).fetchall()
        except Exception:
            rows = [(r[0], r[1], r[2], r[3], "") for r in self.db.list_suppliers()]
        self._all_rows = rows
        self.dd_supplier.options = [
            ft.dropdown.Option(f"{r[0]} - {r[1]}") for r in rows
        ]
        self._render_rows(rows)
        self._safe_update()
