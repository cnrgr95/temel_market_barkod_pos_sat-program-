import sqlite3
import flet as ft


class UsersPage(ft.Container):
    def __init__(self, db):
        self.db = db
        self._editing_id: int | None = None

        self.lbl_form_title = ft.Text("Yeni Kullanici Ekle", size=16, weight=ft.FontWeight.W_600, color=ft.Colors.INDIGO_700)
        self.txt_username = ft.TextField(label="Kullanici Adi *", expand=True)
        self.txt_password = ft.TextField(
            label="Sifre (bos birakma)",
            password=True,
            can_reveal_password=True,
            expand=True,
        )
        self.dd_role = ft.Dropdown(
            label="Rol",
            value="KASIYER",
            width=180,
            options=[
                ft.dropdown.Option("ADMIN", "Admin (Tam Yetki)"),
                ft.dropdown.Option("KASIYER", "Kasiyer"),
                ft.dropdown.Option("YONETICI", "Yonetici"),
            ],
        )
        self.dd_role.on_select = lambda _: self._on_role_changed()

        self.sw_discount = ft.Switch(label="Indirim Uygulama", value=False)
        self.sw_price = ft.Switch(label="Fiyat Degistirme", value=False)
        self.sw_return = ft.Switch(label="Iade Islemi", value=False)
        self.sw_reports = ft.Switch(label="Rapor Goruntuleme", value=False)
        self.sw_sales_history = ft.Switch(label="Satis Gecmisi", value=False)
        self.sw_products = ft.Switch(label="Urunler", value=False)
        self.sw_stock = ft.Switch(label="Stok", value=False)
        self.sw_customers = ft.Switch(label="Cari Hesap", value=False)
        self.sw_suppliers = ft.Switch(label="Tedarikciler", value=False)
        self.sw_cash = ft.Switch(label="Kasa", value=False)
        self.sw_users = ft.Switch(label="Kullanicilar", value=False)
        self.sw_backup = ft.Switch(label="Yedekleme", value=False)
        self.sw_hardware = ft.Switch(label="Donanim", value=False)

        self.btn_save = ft.ElevatedButton(
            "Kullanici Ekle",
            icon=ft.Icons.PERSON_ADD,
            style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_600, color=ft.Colors.WHITE),
            on_click=self._save_user,
        )
        self.btn_cancel = ft.OutlinedButton(
            "Vazgec",
            icon=ft.Icons.CLOSE,
            visible=False,
            on_click=lambda _: self._reset_form(),
        )

        self.table = ft.DataTable(
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            heading_row_color=ft.Colors.INDIGO_50,
            column_spacing=20,
            columns=[
                ft.DataColumn(ft.Text("Kullanici Adi", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Rol", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Indirim", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Fiyat", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Iade", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Rapor", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Modul Yetkileri", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Islem", weight=ft.FontWeight.W_600)),
            ],
            rows=[],
        )

        content = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=14,
            controls=[
                ft.Text("Kullanici ve Yetki Yonetimi", size=26, weight=ft.FontWeight.BOLD),
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    border_radius=14,
                    padding=16,
                    content=ft.Column(
                        spacing=12,
                        controls=[
                            ft.Row([self.lbl_form_title, self.btn_cancel], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Container(col={"sm": 12, "md": 4}, content=self.txt_username),
                                    ft.Container(col={"sm": 12, "md": 4}, content=self.txt_password),
                                    ft.Container(col={"sm": 12, "md": 4}, content=self.dd_role),
                                ]
                            ),
                            ft.Container(
                                bgcolor=ft.Colors.INDIGO_50,
                                border_radius=10,
                                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                                content=ft.Column(
                                    controls=[
                                        ft.Text("Yetkiler", size=13, weight=ft.FontWeight.W_600, color=ft.Colors.INDIGO_800),
                                        ft.Row([self.sw_discount, self.sw_price, self.sw_return, self.sw_reports, self.sw_sales_history], wrap=True),
                                        ft.Row([self.sw_products, self.sw_stock, self.sw_customers, self.sw_suppliers], wrap=True),
                                        ft.Row([self.sw_cash, self.sw_users, self.sw_backup, self.sw_hardware], wrap=True),
                                    ],
                                    spacing=4,
                                ),
                            ),
                            ft.Row([self.btn_save, self.btn_cancel], spacing=10),
                        ],
                    ),
                ),
                ft.Text("Kullanici Listesi", size=16, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_GREY_700),
                ft.Container(
                    content=ft.Column([self.table], scroll=ft.ScrollMode.AUTO),
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    padding=10,
                ),
            ],
        )
        super().__init__(expand=True, content=content)

    def _safe_update(self):
        if self.page is None:
            return
        try:
            self.update()
        except Exception:
            pass

    def _on_role_changed(self):
        role = self.dd_role.value or "KASIYER"
        all_switches = [
            self.sw_discount, self.sw_price, self.sw_return, self.sw_reports, self.sw_sales_history,
            self.sw_products, self.sw_stock, self.sw_customers, self.sw_suppliers,
            self.sw_cash, self.sw_users, self.sw_backup, self.sw_hardware,
        ]
        if role == "ADMIN":
            for sw in all_switches:
                sw.value = True
        elif role == "YONETICI":
            # Yönetici: fiyat, stok, ürün, müşteri, tedarikçi, kasa, yedek dahil; kullanıcı yönetimi hariç
            self.sw_discount.value = True
            self.sw_price.value = True
            self.sw_return.value = True
            self.sw_reports.value = True
            self.sw_sales_history.value = True
            self.sw_products.value = True
            self.sw_stock.value = True
            self.sw_customers.value = True
            self.sw_suppliers.value = True
            self.sw_cash.value = True
            self.sw_users.value = False
            self.sw_backup.value = True
            self.sw_hardware.value = False
        elif role == "KASIYER":
            # Kasiyer: sadece indirim, iade, müşteri görme, satış geçmişi
            self.sw_discount.value = True
            self.sw_price.value = False
            self.sw_return.value = True
            self.sw_reports.value = False
            self.sw_sales_history.value = True
            self.sw_products.value = False
            self.sw_stock.value = False
            self.sw_customers.value = True
            self.sw_suppliers.value = False
            self.sw_cash.value = False
            self.sw_users.value = False
            self.sw_backup.value = False
            self.sw_hardware.value = False
        self._safe_update()

    def _snack(self, text: str):
        try:
            self.page.snack_bar = ft.SnackBar(ft.Text(text), open=True)
            self.page.update()
        except RuntimeError:
            pass

    def _reset_form(self):
        self._editing_id = None
        self.txt_username.value = ""
        self.txt_username.read_only = False
        self.txt_password.value = ""
        self.txt_password.label = "Sifre *"
        self.dd_role.value = "KASIYER"
        self.sw_discount.value = False
        self.sw_price.value = False
        self.sw_return.value = False
        self.sw_reports.value = False
        self.sw_sales_history.value = False
        self.sw_products.value = False
        self.sw_stock.value = False
        self.sw_customers.value = False
        self.sw_suppliers.value = False
        self.sw_cash.value = False
        self.sw_users.value = False
        self.sw_backup.value = False
        self.sw_hardware.value = False
        self.lbl_form_title.value = "Yeni Kullanici Ekle"
        self.lbl_form_title.color = ft.Colors.INDIGO_700
        self.btn_save.text = "Kullanici Ekle"
        self.btn_save.icon = ft.Icons.PERSON_ADD
        self.btn_cancel.visible = False
        self._safe_update()

    def _load_user_to_form(self, row):
        uid, username, role, can_discount, can_price, can_return, can_reports, can_products, can_stock, can_customers, can_suppliers, can_cash, can_users, can_backup, can_hardware, can_sales_history = row
        self._editing_id = uid
        self.txt_username.value = username
        self.txt_username.read_only = True
        self.txt_password.value = ""
        self.txt_password.label = "Yeni Sifre (bos birakabilirsiniz)"
        self.dd_role.value = role
        self.sw_discount.value = bool(can_discount)
        self.sw_price.value = bool(can_price)
        self.sw_return.value = bool(can_return)
        self.sw_reports.value = bool(can_reports)
        self.sw_products.value = bool(can_products)
        self.sw_stock.value = bool(can_stock)
        self.sw_customers.value = bool(can_customers)
        self.sw_suppliers.value = bool(can_suppliers)
        self.sw_cash.value = bool(can_cash)
        self.sw_users.value = bool(can_users)
        self.sw_backup.value = bool(can_backup)
        self.sw_hardware.value = bool(can_hardware)
        self.sw_sales_history.value = bool(can_sales_history)
        self.lbl_form_title.value = f"Kullanici Duzenle: {username}"
        self.lbl_form_title.color = ft.Colors.ORANGE_700
        self.btn_save.text = "Degisiklikleri Kaydet"
        self.btn_save.icon = ft.Icons.SAVE
        self.btn_cancel.visible = True
        self.content.scroll_to(offset=0, duration=300)
        self._safe_update()

    def _save_user(self, _e: ft.ControlEvent):
        username = (self.txt_username.value or "").strip()
        password = (self.txt_password.value or "").strip()
        role = self.dd_role.value or "KASIYER"

        try:
            if self._editing_id is not None:
                self.db.update_user(
                    self._editing_id,
                    password=password,
                    role=role,
                    can_discount=self.sw_discount.value,
                    can_price_change=self.sw_price.value,
                    can_return=self.sw_return.value,
                    can_reports=self.sw_reports.value,
                    can_products=self.sw_products.value,
                    can_stock=self.sw_stock.value,
                    can_customers=self.sw_customers.value,
                    can_suppliers=self.sw_suppliers.value,
                    can_cash=self.sw_cash.value,
                    can_users=self.sw_users.value,
                    can_backup=self.sw_backup.value,
                    can_hardware=self.sw_hardware.value,
                    can_sales_history=self.sw_sales_history.value,
                )
                self._snack(f"{username} guncellendi")
            else:
                if not username or not password:
                    self._snack("Kullanici adi ve sifre zorunlu")
                    return
                self.db.add_user(
                    username=username,
                    password=password,
                    role=role,
                    can_discount=self.sw_discount.value,
                    can_price_change=self.sw_price.value,
                    can_return=self.sw_return.value,
                    can_reports=self.sw_reports.value,
                    can_products=self.sw_products.value,
                    can_stock=self.sw_stock.value,
                    can_customers=self.sw_customers.value,
                    can_suppliers=self.sw_suppliers.value,
                    can_cash=self.sw_cash.value,
                    can_users=self.sw_users.value,
                    can_backup=self.sw_backup.value,
                    can_hardware=self.sw_hardware.value,
                    can_sales_history=self.sw_sales_history.value,
                )
                self._snack(f"{username} eklendi")
        except sqlite3.IntegrityError:
            self._snack("Bu kullanici adi zaten mevcut")
            return

        self._reset_form()
        self.refresh()
        self._safe_update()

    def _confirm_delete(self, user_id: int, username: str):
        def do_delete(_e):
            try:
                self.db.delete_user(user_id)
                self._snack(f"{username} silindi")
            except ValueError as ex:
                self._snack(str(ex))
            dlg.open = False
            self.page.update()
            self.refresh()
            self._safe_update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Kullanici Sil"),
            content=ft.Text(f'"{username}" kullanicisini silmek istediginize emin misiniz?'),
            actions=[
                ft.TextButton("Vazgec", on_click=lambda _: self._close_dlg(dlg)),
                ft.ElevatedButton(
                    "Evet, Sil",
                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED_600, color=ft.Colors.WHITE),
                    on_click=do_delete,
                ),
            ],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _close_dlg(self, dlg):
        dlg.open = False
        self.page.update()

    def refresh(self):
        rows = self.db.list_users()
        self.table.rows = []
        for r in rows:
            uid, username, role, can_d, can_p, can_r, can_rep, can_products, can_stock, can_customers, can_suppliers, can_cash, can_users, can_backup, can_hardware, can_sales_history = r

            def _yn(v):
                return ft.Text("Evet", color=ft.Colors.GREEN_700, weight=ft.FontWeight.W_500) if v else ft.Text("Hayir", color=ft.Colors.BLUE_GREY_400)

            role_colors = {"ADMIN": ft.Colors.INDIGO_700, "YONETICI": ft.Colors.PURPLE_700, "KASIYER": ft.Colors.TEAL_700}
            role_color = role_colors.get(role, ft.Colors.BLUE_GREY_700)

            modules = []
            if can_products:
                modules.append("Urun")
            if can_stock:
                modules.append("Stok")
            if can_customers:
                modules.append("Cari")
            if can_suppliers:
                modules.append("Tedarik")
            if can_cash:
                modules.append("Kasa")
            if can_users:
                modules.append("Kullanici")
            if can_backup:
                modules.append("Yedek")
            if can_hardware:
                modules.append("Donanim")
            if can_sales_history:
                modules.append("SatisGecmisi")
            modules_text = ", ".join(modules) if modules else "-"

            self.table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(username, weight=ft.FontWeight.W_600)),
                        ft.DataCell(ft.Text(role, color=role_color, weight=ft.FontWeight.W_600)),
                        ft.DataCell(_yn(can_d)),
                        ft.DataCell(_yn(can_p)),
                        ft.DataCell(_yn(can_r)),
                        ft.DataCell(_yn(can_rep)),
                        ft.DataCell(ft.Text(modules_text, size=11)),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        ft.Icons.EDIT,
                                        icon_color=ft.Colors.BLUE_700,
                                        tooltip="Duzenle",
                                        on_click=lambda _, row=r: self._load_user_to_form(row),
                                    ),
                                    ft.IconButton(
                                        ft.Icons.DELETE,
                                        icon_color=ft.Colors.RED_600,
                                        tooltip="Sil",
                                        on_click=lambda _, _id=uid, _n=username: self._confirm_delete(_id, _n),
                                    ),
                                ],
                                spacing=0,
                            )
                        ),
                    ]
                )
            )
