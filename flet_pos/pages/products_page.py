import os
import shutil
import threading
import inspect
import asyncio
import flet as ft

from flet_pos.services.barcode import generate_ean13
from flet_pos.services.pricing import compute_prices


class ProductsPage(ft.Container):
    def __init__(self, db, media_dir: str, on_products_changed, file_picker=None):
        super().__init__(expand=True)
        self.db = db
        self.media_dir = media_dir
        self.on_products_changed = on_products_changed
        os.makedirs(self.media_dir, exist_ok=True)

        # file_picker parametresi artık kullanılmıyor — tkinter dialog kullanılıyor
        self.selected_image_src = ""
        self._editing_id: int | None = None
        self._products_cache = []
        self._products_cache_loaded = False

        self.txt_search = ft.TextField(
            label="Urun Ara",
            prefix_icon=ft.Icons.SEARCH,
            width=260,
            on_change=lambda _: self.refresh_table(),
        )

        self.lbl_form_title = ft.Text("Yeni Urun Ekle", size=16, weight=ft.FontWeight.W_600, color=ft.Colors.INDIGO_700)
        self.txt_name = ft.TextField(label="Urun Adi *", expand=True)
        self.txt_barcode = ft.TextField(label="Barkod *", width=220)
        self.txt_desc = ft.TextField(label="Aciklama", multiline=True, min_lines=2, max_lines=3, expand=True)
        self.txt_category = ft.TextField(label="Kategori", width=180)
        self.txt_sub_category = ft.TextField(label="Alt Kategori", width=180)
        self.dd_unit = ft.Dropdown(
            label="Birim",
            options=[ft.dropdown.Option("adet"), ft.dropdown.Option("kg"), ft.dropdown.Option("litre"), ft.dropdown.Option("paket")],
            value="adet",
            width=130,
        )
        self.sw_scale = ft.Switch(label="Terazi urunu", value=False)

        self.dd_supplier = ft.Dropdown(label="Tedarikci (Opsiyonel)", width=260, options=[])

        self.txt_buy = ft.TextField(label="Alis Fiyati", value="0", width=140)
        self.txt_sell_base = ft.TextField(label="Satis Fiyati", value="0", width=140)
        self.dd_vat_mode = ft.Dropdown(
            label="Satis Modu",
            options=[ft.dropdown.Option("INCL", "KDV Dahil"), ft.dropdown.Option("EXCL", "KDV Haric")],
            value="INCL",
            width=160,
        )
        self.txt_vat = ft.TextField(label="KDV %", value="20", width=110)
        self.lbl_excl = ft.Text("KDV Haric: 0.00", color=ft.Colors.BLUE_GREY_700)
        self.lbl_incl = ft.Text("KDV Dahil: 0.00", color=ft.Colors.GREEN_700, weight=ft.FontWeight.W_600)
        self.txt_stock = ft.TextField(label="Stok", value="0", width=120)
        self.txt_critical = ft.TextField(label="Kritik Stok", value="0", width=120)

        self.img_preview = ft.Image(
            src=None,
            width=160,
            height=120,
            fit=ft.BoxFit.CONTAIN,
            border_radius=10,
            error_content=ft.Container(
                bgcolor=ft.Colors.GREY_100,
                border_radius=10,
                width=160,
                height=120,
                content=ft.Column([
                    ft.Icon(ft.Icons.ADD_PHOTO_ALTERNATE, color=ft.Colors.GREY_400, size=36),
                    ft.Text("Resim yok", size=10, color=ft.Colors.GREY_500),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   alignment=ft.MainAxisAlignment.CENTER, spacing=4),
            ),
        )

        self.btn_save = ft.ElevatedButton(
            "Urun Kaydet",
            icon=ft.Icons.SAVE,
            style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_600, color=ft.Colors.WHITE),
            on_click=self._save_product,
        )
        self.btn_cancel_edit = ft.OutlinedButton(
            "Vazgec",
            icon=ft.Icons.CLOSE,
            visible=False,
            on_click=lambda _: self._reset_form(),
        )

        self.table = ft.DataTable(
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            heading_row_color=ft.Colors.INDIGO_50,
            column_spacing=12,
            columns=[
                ft.DataColumn(ft.Text("Resim", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Urun Adi", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Barkod", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Birim", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("KDV %", weight=ft.FontWeight.W_600), numeric=True),
                ft.DataColumn(ft.Text("Satis (KDV Dahil)", weight=ft.FontWeight.W_600), numeric=True),
                ft.DataColumn(ft.Text("Stok", weight=ft.FontWeight.W_600), numeric=True),
                ft.DataColumn(ft.Text("Islem", weight=ft.FontWeight.W_600)),
            ],
            rows=[],
        )

        self.dd_vat_mode.on_select = lambda _: self._refresh_price_labels()
        self.txt_sell_base.on_change = lambda _: self._refresh_price_labels()
        self.txt_vat.on_change = lambda _: self._refresh_price_labels()

        self.content = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=14,
            controls=[
                ft.Text("Urun Yonetimi", size=26, weight=ft.FontWeight.BOLD),
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    border_radius=14,
                    padding=16,
                    content=ft.Column(
                        spacing=12,
                        controls=[
                            ft.Row([self.lbl_form_title, self.btn_cancel_edit], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Column(
                                        col={"sm": 12, "md": 9},
                                        spacing=10,
                                        controls=[
                                            ft.ResponsiveRow(controls=[
                                                ft.Container(col={"sm": 12, "md": 7}, content=self.txt_name),
                                                ft.Container(col={"sm": 12, "md": 5}, content=self.txt_barcode),
                                            ]),
                                            self.txt_desc,
                                            ft.Row([self.txt_category, self.txt_sub_category, self.dd_unit, self.sw_scale], wrap=True),
                                            ft.Row([self.dd_supplier], wrap=True),
                                            ft.Row([self.txt_buy, self.txt_sell_base, self.dd_vat_mode, self.txt_vat, self.txt_stock, self.txt_critical], wrap=True),
                                            ft.Container(
                                                bgcolor=ft.Colors.INDIGO_50,
                                                border_radius=8,
                                                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                                                content=ft.Row([self.lbl_excl, self.lbl_incl], spacing=24),
                                            ),
                                            ft.Row(
                                                [
                                                    ft.OutlinedButton("Barkod Uret", icon=ft.Icons.QR_CODE, on_click=self._on_generate_barcode),
                                                    ft.OutlinedButton("Resim Sec", icon=ft.Icons.IMAGE, on_click=self._pick_image),
                                                    self.btn_save,
                                                    self.btn_cancel_edit,
                                                ],
                                                wrap=True,
                                            ),
                                        ],
                                    ),
                                    ft.Column(
                                        col={"sm": 12, "md": 3},
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                        controls=[
                                            ft.Text("Urun Gorseli", size=13, color=ft.Colors.BLUE_GREY_600),
                                            ft.Container(
                                                content=self.img_preview,
                                                bgcolor=ft.Colors.GREY_50,
                                                border_radius=12,
                                                padding=8,
                                                border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                                            ),
                                        ],
                                    ),
                                ]
                            ),
                        ],
                    ),
                ),
                ft.Row(
                    [
                        ft.Text("Urun Listesi", size=16, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_GREY_700),
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
            ],
        )

        self._refresh_price_labels()
        self.refresh_table()
        self._load_suppliers()

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

    def _run_ui_call(self, result):
        """Flet sürümüne göre sync/async UI çağrısını güvenle çalıştır."""
        if inspect.isawaitable(result):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(result)
            except RuntimeError:
                pass

    def _load_suppliers(self):
        suppliers = self.db.list_suppliers()
        self.dd_supplier.options = [ft.dropdown.Option("", "-- Tedarikci Yok --")] + [
            ft.dropdown.Option(str(s[0]), s[1]) for s in suppliers
        ]
        self._safe_update()

    def _pick_image(self, _e: ft.ControlEvent):
        """OS native dosya seçici — tkinter (FilePicker overlay sorunu yok)."""
        def _open_dialog():
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                path = filedialog.askopenfilename(
                    title="Ürün Resmi Seç",
                    filetypes=[
                        ("Resim Dosyaları", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"),
                        ("Tüm Dosyalar", "*.*"),
                    ],
                )
                root.destroy()
                if path:
                    self.selected_image_src = path
                    self.img_preview.src = path
                    self._safe_update()
            except Exception as ex:
                self._snack(f"Resim seçilemedi: {ex}")

        # Ana thread'i bloke etmemek için ayrı thread
        threading.Thread(target=_open_dialog, daemon=True).start()

    def _on_generate_barcode(self, _e: ft.ControlEvent):
        self.txt_barcode.value = generate_ean13("869")
        self._safe_update()

    def _to_float(self, value: str, default: float = 0.0) -> float:
        try:
            return float((value or "").replace(",", "."))
        except ValueError:
            return default

    def _refresh_price_labels(self):
        base = self._to_float(self.txt_sell_base.value, 0.0)
        vat = self._to_float(self.txt_vat.value, 20.0)
        mode = self.dd_vat_mode.value or "INCL"
        excl, incl = compute_prices(base, vat, mode)
        self.lbl_excl.value = f"KDV Haric: {excl:.2f}"
        self.lbl_incl.value = f"KDV Dahil: {incl:.2f}"
        self._safe_update()

    def _load_product_to_form(self, product_id: int):
        r = self.db.get_product_full(product_id)
        if not r:
            return
        # r: id, name, barcode, desc, cat, sub_cat, unit, buy, excl, incl, vat_rate, vat_mode,
        #    stock, critical, image_path, is_scale, supplier_id
        self._editing_id = r[0]
        self.txt_name.value = r[1] or ""
        self.txt_barcode.value = r[2] or ""
        self.txt_barcode.read_only = True
        self.txt_desc.value = r[3] or ""
        self.txt_category.value = r[4] or ""
        self.txt_sub_category.value = r[5] or ""
        self.dd_unit.value = r[6] or "adet"
        self.txt_buy.value = str(r[7] or 0)
        self.dd_vat_mode.value = r[11] or "INCL"
        self.txt_vat.value = str(r[10] or 20)
        incl_price = float(r[9] or 0)
        excl_price = float(r[8] or 0)
        self.txt_sell_base.value = str(incl_price if (r[11] or "INCL") == "INCL" else excl_price)
        self.txt_stock.value = str(r[12] or 0)
        self.txt_critical.value = str(r[13] or 0)
        self.selected_image_src = r[14] or ""
        self.img_preview.src = r[14] or None
        self.sw_scale.value = bool(r[15])
        supplier_id = r[16]
        self.dd_supplier.value = str(supplier_id) if supplier_id else ""
        self.lbl_form_title.value = f"Urunu Duzenle: {r[1]}"
        self.lbl_form_title.color = ft.Colors.ORANGE_700
        self.btn_cancel_edit.visible = True
        self.btn_save.text = "Degisiklikleri Kaydet"
        self._refresh_price_labels()
        self._run_ui_call(self.content.scroll_to(offset=0, duration=300))
        self._safe_update()

    def _reset_form(self):
        self._editing_id = None
        self.txt_name.value = ""
        self.txt_barcode.value = ""
        self.txt_barcode.read_only = False
        self.txt_desc.value = ""
        self.txt_category.value = ""
        self.txt_sub_category.value = ""
        self.dd_unit.value = "adet"
        self.txt_buy.value = "0"
        self.txt_sell_base.value = "0"
        self.dd_vat_mode.value = "INCL"
        self.txt_vat.value = "20"
        self.txt_stock.value = "0"
        self.txt_critical.value = "0"
        self.selected_image_src = ""
        self.img_preview.src = None
        self.sw_scale.value = False
        self.dd_supplier.value = ""
        self.lbl_form_title.value = "Yeni Urun Ekle"
        self.lbl_form_title.color = ft.Colors.INDIGO_700
        self.btn_cancel_edit.visible = False
        self.btn_save.text = "Urun Kaydet"
        self._refresh_price_labels()
        self._safe_update()

    def start_add_with_barcode(self, barcode: str):
        """POS'tan gelen bilinmeyen barkodla hızlı ürün ekleme formunu aç."""
        self._reset_form()
        self.txt_barcode.value = (barcode or "").strip()
        try:
            self._run_ui_call(self.content.scroll_to(offset=0, duration=250))
        except Exception:
            pass
        self._run_ui_call(self.txt_name.focus())
        self._safe_update()

    def _confirm_delete(self, product_id: int, product_name: str):
        def do_delete(_e):
            self.db.delete_product(product_id)
            dlg.open = False
            self.page.update()
            self.invalidate_cache()
            self.refresh_table()
            self.on_products_changed()
            self._snack(f"{product_name} silindi")

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Urunu Sil"),
            content=ft.Text(f'"{product_name}" urununu silmek istediginize emin misiniz?'),
            actions=[
                ft.TextButton("Vazgec", on_click=lambda _: self._close_dlg(dlg)),
                ft.ElevatedButton("Evet, Sil", style=ft.ButtonStyle(bgcolor=ft.Colors.RED_600, color=ft.Colors.WHITE), on_click=do_delete),
            ],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _close_dlg(self, dlg):
        dlg.open = False
        self.page.update()

    def _save_product(self, _e: ft.ControlEvent):
        if not self.txt_name.value or not self.txt_barcode.value:
            self._snack("Urun adi ve barkod zorunlu")
            return

        base = self._to_float(self.txt_sell_base.value, 0.0)
        vat = self._to_float(self.txt_vat.value, 20.0)
        excl, incl = compute_prices(base, vat, self.dd_vat_mode.value or "INCL")

        image_path = self.selected_image_src or ""
        if self.selected_image_src and os.path.exists(self.selected_image_src):
            ext = os.path.splitext(self.selected_image_src)[1] or ".png"
            target = os.path.join(self.media_dir, f"{self.txt_barcode.value}{ext}")
            if os.path.abspath(target) != os.path.abspath(self.selected_image_src):
                shutil.copy2(self.selected_image_src, target)
            image_path = target

        supplier_id: int | None = None
        if self.dd_supplier.value:
            try:
                supplier_id = int(self.dd_supplier.value)
            except ValueError:
                supplier_id = None

        is_new = self.db.upsert_product(
            barcode=self.txt_barcode.value.strip(),
            name=self.txt_name.value.strip(),
            description=(self.txt_desc.value or "").strip(),
            category=(self.txt_category.value or "").strip(),
            sub_category=(self.txt_sub_category.value or "").strip(),
            unit=self.dd_unit.value or "adet",
            buy_price=self._to_float(self.txt_buy.value, 0),
            sell_price_excl_vat=excl,
            sell_price_incl_vat=incl,
            vat_rate=vat,
            vat_mode=self.dd_vat_mode.value or "INCL",
            stock=self._to_float(self.txt_stock.value, 0),
            critical_stock=self._to_float(self.txt_critical.value, 0),
            image_path=image_path,
            is_scale_product=self.sw_scale.value,
            supplier_id=supplier_id,
        )
        self._reset_form()
        self.invalidate_cache()
        self.refresh_table()
        self.on_products_changed()
        self._snack("Urun eklendi" if is_new else "Urun guncellendi")

    def invalidate_cache(self):
        self._products_cache = []
        self._products_cache_loaded = False

    def refresh(self):
        self.refresh_table(force_reload=True)

    def _load_products(self, force_reload: bool = False):
        if force_reload or not self._products_cache_loaded:
            self._products_cache = list(self.db.list_products())
            self._products_cache_loaded = True
        return self._products_cache

    def refresh_table(self, force_reload: bool = False):
        search = (self.txt_search.value or "").strip().lower() if hasattr(self, "txt_search") else ""
        rows = self._load_products(force_reload)
        if search:
            rows = [r for r in rows if search in (r[1] or "").lower() or search in (r[2] or "").lower()]

        # list_products: id(0), name(1), barcode(2), unit(3), sell_price_incl_vat(4),
        #                vat_rate(5), stock(6), image_path(7), is_scale_product(8)
        self.table.rows = []
        for r in rows:
            pid = r[0]
            stock = float(r[6] or 0)
            stok_color = ft.Colors.RED_700 if stock <= 0 else (ft.Colors.ORANGE_700 if stock < 5 else ft.Colors.GREEN_700)
            image_path = r[7]
            thumb = (
                ft.Image(src=image_path, width=52, height=52, fit=ft.BoxFit.COVER, border_radius=6)
                if image_path and os.path.exists(image_path)
                else ft.Container(
                    width=52, height=52,
                    bgcolor=ft.Colors.GREY_100,
                    border_radius=6,
                    content=ft.Icon(ft.Icons.SHOPPING_BAG, size=30, color=ft.Colors.GREY_400),
                )
            )
            self.table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(thumb),
                        ft.DataCell(ft.Text(r[1], weight=ft.FontWeight.W_500)),
                        ft.DataCell(ft.Text(r[2] or "")),
                        ft.DataCell(ft.Text(r[3] or "")),
                        ft.DataCell(ft.Text(f"%{float(r[5]):.0f}")),
                        ft.DataCell(ft.Text(f"{float(r[4]):.2f} TL")),
                        ft.DataCell(ft.Text(f"{stock:.2f}", color=stok_color, weight=ft.FontWeight.W_600)),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(ft.Icons.EDIT, icon_color=ft.Colors.BLUE_700, tooltip="Duzenle", on_click=lambda _, _id=pid: self._load_product_to_form(_id)),
                                    ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_600, tooltip="Sil", on_click=lambda _, _id=pid, _n=r[1]: self._confirm_delete(_id, _n)),
                                ],
                                spacing=0,
                            )
                        ),
                    ]
                )
            )
        self._safe_update()
