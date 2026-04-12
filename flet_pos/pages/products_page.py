import asyncio
import inspect
import json
import os
import shutil
import threading

import flet as ft

from flet_pos.services.barcode import generate_ean13
from flet_pos.services.pricing import compute_prices


class ProductsPage(ft.Container):
    def __init__(self, db, media_dir: str, on_products_changed, file_picker=None):
        self.db = db
        self.media_dir = media_dir
        self.on_products_changed = on_products_changed
        os.makedirs(self.media_dir, exist_ok=True)

        self.selected_image_src = ""
        self._editing_id: int | None = None
        self._quick_product_ids = self._load_quick_product_ids()

        # --- Arama ---
        self.txt_search = ft.TextField(
            label="Urun Ara",
            prefix_icon=ft.Icons.SEARCH,
            width=300,
            on_change=lambda _: self._schedule_refresh_table(),
        )
        self.dd_filter_group = ft.Dropdown(
            label="Grup Filtrele",
            width=200,
            options=[ft.dropdown.Option("", "Tum Gruplar")],
            value="",
            on_select=lambda _: self.refresh_table(),
        )

        # --- Hizli satis ---
        self.dd_quick_add = ft.Dropdown(label="Hizli listeye urun ekle", expand=True, options=[])
        self.btn_quick_add = ft.ElevatedButton(
            "Listeye Ekle",
            icon=ft.Icons.ADD,
            style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_600, color=ft.Colors.WHITE),
            on_click=lambda _: self._add_selected_quick_product(),
        )
        self.lbl_quick_summary = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_600)
        self.quick_selection_list = ft.Column(spacing=8)

        # --- Form alanlari ---
        self.lbl_form_title = ft.Text("Yeni Urun Ekle", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.INDIGO_800)
        self.txt_name = ft.TextField(label="Urun Adi *", expand=True)
        self.txt_barcode = ft.TextField(label="Barkod *", width=220)
        self.txt_desc = ft.TextField(label="Aciklama", multiline=True, min_lines=2, max_lines=4)
        self.dd_category = ft.Dropdown(
            label="Kategori / Grup", width=200,
            options=[ft.dropdown.Option("", "— Sec —")],
            on_select=lambda _: self._on_category_changed(),
        )
        self.dd_sub_category = ft.Dropdown(
            label="Alt Kategori", width=200,
            options=[ft.dropdown.Option("", "— Sec —")],
        )
        self.dd_unit = ft.Dropdown(
            label="Birim",
            options=[
                ft.dropdown.Option("adet"),
                ft.dropdown.Option("kg"),
                ft.dropdown.Option("litre"),
                ft.dropdown.Option("paket"),
            ],
            value="adet",
            width=140,
        )
        self.sw_scale = ft.Switch(label="Terazi urunu", value=False)
        self.dd_supplier = ft.Dropdown(label="Tedarikci", width=260, options=[])
        self.txt_buy = ft.TextField(label="Alis Fiyati", value="0", width=140)
        self.txt_sell_base = ft.TextField(label="Satis Fiyati", value="0", width=140)
        self.dd_vat_mode = ft.Dropdown(
            label="Satis Modu",
            options=[ft.dropdown.Option("INCL", "KDV Dahil"), ft.dropdown.Option("EXCL", "KDV Haric")],
            value="INCL",
            width=170,
        )
        self.txt_vat = ft.TextField(label="KDV %", value="20", width=110)
        self.lbl_excl = ft.Text("KDV Haric: 0.00", color=ft.Colors.BLUE_GREY_700)
        self.lbl_incl = ft.Text("KDV Dahil: 0.00", color=ft.Colors.GREEN_700, weight=ft.FontWeight.W_600)
        self.txt_stock = ft.TextField(label="Stok", value="0", width=120)
        self.txt_critical = ft.TextField(label="Kritik Stok", value="0", width=120)

        self.img_preview = ft.Image(
            src=None,
            width=180,
            height=140,
            fit=ft.BoxFit.CONTAIN,
            border_radius=10,
            error_content=ft.Container(
                width=180, height=140,
                bgcolor=ft.Colors.GREY_100, border_radius=10,
                alignment=ft.Alignment(0, 0),
                content=ft.Text("Resim yok", color=ft.Colors.GREY_500),
            ),
        )

        self.btn_save = ft.ElevatedButton(
            "Urun Kaydet",
            icon=ft.Icons.SAVE,
            style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
            on_click=self._save_product,
        )
        self.btn_cancel_edit = ft.OutlinedButton(
            "Vazgec",
            icon=ft.Icons.CLOSE,
            visible=False,
            on_click=lambda _: self._reset_form(),
        )

        self._table_page_index = 0
        self._table_page_size = 100
        self._table_total = 0
        self._table_query_key = ("", "")
        self._search_timer = None
        self._show_list_images = True
        self._quick_search_timer = None
        self.lbl_page_info = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_600)
        self.btn_page_prev = ft.IconButton(
            ft.Icons.ARROW_BACK,
            tooltip="Onceki sayfa",
            on_click=lambda _: self._goto_prev_page(),
        )
        self.btn_page_next = ft.IconButton(
            ft.Icons.ARROW_FORWARD,
            tooltip="Sonraki sayfa",
            on_click=lambda _: self._goto_next_page(),
        )

        self.products_list = ft.Column(spacing=6)

        self.dd_vat_mode.on_select = lambda _: self._refresh_price_labels()
        self.txt_sell_base.on_change = lambda _: self._refresh_price_labels()
        self.txt_vat.on_change = lambda _: self._refresh_price_labels()

        # --- Toplu fiyat degistirme ---
        self.dd_bulk_scope = ft.Dropdown(
            label="Kapsam",
            value="ALL",
            width=200,
            options=[
                ft.dropdown.Option("ALL", "Tum Urunler"),
                ft.dropdown.Option("GROUP", "Gruba Gore"),
                ft.dropdown.Option("CATEGORY", "Kategoriye Gore"),
            ],
            on_select=lambda _: self._on_bulk_scope_changed(),
        )
        self.dd_bulk_group = ft.Dropdown(
            label="Grup", width=200, options=[], visible=False,
            on_select=lambda _: self._on_bulk_group_changed()
        )
        self.dd_bulk_category = ft.Dropdown(label="Alt Kategori", width=200, options=[], visible=False)
        self.dd_bulk_type = ft.Dropdown(
            label="Degisim Tipi",
            value="PERCENT",
            width=180,
            options=[
                ft.dropdown.Option("PERCENT", "Yuzde (%)"),
                ft.dropdown.Option("FIXED", "Sabit Tutar (TL)"),
            ],
        )
        self.dd_bulk_direction = ft.Dropdown(
            label="Yon",
            value="INCREASE",
            width=160,
            options=[
                ft.dropdown.Option("INCREASE", "Artir (+)"),
                ft.dropdown.Option("DECREASE", "Azalt (-)"),
            ],
        )
        self.txt_bulk_value = ft.TextField(label="Deger", value="0", width=130)
        self.lbl_bulk_result = ft.Text("", size=13, color=ft.Colors.GREEN_700)
        self.lbl_bulk_preview_status = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_600)
        self.bulk_preview_table_col = ft.Column(spacing=4)

        # --- Kategori / Grup yonetimi ---
        self.txt_group_name = ft.TextField(label="Grup Adi *", expand=True)
        self.txt_group_note = ft.TextField(label="Aciklama", expand=True)
        self._editing_group_name = ""
        self.groups_list = ft.Column(spacing=6)

        self.txt_cat_group = ft.Dropdown(label="Ait Oldugu Grup", expand=True, options=[])
        self.txt_cat_name = ft.TextField(label="Kategori Adi *", expand=True)
        self.txt_cat_note = ft.TextField(label="Aciklama", expand=True)
        self._editing_cat_key: tuple[str, str] = ("", "")
        self.cats_list = ft.Column(spacing=6)

        self.txt_quick_add_search = ft.TextField(
            label="Urun ara",
            expand=True,
            prefix_icon=ft.Icons.SEARCH,
            on_change=lambda _: self._schedule_quick_add_refresh(),
        )

        # --- Tab yapisi (Flet 0.84: TabBar + TabBarView + Tabs controller) ---
        _tab_contents = [
            ft.Container(
                expand=True,
                content=ft.Column(
                    expand=True, scroll=ft.ScrollMode.AUTO, spacing=12,
                    controls=[
                        self._build_form_card(),
                        self._build_products_card(),
                    ],
                ),
            ),
            ft.Container(
                expand=True,
                content=ft.Column(
                    expand=True, scroll=ft.ScrollMode.AUTO, spacing=12,
                    controls=[self._build_quick_list_card()],
                ),
            ),
            ft.Container(
                expand=True,
                content=ft.Column(
                    expand=True, scroll=ft.ScrollMode.AUTO, spacing=12,
                    controls=[self._build_bulk_price_card()],
                ),
            ),
            ft.Container(
                expand=True,
                content=ft.Column(
                    expand=True, scroll=ft.ScrollMode.AUTO, spacing=12,
                    controls=[self._build_taxonomy_card()],
                ),
            ),
        ]
        self._tabs = ft.Tabs(
            selected_index=0,
            length=4,
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    ft.TabBar(tabs=[
                        ft.Tab(label="Urun Listesi", icon=ft.Icons.INVENTORY_2),
                        ft.Tab(label="Hizli Satis Listesi", icon=ft.Icons.STAR),
                        ft.Tab(label="Toplu Fiyat Degistir", icon=ft.Icons.PRICE_CHANGE),
                        ft.Tab(label="Kategori / Grup Yonetimi", icon=ft.Icons.CATEGORY),
                    ]),
                    ft.TabBarView(controls=_tab_contents, expand=True),
                ],
            ),
        )

        super().__init__(expand=True, content=self._tabs)

        self._scanner_buffer = ""
        self._last_key_time = 0

        self._refresh_price_labels()
        # data loading handled by app.py _refresh_page_data on first navigation

    # ── Kart insa ─────────────────────────────────────────────────────────────

    def _build_quick_list_card(self):
        return ft.Container(
            bgcolor=ft.Colors.WHITE,
            border_radius=14,
            padding=16,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Text("Hizli Satis Listesi", size=17, weight=ft.FontWeight.W_700, color=ft.Colors.INDIGO_800),
                    ft.Row([self.txt_quick_add_search], spacing=10),
                    ft.Row([ft.Container(expand=True, content=self.dd_quick_add), self.btn_quick_add], spacing=10),
                    self.lbl_quick_summary,
                    self.quick_selection_list,
                ],
            ),
        )

    def _build_form_card(self):
        return ft.Container(
            bgcolor=ft.Colors.WHITE,
            border_radius=14,
            padding=16,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Row([self.lbl_form_title, self.btn_cancel_edit], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([ft.Container(expand=True, content=self.txt_name),
                            ft.Container(width=230, content=self.txt_barcode)], spacing=10),
                    self.txt_desc,
                    ft.Row([self.dd_category, self.dd_sub_category, self.dd_unit, self.sw_scale], spacing=10),
                    ft.Row([self.dd_supplier], wrap=True),
                    ft.Row([self.txt_buy, self.txt_sell_base, self.dd_vat_mode, self.txt_vat,
                            self.txt_stock, self.txt_critical], wrap=True, spacing=10),
                    ft.Container(
                        bgcolor=ft.Colors.INDIGO_50, border_radius=10,
                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                        content=ft.Row([self.lbl_excl, self.lbl_incl], wrap=True, spacing=24),
                    ),
                    ft.Row([
                        ft.Container(
                            bgcolor=ft.Colors.GREY_50, border_radius=12,
                            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                            padding=8,
                            content=self.img_preview,
                        ),
                        ft.Column([
                            ft.OutlinedButton("Barkod Uret", icon=ft.Icons.QR_CODE, on_click=self._on_generate_barcode),
                            ft.OutlinedButton("Resim Sec", icon=ft.Icons.IMAGE, on_click=self._pick_image),
                            self.btn_save,
                            self.btn_cancel_edit,
                        ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.START),
                    ], wrap=True, spacing=16, vertical_alignment=ft.CrossAxisAlignment.START),
                ],
            ),
        )

    def _build_products_card(self):
        return ft.Container(
            bgcolor=ft.Colors.WHITE,
            border_radius=14,
            padding=16,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Row([
                        ft.Text("Urun Listesi", size=17, weight=ft.FontWeight.W_700, color=ft.Colors.INDIGO_800),
                        self.txt_search,
                        self.dd_filter_group,
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=8),
                    ft.Row(
                        [self.btn_page_prev, self.lbl_page_info, self.btn_page_next],
                        alignment=ft.MainAxisAlignment.END,
                        spacing=6,
                    ),
                    self.products_list,
                ],
            ),
        )

    def handle_keyboard_event(self, e: ft.KeyboardEvent) -> bool:
        """Global barkod okuyucu dinleyicisi (sayfa aktifken tum tuslari yakalar)."""
        import time
        now = time.time()
        # 100ms'den uzun sürdüyse beyni sıfırla (tarayıcılar genelde 10-30ms arası gönderir)
        if now - self._last_key_time > 0.1:
            self._scanner_buffer = ""
        
        self._last_key_time = now
        
        # Enter okunduysa ve bufferda en az 3 karakter varsa barkod kabul et
        if e.key == "Enter":
            if len(self._scanner_buffer) >= 3:
                self.txt_barcode.value = self._scanner_buffer
                self._scanner_buffer = ""
                self._safe_update()
                # Sekmeyi Ekle formuna alabiliriz
                if self._tabs.selected_index != 0:
                    self._tabs.selected_index = 0
                    self._safe_update()
                return True
            else:
                self._scanner_buffer = ""
                return False
                
        # Sadece rakamları / harfleri tampona al (barkodlar için)
        if len(e.key) == 1 and e.key.isalnum():
            self._scanner_buffer += e.key
            return True
        elif len(e.key) == 1:
            self._scanner_buffer = "" # iptal
            
        return False



    def _build_bulk_price_card(self):
        return ft.Container(
            bgcolor=ft.Colors.WHITE,
            border_radius=14,
            padding=16,
            content=ft.Column(
                spacing=16,
                controls=[
                    ft.Text("Toplu Fiyat Degistirme", size=20, weight=ft.FontWeight.W_700, color=ft.Colors.INDIGO_800),
                    ft.Container(
                        bgcolor=ft.Colors.AMBER_50, border_radius=10,
                        border=ft.border.all(1, ft.Colors.AMBER_200),
                        padding=12,
                        content=ft.Row([
                            ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.AMBER_700),
                            ft.Text(
                                "Secilen kapsama gore tum urunlerin satis fiyatini artir veya azalt.\n"
                                "Bu islem geri alinamaz, oncesinde yedek almaniz onerilir.",
                                size=12, color=ft.Colors.AMBER_900,
                            ),
                        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START),
                    ),
                    ft.Row([self.dd_bulk_scope, self.dd_bulk_group, self.dd_bulk_category], spacing=12),
                    ft.Row([self.dd_bulk_type, self.dd_bulk_direction, self.txt_bulk_value], spacing=12),
                    ft.Row([
                        ft.OutlinedButton(
                            "Onizle",
                            icon=ft.Icons.PREVIEW,
                            style=ft.ButtonStyle(color=ft.Colors.INDIGO_700),
                            on_click=self._preview_bulk_price,
                        ),
                        ft.ElevatedButton(
                            "Fiyatlari Guncelle",
                            icon=ft.Icons.PRICE_CHANGE,
                            style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_700, color=ft.Colors.WHITE),
                            on_click=self._do_bulk_price_change,
                        ),
                    ], spacing=10),
                    self.lbl_bulk_result,
                    self.lbl_bulk_preview_status,
                    ft.Container(
                        content=self.bulk_preview_table_col,
                        bgcolor=ft.Colors.GREY_50,
                        border_radius=10,
                        padding=10,
                    ),
                ],
            ),
        )

    def _build_taxonomy_card(self):
        return ft.Column(
            spacing=12,
            controls=[
                # Gruplar
                ft.Container(
                    bgcolor=ft.Colors.WHITE, border_radius=14, padding=16,
                    content=ft.Column(spacing=10, controls=[
                        ft.Text("Urun Gruplari", size=17, weight=ft.FontWeight.W_700, color=ft.Colors.INDIGO_800),
                        ft.Row([
                            ft.Container(expand=True, content=self.txt_group_name),
                            ft.Container(expand=True, content=self.txt_group_note),
                            ft.ElevatedButton(
                                "Kaydet", icon=ft.Icons.SAVE,
                                style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_600, color=ft.Colors.WHITE),
                                on_click=self._save_group,
                            ),
                            ft.OutlinedButton("Yeni", icon=ft.Icons.ADD, on_click=lambda _: self._reset_group_form()),
                        ], spacing=8),
                        self.groups_list,
                    ]),
                ),
                # Kategoriler
                ft.Container(
                    bgcolor=ft.Colors.WHITE, border_radius=14, padding=16,
                    content=ft.Column(spacing=10, controls=[
                        ft.Text("Alt Kategoriler", size=17, weight=ft.FontWeight.W_700, color=ft.Colors.TEAL_800),
                        ft.Row([
                            ft.Container(expand=True, content=self.txt_cat_group),
                            ft.Container(expand=True, content=self.txt_cat_name),
                            ft.Container(expand=True, content=self.txt_cat_note),
                            ft.ElevatedButton(
                                "Kaydet", icon=ft.Icons.SAVE,
                                style=ft.ButtonStyle(bgcolor=ft.Colors.TEAL_600, color=ft.Colors.WHITE),
                                on_click=self._save_category,
                            ),
                            ft.OutlinedButton("Yeni", icon=ft.Icons.ADD, on_click=lambda _: self._reset_category_form()),
                        ], spacing=8),
                        self.cats_list,
                    ]),
                ),
            ],
        )

    # ── Yardimci ─────────────────────────────────────────────────────────────

    def _safe_update(self):
        try:
            if self.page is None:
                return
            self.update()
        except Exception:
            pass

    def _snack(self, text: str):
        try:
            self.page.snack_bar = ft.SnackBar(ft.Text(text), open=True)
            self.page.update()
        except Exception:
            pass

    def _run_ui_call(self, result):
        if inspect.isawaitable(result):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(result)
            except RuntimeError:
                pass

    def _open_dialog(self, dlg):
        try:
            if dlg not in self.page.overlay:
                self.page.overlay.append(dlg)
            dlg.open = True
            self.page.update()
        except Exception:
            pass

    def _close_dialog(self, dlg):
        try:
            dlg.open = False
            self.page.update()
        except Exception:
            pass

    def _load_suppliers(self):
        suppliers = self.db.list_suppliers()
        self.dd_supplier.options = [ft.dropdown.Option("", "-- Tedarikci Yok --")] + [
            ft.dropdown.Option(str(s[0]), s[1]) for s in suppliers
        ]
        self._safe_update()

    def _merged_group_names(self) -> list[str]:
        names: list[str] = []
        try:
            names.extend(g[1] for g in self.db.list_product_groups() if g and g[1])
        except Exception:
            pass
        try:
            names.extend(name for name in self.db.list_categories() if name)
        except Exception:
            pass
        return sorted({str(name).strip() for name in names if str(name).strip()})

    def _merged_sub_category_names(self, group_name: str = "") -> list[str]:
        names: list[str] = []
        try:
            cats = self.db.list_product_categories(group_name=group_name) if group_name else self.db.list_product_categories()
            names.extend(c[2] for c in cats if len(c) > 2 and c[2])
        except Exception:
            pass
        try:
            names.extend(name for name in self.db.list_sub_categories(group_name) if name)
        except Exception:
            pass
        return sorted({str(name).strip() for name in names if str(name).strip()})

    def _load_category_dropdowns(self):
        """Populate Category and Sub-Category dropdowns from DB taxonomy."""
        current_group = self.dd_category.value or ""
        groups = self._merged_group_names()
        self.dd_category.options = [ft.dropdown.Option("", "-- Sec --")] + [
            ft.dropdown.Option(name, name) for name in groups
        ]
        self.dd_category.value = current_group if current_group in groups else ""
        self._on_category_changed()
        self._safe_update()

    def _on_category_changed(self, group_override: str | None = None):
        """When category changes, reload sub-category options from DB."""
        group = group_override if group_override is not None else (self.dd_category.value or "")
        current_sub = self.dd_sub_category.value or ""
        cats = self._merged_sub_category_names(group)
        self.dd_sub_category.options = [ft.dropdown.Option("", "-- Sec --")] + [
            ft.dropdown.Option(name, name) for name in cats
        ]
        if group_override is None:
            self.dd_sub_category.value = current_sub if current_sub in cats else ""
        self._safe_update()



    def _pick_image(self, _e):
        def _open_dialog():
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                path = filedialog.askopenfilename(
                    title="Urun Resmi Sec",
                    filetypes=[
                        ("Resim Dosyalari", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"),
                        ("Tum Dosyalar", "*.*"),
                    ],
                )
                root.destroy()
                if path:
                    self.selected_image_src = path
                    self.img_preview.src = path
                    self._safe_update()
            except Exception as ex:
                self._snack(f"Resim secilemedi: {ex}")
        threading.Thread(target=_open_dialog, daemon=True).start()

    def _on_generate_barcode(self, _e):
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

    # ── Quick sale products ───────────────────────────────────────────────────

    def _load_quick_product_ids(self) -> list[int]:
        raw = self.db.get_setting("quick_sale_product_ids", "[]")
        try:
            values = json.loads(raw)
        except Exception:
            values = []
        result: list[int] = []
        for value in values if isinstance(values, list) else []:
            try:
                product_id = int(value)
            except (TypeError, ValueError):
                continue
            if product_id not in result:
                result.append(product_id)
        return result

    def _save_quick_product_ids(self, available_rows: list | None = None):
        rows = available_rows if available_rows is not None else self.db.get_products_by_ids(self._quick_product_ids)
        valid_ids = {int(r[0]) for r in rows if r and r[0] is not None}
        cleaned: list[int] = []
        for product_id in self._quick_product_ids:
            if product_id in valid_ids and product_id not in cleaned:
                cleaned.append(product_id)
        self._quick_product_ids = cleaned
        self.db.set_setting("quick_sale_product_ids", json.dumps(cleaned))

    def _refresh_quick_add_options(self, rows: list):
        current = self.dd_quick_add.value
        self.dd_quick_add.options = [
            ft.dropdown.Option(str(r[0]), f"{r[1]} | {r[2] or '-'}")
            for r in rows
        ]
        valid_ids = {str(r[0]) for r in rows}
        self.dd_quick_add.value = current if current in valid_ids else None

    def _refresh_quick_add_options_from_search(self):
        query = (self.txt_quick_add_search.value or "").strip()
        rows = self.db.search_products(search=query, limit=200, offset=0)
        self._refresh_quick_add_options(rows)
        self._safe_update()

    def _schedule_quick_add_refresh(self, delay: float = 0.25):
        try:
            if self._quick_search_timer:
                self._quick_search_timer.cancel()
        except Exception:
            pass
        import threading
        self._quick_search_timer = threading.Timer(delay, self._refresh_quick_add_options_from_search)
        self._quick_search_timer.daemon = True
        self._quick_search_timer.start()

    def _add_selected_quick_product(self):
        if not self.dd_quick_add.value:
            self._snack("Once urun secin")
            return
        try:
            product_id = int(self.dd_quick_add.value)
        except ValueError:
            return
        if product_id in self._quick_product_ids:
            self._snack("Bu urun zaten hizli satis listesinde")
            return
        self._quick_product_ids.append(product_id)
        self._save_quick_product_ids()
        self.refresh_table()
        self.on_products_changed()
        self._snack("Urun hizli satis listesine eklendi")

    def _toggle_quick_product(self, product_id: int):
        if product_id in self._quick_product_ids:
            self._quick_product_ids = [pid for pid in self._quick_product_ids if pid != product_id]
            message = "Urun hizli satis listesinden cikarildi"
        else:
            self._quick_product_ids.append(product_id)
            message = "Urun hizli satis listesine eklendi"
        self._save_quick_product_ids()
        self.refresh_table()
        self.on_products_changed()
        self._snack(message)

    def _move_quick_product(self, product_id: int, direction: int):
        try:
            index = self._quick_product_ids.index(product_id)
        except ValueError:
            return
        new_index = index + direction
        if new_index < 0 or new_index >= len(self._quick_product_ids):
            return
        self._quick_product_ids[index], self._quick_product_ids[new_index] = (
            self._quick_product_ids[new_index], self._quick_product_ids[index]
        )
        self._save_quick_product_ids()
        self.refresh_table()
        self.on_products_changed()

    def _refresh_quick_selection_panel(self, all_rows: list | None = None):
        rows = all_rows if all_rows is not None else self.db.get_products_by_ids(self._quick_product_ids)
        row_map = {int(r[0]): r for r in rows if r and r[0] is not None}
        valid_ids = [pid for pid in self._quick_product_ids if pid in row_map]
        if valid_ids != self._quick_product_ids:
            self._quick_product_ids = valid_ids
            self._save_quick_product_ids(rows)

        self.lbl_quick_summary.value = (
            f"Secili urun sayisi: {len(self._quick_product_ids)}"
            if self._quick_product_ids
            else "Henuz hizli satis urunu secilmedi."
        )

        controls = []
        for index, product_id in enumerate(self._quick_product_ids):
            row = row_map[product_id]
            controls.append(
                ft.Container(
                    bgcolor=ft.Colors.INDIGO_50 if index % 2 == 0 else ft.Colors.GREY_50,
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=10, vertical=8),
                    content=ft.Row([
                        ft.Container(
                            width=28, height=28, border_radius=14,
                            bgcolor=ft.Colors.INDIGO_700, alignment=ft.Alignment(0, 0),
                            content=ft.Text(str(index + 1), color=ft.Colors.WHITE, size=11),
                        ),
                        ft.Column([
                            ft.Text(row[1] or "", weight=ft.FontWeight.W_600, size=14),
                            ft.Text(row[2] or "", size=11, color=ft.Colors.BLUE_GREY_500),
                        ], spacing=2, expand=True),
                        ft.IconButton(ft.Icons.KEYBOARD_ARROW_UP, tooltip="Yukari al",
                                      on_click=lambda _, pid=product_id: self._move_quick_product(pid, -1),
                                      disabled=index == 0),
                        ft.IconButton(ft.Icons.KEYBOARD_ARROW_DOWN, tooltip="Asagi al",
                                      on_click=lambda _, pid=product_id: self._move_quick_product(pid, 1),
                                      disabled=index == len(self._quick_product_ids) - 1),
                        ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, tooltip="Listeden cikar",
                                      icon_color=ft.Colors.RED_600,
                                      on_click=lambda _, pid=product_id: self._toggle_quick_product(pid)),
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                )
            )
        if not controls:
            controls = [ft.Container(
                padding=ft.padding.symmetric(vertical=8),
                content=ft.Text("Hizli satis listesi bos.", color=ft.Colors.BLUE_GREY_400),
            )]
        self.quick_selection_list.controls = controls

    # ── Form ─────────────────────────────────────────────────────────────────

    def _load_product_to_form(self, product_id: int):
        r = self.db.get_product_full(product_id)
        if not r:
            return
        self._editing_id = r[0]
        self.txt_name.value = r[1] or ""
        self.txt_barcode.value = r[2] or ""
        self.txt_barcode.read_only = True
        self.txt_desc.value = r[3] or ""
        self.dd_category.value = r[4] or ""
        # Populate sub-cats for this group then set value
        self._on_category_changed(group_override=r[4] or "")
        self.dd_sub_category.value = r[5] or ""
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
        self.dd_supplier.value = str(r[16]) if r[16] else ""
        self.lbl_form_title.value = f"Urunu Duzenle: {r[1]}"
        self.lbl_form_title.color = ft.Colors.ORANGE_700
        self.btn_cancel_edit.visible = True
        self.btn_save.text = "Degisiklikleri Kaydet"
        self._refresh_price_labels()
        # Form sekmesine gec
        self._tabs.selected_index = 0
        self._safe_update()

    def _reset_form(self):
        self._editing_id = None
        self.txt_name.value = ""
        self.txt_barcode.value = ""
        self.txt_barcode.read_only = False
        self.txt_desc.value = ""
        self.dd_category.value = ""
        self.dd_sub_category.value = ""
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
        self.lbl_form_title.color = ft.Colors.INDIGO_800
        self.btn_cancel_edit.visible = False
        self.btn_save.text = "Urun Kaydet"
        self._refresh_price_labels()
        self._safe_update()

    def start_add_with_barcode(self, barcode: str):
        self._reset_form()
        self.txt_barcode.value = (barcode or "").strip()
        self._tabs.selected_index = 0
        self._safe_update()

    def _close_dlg(self, dlg):
        try:
            dlg.open = False
            self.page.update()
        except Exception:
            pass

    def _confirm_delete(self, product_id: int, product_name: str):
        def do_delete(_e):
            self.db.delete_product(product_id)
            if product_id in self._quick_product_ids:
                self._quick_product_ids = [pid for pid in self._quick_product_ids if pid != product_id]
                self._save_quick_product_ids()
            self._close_dialog(dlg)
            self.invalidate_cache()
            self.refresh_table()
            self.on_products_changed()
            self._snack(f"{product_name} silindi")

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Urunu Sil"),
            content=ft.Text(f'"{product_name}" urununu silmek istediginize emin misiniz?'),
            actions=[
                ft.TextButton("Vazgec", on_click=lambda _: self._close_dialog(dlg)),
                ft.ElevatedButton(
                    "Evet, Sil",
                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED_600, color=ft.Colors.WHITE),
                    on_click=do_delete,
                ),
            ],
        )
        self._open_dialog(dlg)

    def _show_edit_popup(self, product_id: int):
        """Sag tik ile gelen duzenle popup'i — Tab'a gitmeden dialog icinde duzenle."""
        r = self.db.get_product_full(product_id)
        if not r:
            return
        txt_name = ft.TextField(label="Urun Adi *", value=r[1] or "", expand=True)
        txt_buy = ft.TextField(label="Alis Fiyati", value=str(r[7] or 0), width=140)
        txt_sell = ft.TextField(label="Satis Fiyati", value=str(r[9] or 0), width=140)
        txt_vat = ft.TextField(label="KDV %", value=str(r[10] or 20), width=110)
        txt_stock = ft.TextField(label="Stok", value=str(r[12] or 0), width=120)
        txt_critical = ft.TextField(label="Kritik Stok", value=str(r[13] or 0), width=120)
        dd_vat_mode = ft.Dropdown(
            label="Satis Modu",
            value=r[11] or "INCL", width=170,
            options=[ft.dropdown.Option("INCL", "KDV Dahil"), ft.dropdown.Option("EXCL", "KDV Haric")],
        )
        lbl_prices = ft.Text("", size=12, color=ft.Colors.GREEN_700)

        def _upd_prices(_e=None):
            base = self._to_float(txt_sell.value, 0)
            vat = self._to_float(txt_vat.value, 20)
            excl, incl = compute_prices(base, vat, dd_vat_mode.value or "INCL")
            lbl_prices.value = f"KDV Haric: {excl:.2f}  |  KDV Dahil: {incl:.2f}"
            try:
                self.page.update()
            except Exception:
                pass

        txt_sell.on_change = _upd_prices
        txt_vat.on_change = _upd_prices
        dd_vat_mode.on_select = _upd_prices
        _upd_prices()

        def _save_popup(_e):
            name = (txt_name.value or "").strip()
            if not name:
                return
            base = self._to_float(txt_sell.value, 0)
            vat = self._to_float(txt_vat.value, 20)
            excl, incl = compute_prices(base, vat, dd_vat_mode.value or "INCL")
            self.db.upsert_product(
                barcode=r[2],
                name=name,
                description=r[3] or "",
                category=r[4] or "",
                sub_category=r[5] or "",
                unit=r[6] or "adet",
                buy_price=self._to_float(txt_buy.value, 0),
                sell_price_excl_vat=excl,
                sell_price_incl_vat=incl,
                vat_rate=vat,
                vat_mode=dd_vat_mode.value or "INCL",
                stock=self._to_float(txt_stock.value, 0),
                critical_stock=self._to_float(txt_critical.value, 0),
                image_path=r[14] or "",
                is_scale_product=bool(r[15]),
            )
            self._close_dialog(dlg)
            self.invalidate_cache()
            self.refresh_table()
            self.on_products_changed()
            self._snack(f"{name} guncellendi")

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.EDIT, color=ft.Colors.INDIGO_700),
                ft.Text(f"Hizli Duzenle: {r[1]}", size=14),
            ], spacing=8),
            content=ft.Container(
                width=560,
                content=ft.Column([
                    txt_name,
                    ft.Row([txt_buy, txt_sell, dd_vat_mode, txt_vat], spacing=8),
                    lbl_prices,
                    ft.Row([txt_stock, txt_critical], spacing=8),
                ], spacing=10, tight=True),
            ),
            actions=[
                ft.TextButton("Vazgec", on_click=lambda _: self._close_dialog(dlg)),
                ft.ElevatedButton(
                    "Kaydet",
                    icon=ft.Icons.SAVE,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
                    on_click=_save_popup,
                ),
            ],
        )
        self._open_dialog(dlg)

    def _save_product(self, _e):
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
            category=(self.dd_category.value or "").strip(),
            sub_category=(self.dd_sub_category.value or "").strip(),
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

    # ── Toplu fiyat ───────────────────────────────────────────────────────────

    def _on_bulk_scope_changed(self):
        scope = self.dd_bulk_scope.value or "ALL"
        self.dd_bulk_group.visible = scope in ("GROUP", "CATEGORY")
        self.dd_bulk_category.visible = scope == "CATEGORY"
        if scope in ("GROUP", "CATEGORY"):
            groups = self._merged_group_names()
            self.dd_bulk_group.options = [ft.dropdown.Option("", "-- Hepsi --")] + [
                ft.dropdown.Option(name, name) for name in groups
            ]
            self._on_bulk_group_changed()
        self._safe_update()

    def _on_bulk_group_changed(self):
        scope = self.dd_bulk_scope.value or "ALL"
        if scope == "CATEGORY":
            group_name = self.dd_bulk_group.value or ""
            cats = self._merged_sub_category_names(group_name)
            self.dd_bulk_category.options = [ft.dropdown.Option("", "-- Hepsi --")] + [
                ft.dropdown.Option(name, name) for name in cats
            ]
            self.dd_bulk_category.value = ""
        self._safe_update()

    # ── Kategori/Grup yonetimi ────────────────────────────────────────────────

    def _bulk_scope_label(self, scope: str, group_name: str, category_name: str) -> str:
        if scope == "GROUP":
            return f"Grup: {group_name or 'Hepsi'}"
        if scope == "CATEGORY":
            if group_name and category_name:
                return f"{group_name} > {category_name}"
            if group_name:
                return f"{group_name} > Tum alt kategoriler"
            if category_name:
                return f"Alt kategori: {category_name}"
            return "Tum alt kategoriler"
        return "Tum urunler"

    def _collect_bulk_price_preview(self) -> list[dict]:
        scope = self.dd_bulk_scope.value or "ALL"
        change_type = self.dd_bulk_type.value or "PERCENT"
        direction = self.dd_bulk_direction.value or "INCREASE"
        try:
            value = float((self.txt_bulk_value.value or "0").replace(",", "."))
        except ValueError:
            self._snack("Gecerli bir deger giriniz")
            return []
        if value <= 0:
            self._snack("Deger 0'dan buyuk olmalidir")
            return []

        group_name = self.dd_bulk_group.value or ""
        category_name = self.dd_bulk_category.value or ""
        affected = []
        for r in self.db.list_products_by_scope(scope=scope, group_name=group_name, category_name=category_name):
            group = (r[10] or "") if len(r) > 10 else ""
            sub_category = (r[11] or "") if len(r) > 11 else ""
            if scope == "GROUP" and group_name and group != group_name:
                continue
            if scope == "CATEGORY" and group_name and group != group_name:
                continue
            if scope == "CATEGORY" and category_name and sub_category != category_name:
                continue

            old_price = float(r[4] or 0)
            delta = old_price * value / 100 if change_type == "PERCENT" else value
            new_price = old_price + delta if direction == "INCREASE" else old_price - delta
            affected.append({
                "id": int(r[0]),
                "name": r[1] or "",
                "barcode": r[2] or "",
                "group": group,
                "category": sub_category,
                "old_price": old_price,
                "new_price": max(0.0, new_price),
            })
        return affected

    def _render_bulk_preview_inline(self, affected: list[dict]):
        if not affected:
            self.lbl_bulk_preview_status.value = "Hicbir urun bu kriterlere uymuyor."
            self.bulk_preview_table_col.controls = []
            self._safe_update()
            return

        self.lbl_bulk_preview_status.value = (
            f"{len(affected)} urun etkilenecek. Onizleme penceresinde tek tek duzenleyebilirsiniz."
        )
        rows_ui = [
            ft.Row([
                ft.Text("Urun Adi", size=12, weight=ft.FontWeight.W_700, expand=True),
                ft.Text("Onceki", size=12, weight=ft.FontWeight.W_700, width=95, text_align=ft.TextAlign.RIGHT),
                ft.Text("Yeni", size=12, weight=ft.FontWeight.W_700, width=95, text_align=ft.TextAlign.RIGHT),
            ], spacing=4)
        ]
        for item in affected[:50]:
            old_p = item["old_price"]
            new_p = item["new_price"]
            color = ft.Colors.GREEN_700 if new_p >= old_p else ft.Colors.RED_700
            rows_ui.append(ft.Row([
                ft.Text(item["name"], size=12, expand=True, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(f"{old_p:.2f} TL", size=12, width=95, text_align=ft.TextAlign.RIGHT, color=ft.Colors.BLUE_GREY_700),
                ft.Text(f"{new_p:.2f} TL", size=12, weight=ft.FontWeight.W_600, width=95, text_align=ft.TextAlign.RIGHT, color=color),
            ], spacing=4))
        if len(affected) > 50:
            rows_ui.append(ft.Text(f"... ve {len(affected) - 50} urun daha", size=11, color=ft.Colors.BLUE_GREY_400))
        self.bulk_preview_table_col.controls = rows_ui
        self._safe_update()

    def _open_bulk_preview_dialog(self, affected: list[dict]):
        if not affected:
            return

        scope = self.dd_bulk_scope.value or "ALL"
        change_type = self.dd_bulk_type.value or "PERCENT"
        direction = self.dd_bulk_direction.value or "INCREASE"
        value = float((self.txt_bulk_value.value or "0").replace(",", "."))
        group_name = self.dd_bulk_group.value or ""
        category_name = self.dd_bulk_category.value or ""
        direction_label = "Artis" if direction == "INCREASE" else "Azalis"
        type_label = f"%{value:.2f}" if change_type == "PERCENT" else f"{value:.2f} TL"
        price_fields: dict[int, ft.TextField] = {}

        rows = [
            ft.Row(
                [
                    ft.Text("Urun", size=12, weight=ft.FontWeight.W_700, expand=True),
                    ft.Text("Onceki", size=12, weight=ft.FontWeight.W_700, width=100, text_align=ft.TextAlign.RIGHT),
                    ft.Text("Yeni fiyat", size=12, weight=ft.FontWeight.W_700, width=130, text_align=ft.TextAlign.RIGHT),
                ],
                spacing=8,
            ),
            ft.Divider(height=1),
        ]
        for item in affected:
            field = ft.TextField(
                value=f"{item['new_price']:.2f}",
                width=130,
                dense=True,
                text_align=ft.TextAlign.RIGHT,
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            price_fields[item["id"]] = field
            rows.append(
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(item["name"], size=12, weight=ft.FontWeight.W_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(item["barcode"] or "-", size=10, color=ft.Colors.BLUE_GREY_500, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        ft.Text(f"{item['old_price']:.2f} TL", size=12, width=100, text_align=ft.TextAlign.RIGHT, color=ft.Colors.BLUE_GREY_700),
                        field,
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )

        msg = ft.Text("", size=12, color=ft.Colors.RED_600)

        def _apply(_e):
            updates: list[tuple[int, float]] = []
            for item in affected:
                raw = price_fields[item["id"]].value or "0"
                try:
                    new_price = float(raw.replace(",", "."))
                except ValueError:
                    msg.value = f"Gecersiz fiyat: {item['name']}"
                    try:
                        self.page.update()
                    except Exception:
                        self._safe_update()
                    return
                if new_price < 0:
                    msg.value = f"Fiyat negatif olamaz: {item['name']}"
                    try:
                        self.page.update()
                    except Exception:
                        self._safe_update()
                    return
                updates.append((item["id"], new_price))

            count = self.db.set_product_prices(updates)
            self._close_dialog(dlg)
            self.lbl_bulk_result.value = f"{count} urunun fiyati guncellendi."
            self.lbl_bulk_result.color = ft.Colors.GREEN_700 if count > 0 else ft.Colors.ORANGE_700
            self.bulk_preview_table_col.controls = []
            self.lbl_bulk_preview_status.value = "Guncelleme tamamlandi. Yeni onizleme icin tekrar Onizle'ye basin."
            self.invalidate_cache()
            self.refresh_table(force_reload=True)
            self.on_products_changed()
            self._safe_update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Toplu Fiyat Onizleme"),
            content=ft.Container(
                width=780,
                height=520,
                content=ft.Column(
                    [
                        ft.Container(
                            bgcolor=ft.Colors.INDIGO_50,
                            border_radius=8,
                            padding=ft.padding.symmetric(horizontal=10, vertical=8),
                            content=ft.Column(
                                [
                                    ft.Text(f"Kapsam: {self._bulk_scope_label(scope, group_name, category_name)}", size=12, weight=ft.FontWeight.W_600),
                                    ft.Text(f"Islem: {direction_label} - {type_label}", size=12, color=ft.Colors.BLUE_GREY_700),
                                    ft.Text("Yeni fiyat alanlarini degistirerek tek urunu farkli fiyata alabilirsiniz.", size=11, color=ft.Colors.INDIGO_700),
                                ],
                                spacing=3,
                            ),
                        ),
                        ft.Container(
                            expand=True,
                            content=ft.Column(rows, spacing=6, scroll=ft.ScrollMode.AUTO),
                        ),
                        msg,
                    ],
                    spacing=10,
                ),
            ),
            actions=[
                ft.TextButton("Kapat", on_click=lambda _: self._close_dialog(dlg)),
                ft.ElevatedButton(
                    "Onizlenen Fiyatlari Uygula",
                    icon=ft.Icons.CHECK,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_700, color=ft.Colors.WHITE),
                    on_click=_apply,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._open_dialog(dlg)

    def _preview_bulk_price(self, _e=None):
        affected = self._collect_bulk_price_preview()
        if not affected:
            self.lbl_bulk_preview_status.value = "Hicbir urun bu kriterlere uymuyor."
            self.bulk_preview_table_col.controls = []
            self._safe_update()
            return
        self._render_bulk_preview_inline(affected)
        self._open_bulk_preview_dialog(affected)

    def _do_bulk_price_change(self, _e):
        affected = self._collect_bulk_price_preview()
        if not affected:
            self.lbl_bulk_preview_status.value = "Hicbir urun bu kriterlere uymuyor."
            self.bulk_preview_table_col.controls = []
            self._safe_update()
            return
        self._render_bulk_preview_inline(affected)
        self._open_bulk_preview_dialog(affected)

    def _refresh_taxonomy_lists(self):
        # Grup listesi
        groups = self.db.list_product_groups()
        rows = []
        for g in groups:
            gid, gname, gnote = g
            rows.append(ft.Container(
                bgcolor=ft.Colors.GREY_50, border_radius=10,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                content=ft.Row([
                    ft.Icon(ft.Icons.FOLDER, color=ft.Colors.INDIGO_400, size=18),
                    ft.Text(gname or "", weight=ft.FontWeight.W_600, expand=True),
                    ft.Text(gnote or "", size=11, color=ft.Colors.BLUE_GREY_500),
                    ft.IconButton(ft.Icons.EDIT, icon_color=ft.Colors.BLUE_700, tooltip="Duzenle",
                                  on_click=lambda _, n=gname, nt=gnote: self._edit_group(n, nt)),
                    ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_600, tooltip="Sil",
                                  on_click=lambda _, n=gname: self._confirm_delete_group(n)),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ))
        self.groups_list.controls = rows if rows else [
            ft.Text("Henuz grup yok", color=ft.Colors.BLUE_GREY_400)
        ]

        # Kategori listesi
        cats = self.db.list_product_categories()
        cat_rows = []
        for c in cats:
            cid, cgroup, cname, cnote = c
            cat_rows.append(ft.Container(
                bgcolor=ft.Colors.GREY_50, border_radius=10,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                content=ft.Row([
                    ft.Icon(ft.Icons.LABEL, color=ft.Colors.TEAL_400, size=16),
                    ft.Text(f"{cgroup} > " if cgroup else "", size=11, color=ft.Colors.BLUE_GREY_500),
                    ft.Text(cname or "", weight=ft.FontWeight.W_600, expand=True),
                    ft.Text(cnote or "", size=11, color=ft.Colors.BLUE_GREY_500),
                    ft.IconButton(ft.Icons.EDIT, icon_color=ft.Colors.BLUE_700, tooltip="Duzenle",
                                  on_click=lambda _, n=cname, gn=cgroup, nt=cnote: self._edit_category(gn, n, nt)),
                    ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_600, tooltip="Sil",
                                  on_click=lambda _, n=cname, gn=cgroup: self._confirm_delete_category(gn, n)),
                ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ))
        self.cats_list.controls = cat_rows if cat_rows else [
            ft.Text("Henuz alt kategori yok", color=ft.Colors.BLUE_GREY_400)
        ]

        # Kategori ekleme dropdown'unu guncelle
        self.txt_cat_group.options = [ft.dropdown.Option("", "-- Grupsuz --")] + [
            ft.dropdown.Option(g[1], g[1]) for g in groups
        ]
        # Filtre dropdown'unu guncelle
        self.dd_filter_group.options = [ft.dropdown.Option("", "Tum Gruplar")] + [
            ft.dropdown.Option(g[1], g[1]) for g in groups
        ]
        self._safe_update()

    def _reset_group_form(self):
        self._editing_group_name = ""
        self.txt_group_name.value = ""
        self.txt_group_name.read_only = False
        self.txt_group_note.value = ""
        self._safe_update()

    def _edit_group(self, name: str, note: str):
        self._editing_group_name = name
        self.txt_group_name.value = name
        self.txt_group_name.read_only = False
        self.txt_group_note.value = note
        self._safe_update()

    def _save_group(self, _e):
        name = (self.txt_group_name.value or "").strip()
        if not name:
            self._snack("Grup adi zorunlu")
            return
        try:
            self.db.upsert_product_group(name, old_name=self._editing_group_name,
                                          note=self.txt_group_note.value or "")
            self._reset_group_form()
            self._refresh_taxonomy_lists()
            self._snack(f"Grup kaydedildi: {name}")
        except Exception as ex:
            self._snack(f"Hata: {ex}")

    def _confirm_delete_group(self, name: str):
        def _do(_e):
            self.db.delete_product_group(name)
            self._close_dialog(dlg)
            self._refresh_taxonomy_lists()
            self._snack(f"{name} grubu silindi")

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Grubu Sil"),
            content=ft.Text(f'"{name}" grubu ve bagli kategorileri silinsin mi?'),
            actions=[
                ft.TextButton("Vazgec", on_click=lambda _: self._close_dialog(dlg)),
                ft.ElevatedButton("Sil", style=ft.ButtonStyle(bgcolor=ft.Colors.RED_600, color=ft.Colors.WHITE), on_click=_do),
            ],
        )
        self._open_dialog(dlg)

    def _reset_category_form(self):
        self._editing_cat_key = ("", "")
        self.txt_cat_name.value = ""
        self.txt_cat_group.value = ""
        self.txt_cat_note.value = ""
        self._safe_update()

    def _edit_category(self, group_name: str, name: str, note: str):
        self._editing_cat_key = (group_name, name)
        self.txt_cat_group.value = group_name
        self.txt_cat_name.value = name
        self.txt_cat_note.value = note
        self._safe_update()

    def _save_category(self, _e):
        name = (self.txt_cat_name.value or "").strip()
        if not name:
            self._snack("Kategori adi zorunlu")
            return
        old_group, old_name = self._editing_cat_key
        try:
            self.db.upsert_product_category(
                name, group_name=self.txt_cat_group.value or "",
                old_name=old_name, old_group_name=old_group,
                note=self.txt_cat_note.value or "",
            )
            self._reset_category_form()
            self._refresh_taxonomy_lists()
            self._snack(f"Kategori kaydedildi: {name}")
        except Exception as ex:
            self._snack(f"Hata: {ex}")

    def _confirm_delete_category(self, group_name: str, name: str):
        def _do(_e):
            self.db.delete_product_category(name, group_name=group_name)
            self._close_dialog(dlg)
            self._refresh_taxonomy_lists()
            self._snack(f"{name} kategorisi silindi")

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Kategoriyi Sil"),
            content=ft.Text(f'"{name}" kategorisi silinsin mi?'),
            actions=[
                ft.TextButton("Vazgec", on_click=lambda _: self._close_dialog(dlg)),
                ft.ElevatedButton("Sil", style=ft.ButtonStyle(bgcolor=ft.Colors.RED_600, color=ft.Colors.WHITE), on_click=_do),
            ],
        )
        self._open_dialog(dlg)

    # ── Urun listesi ─────────────────────────────────────────────────────────

    def _build_product_row(self, row):
        pid = int(row[0])
        stock = float(row[6] or 0)
        critical = float(row[9] if len(row) > 9 else 5)
        stok_color = ft.Colors.RED_700 if stock <= 0 else (ft.Colors.ORANGE_700 if stock <= critical else ft.Colors.GREEN_700)
        image_path = row[7]
        is_quick = pid in self._quick_product_ids

        thumb = (
            ft.Image(src=image_path, width=58, height=58, fit=ft.BoxFit.COVER, border_radius=8)
            if (image_path and self._show_list_images)
            else ft.Container(
                width=58, height=58, bgcolor=ft.Colors.GREY_100,
                border_radius=8, alignment=ft.Alignment(0, 0),
                content=ft.Icon(ft.Icons.SHOPPING_BAG, size=28, color=ft.Colors.GREY_400),
            )
        )

        # Sag tik kontekst menusu (GestureDetector ile)
        action_bar = ft.Row([
            ft.IconButton(ft.Icons.EDIT, icon_color=ft.Colors.BLUE_700, tooltip="Duzenle",
                          on_click=lambda _, _id=pid: self._load_product_to_form(_id)),
            ft.IconButton(
                ft.Icons.STAR if is_quick else ft.Icons.STAR_BORDER,
                icon_color=ft.Colors.ORANGE_700 if is_quick else ft.Colors.BLUE_GREY_400,
                tooltip="Hizli satis listesi",
                on_click=lambda _, _id=pid: self._toggle_quick_product(_id),
            ),
            ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_600, tooltip="Sil",
                          on_click=lambda _, _id=pid, _n=row[1]: self._confirm_delete(_id, _n)),
        ], spacing=0)

        row_content = ft.Container(
            bgcolor=ft.Colors.GREY_50 if pid % 2 == 0 else ft.Colors.WHITE,
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            content=ft.Row([
                thumb,
                ft.Column([
                    ft.Text(row[1] or "", size=15, weight=ft.FontWeight.W_700, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(f"Barkod: {row[2] or '-'}", size=11, color=ft.Colors.BLUE_GREY_500),
                    ft.Row([
                        ft.Text(f"Birim: {row[3] or '-'}", size=11, color=ft.Colors.BLUE_GREY_500),
                        ft.Text(f"| KDV: %{float(row[5] or 0):.0f}", size=11, color=ft.Colors.BLUE_GREY_500),
                        ft.Text(f"| {row[10] or ''}", size=11, color=ft.Colors.INDIGO_500) if row[10] else ft.Text(""),
                    ], spacing=4),
                ], spacing=2, expand=True),
                ft.Column([
                    ft.Text(f"{float(row[4] or 0):.2f} TL", size=15, weight=ft.FontWeight.W_700, color=ft.Colors.INDIGO_700),
                    ft.Text(f"Stok: {stock:.2f}", size=12, color=stok_color, weight=ft.FontWeight.W_600),
                ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.END),
                action_bar,
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

        # Sag tik: popup menu
        return ft.GestureDetector(
            content=row_content,
            on_secondary_tap=lambda _, _pid=pid, _name=row[1]: self._show_row_context_menu(_pid, _name),
        )

    def _show_row_context_menu(self, product_id: int, product_name: str):
        is_quick = product_id in self._quick_product_ids
        menu = ft.AlertDialog(
            modal=False,
            title=ft.Text(product_name, size=13, weight=ft.FontWeight.W_600),
            content=ft.Column([
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.EDIT, color=ft.Colors.BLUE_700),
                    title=ft.Text("Hizli Duzenle"),
                    on_click=lambda _: (self._close_dialog(menu), self._show_edit_popup(product_id)),
                ),
                ft.ListTile(
                    leading=ft.Icon(
                        ft.Icons.STAR if is_quick else ft.Icons.STAR_BORDER,
                        color=ft.Colors.ORANGE_700,
                    ),
                    title=ft.Text("Hizli Listeden Cikar" if is_quick else "Hizli Listeye Ekle"),
                    on_click=lambda _: (self._close_dialog(menu), self._toggle_quick_product(product_id)),
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.DELETE, color=ft.Colors.RED_600),
                    title=ft.Text("Sil", style=ft.TextStyle(color=ft.Colors.RED_600)),
                    on_click=lambda _: (self._close_dialog(menu), self._confirm_delete(product_id, product_name)),
                ),
            ], tight=True, spacing=0),
            actions=[ft.TextButton("Kapat", on_click=lambda _: self._close_dialog(menu))],
        )
        self._open_dialog(menu)

    # ── Cache ve refresh ──────────────────────────────────────────────────────

    def invalidate_cache(self):
        self._table_query_key = ("", "")
        self._table_page_index = 0

    def refresh(self):
        self._load_category_dropdowns()
        self._load_suppliers()
        self.refresh_table(force_reload=True)
        self._refresh_taxonomy_lists()

    def _goto_prev_page(self):
        if self._table_page_index <= 0:
            return
        self._table_page_index -= 1
        self.refresh_table()

    def _goto_next_page(self):
        max_page = max(0, (self._table_total - 1) // self._table_page_size)
        if self._table_page_index >= max_page:
            return
        self._table_page_index += 1
        self.refresh_table()

    def _schedule_refresh_table(self, delay: float = 0.25):
        try:
            if self._search_timer:
                self._search_timer.cancel()
        except Exception:
            pass
        import threading
        self._search_timer = threading.Timer(delay, self.refresh_table)
        self._search_timer.daemon = True
        self._search_timer.start()

    def schedule_refresh_table(self, *, force_reload: bool = False, delay: float = 0.05):
        try:
            if self._search_timer:
                self._search_timer.cancel()
        except Exception:
            pass
        import threading
        self._search_timer = threading.Timer(delay, lambda: self.refresh_table(force_reload=force_reload))
        self._search_timer.daemon = True
        self._search_timer.start()

    def refresh_table(self, force_reload: bool = False):
        try:
            search = (self.txt_search.value or "").strip().lower() if hasattr(self, "txt_search") else ""
            group_filter = (self.dd_filter_group.value or "") if hasattr(self, "dd_filter_group") else ""
            query_key = (search, group_filter)
            if query_key != self._table_query_key:
                self._table_query_key = query_key
                self._table_page_index = 0

            self._table_total = self.db.count_products(search=search, category=group_filter)
            self._show_list_images = self._table_total <= 5000
            max_page = max(0, (self._table_total - 1) // self._table_page_size) if self._table_total else 0
            if self._table_page_index > max_page:
                self._table_page_index = max_page
            offset = self._table_page_index * self._table_page_size
            rows = self.db.search_products(
                search=search,
                category=group_filter,
                limit=self._table_page_size,
                offset=offset,
            )

            self._refresh_quick_add_options_from_search()
            self._refresh_quick_selection_panel()

            if not rows:
                self.lbl_page_info.value = "0 urun"
                self.btn_page_prev.disabled = True
                self.btn_page_next.disabled = True
                self.products_list.controls = [
                    ft.Container(
                        padding=ft.padding.symmetric(vertical=12),
                        content=ft.Text("Urun bulunamadi", color=ft.Colors.BLUE_GREY_400),
                    )
                ]
            else:
                total_pages = max_page + 1 if self._table_total else 1
                self.lbl_page_info.value = (
                    f"Sayfa {self._table_page_index + 1}/{total_pages} | Toplam {self._table_total}"
                )
                self.btn_page_prev.disabled = self._table_page_index <= 0
                self.btn_page_next.disabled = self._table_page_index >= max_page
                self.products_list.controls = [self._build_product_row(r) for r in rows]
            self._safe_update()
        except Exception as ex:
            try:
                self.products_list.controls = [
                    ft.Container(
                        padding=ft.padding.symmetric(vertical=12),
                        content=ft.Text(f"Yukleme hatasi: {ex}", color=ft.Colors.RED_400),
                    )
                ]
                self._safe_update()
            except Exception:
                pass
