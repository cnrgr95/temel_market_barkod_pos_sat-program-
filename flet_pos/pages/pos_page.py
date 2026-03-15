import os
from datetime import datetime
import inspect
import asyncio
import flet as ft

# Banknot değerleri (TL)
_BANKNOTES = [1, 5, 10, 20, 50, 100, 200]


class POSPage(ft.Container):
    def __init__(self, db, on_sale_completed=None, current_user=None, on_unknown_barcode=None):
        super().__init__(expand=True, padding=0)
        self.db = db
        self.on_sale_completed = on_sale_completed
        self.current_user = current_user or {}
        self.on_unknown_barcode = on_unknown_barcode
        self._last_unknown_barcode = ""
        self._unknown_barcode_value = ""
        self._unknown_search_value = ""

        # 4 bağımsız sepet
        self._baskets: list[list[dict]] = [[], [], [], []]
        self._active_basket: int = 0
        self._category_filter: str = ""

        # ── Sol panel alanları ───────────────────────────────────────────────
        self.lbl_total = ft.Text(
            "0,00 ₺", size=38, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE,
            text_align=ft.TextAlign.RIGHT,
        )
        self.lbl_change_big = ft.Text(
            "Para Üstü: 0,00 ₺", size=14, weight=ft.FontWeight.W_600,
            color=ft.Colors.GREEN_700,
        )

        # Sepet sekme butonları
        self._basket_tab_row = ft.Row(spacing=4)

        # Barkod
        self.txt_barcode = ft.TextField(
            label="BARKOD NO",
            expand=True,
            border_color=ft.Colors.BLUE_700,
            bgcolor=ft.Colors.WHITE,
            on_submit=lambda _: self._add_by_barcode(),
            on_change=lambda _: self._on_barcode_changed(),
            text_size=15,
            autofocus=True,
        )
        self.unknown_barcode_hint = ft.Container(
            visible=False,
            bgcolor=ft.Colors.ORANGE_50,
            border=ft.border.all(1, ft.Colors.ORANGE_200),
            border_radius=6,
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            on_click=lambda _: self._open_unknown_from_hint("barcode"),
            content=ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.ORANGE_700, size=14),
                ft.Text("Ürün bulunamadı", size=11, color=ft.Colors.ORANGE_800, expand=True),
                ft.ElevatedButton(
                    "Ürünü Ekle",
                    icon=ft.Icons.ADD_BOX,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.ORANGE_100,
                        color=ft.Colors.ORANGE_800,
                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                    ),
                    height=28,
                    on_click=lambda _: self._open_unknown_from_hint("barcode"),
                ),
            ], spacing=6),
        )

        # Adet
        self.txt_qty = ft.TextField(label="Adet / Kg", width=90, value="1",
                                     bgcolor=ft.Colors.WHITE)

        # İskonto
        self.txt_discount_pct = ft.TextField(
            label="% İSKONTO", width=100, value="0", bgcolor=ft.Colors.WHITE,
            on_change=lambda _: self._on_discount_pct_changed(),
        )
        self.txt_discount_amt = ft.TextField(
            label="İSKONTO TL", width=110, value="0.00", bgcolor=ft.Colors.WHITE,
            on_change=lambda _: self._update_totals(),
            read_only=True,
        )

        # Alınan para
        self.txt_received = ft.TextField(
            label="ALINAN PARA",
            bgcolor=ft.Colors.WHITE,
            expand=True,
            value="0",
            text_size=18,
            on_change=lambda _: self._update_totals(),
        )

        self.lbl_change_val = ft.Text(
            "0,00", size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700,
            text_align=ft.TextAlign.RIGHT,
        )
        self.lbl_change_title = ft.Text(
            "PARA ÜSTÜ", size=11, color=ft.Colors.GREEN_700, weight=ft.FontWeight.W_600, expand=True
        )
        self.ico_change = ft.Icon(ft.Icons.CURRENCY_LIRA, color=ft.Colors.GREEN_700, size=20)

        # ── Sağ panel alanları ───────────────────────────────────────────────
        self.dd_product_picker = ft.Dropdown(
            label="Listeden Urun Sec", expand=True, options=[],
        )
        self.dd_product_picker.on_select = lambda _: self._on_dropdown_changed()

        self.dd_customer = ft.Dropdown(
            label="Veresiye Musteri", expand=True, options=[], visible=False,
        )

        # Sepet listesi (sağ panel)
        self.cart_list = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=3)

        # Ürün arama
        self.txt_search = ft.TextField(
            label="Urun Ara... (Barkod ile ara: Enter)",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            on_change=lambda _: self._on_search_changed(),
            on_submit=lambda _: self._search_and_add(),
            bgcolor=ft.Colors.WHITE,
        )
        self.unknown_search_hint = ft.Container(
            visible=False,
            bgcolor=ft.Colors.ORANGE_50,
            border=ft.border.all(1, ft.Colors.ORANGE_200),
            border_radius=6,
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            on_click=lambda _: self._open_unknown_from_hint("search"),
            content=ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.ORANGE_700, size=14),
                ft.Text("Ürün bulunamadı", size=11, color=ft.Colors.ORANGE_800, expand=True),
                ft.ElevatedButton(
                    "Ürünü Ekle",
                    icon=ft.Icons.ADD_BOX,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.ORANGE_100,
                        color=ft.Colors.ORANGE_800,
                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                    ),
                    height=28,
                    on_click=lambda _: self._open_unknown_from_hint("search"),
                ),
            ], spacing=6),
        )

        # Kategori satırı
        self.tabs_category = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=4)

        # Ürün grid
        self.products_grid = ft.GridView(
            expand=True, max_extent=160, child_aspect_ratio=0.9,
            spacing=4, run_spacing=4,
        )

        # ── Layout ───────────────────────────────────────────────────────────
        self._build_basket_tabs()
        self.content = ft.Row(
            expand=True, spacing=0,
            controls=[
                self._build_left_panel(),
                ft.VerticalDivider(width=1, color=ft.Colors.BLUE_GREY_200),
                self._build_right_panel(),
            ],
        )

        self.refresh_customers()
        self.refresh_products_grid()
        self.set_responsive(1280)

    # ── Sol panel ─────────────────────────────────────────────────────────────

    def _build_left_panel(self):
        # Banknot butonları
        banknote_row = ft.Row(
            wrap=True, spacing=4, run_spacing=4,
            controls=[
                ft.ElevatedButton(
                    f"{v} ₺",
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.WHITE,
                        color=ft.Colors.BLUE_GREY_800,
                        side=ft.BorderSide(1, ft.Colors.BLUE_GREY_300),
                        shape=ft.RoundedRectangleBorder(radius=6),
                        padding=ft.padding.symmetric(horizontal=4, vertical=2),
                    ),
                    height=32,
                    on_click=lambda _, v=v: self._add_banknote(v),
                )
                for v in _BANKNOTES
            ],
        )
        self.change_box = ft.Container(
            bgcolor=ft.Colors.GREEN_50,
            border_radius=8,
            border=ft.border.all(1, ft.Colors.GREEN_300),
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            margin=ft.margin.symmetric(horizontal=8),
            content=ft.Row([
                self.lbl_change_title,
                ft.Row([
                    self.ico_change,
                    self.lbl_change_val,
                ], spacing=2),
            ]),
        )

        return ft.Container(
            width=270,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border=ft.border.only(right=ft.BorderSide(1, ft.Colors.BLUE_GREY_200)),
            content=ft.Column(
                scroll=ft.ScrollMode.AUTO,
                spacing=8,
                expand=True,
                controls=[
                    # ── Toplam kutusu ─────────────────────────────
                    ft.Container(
                        bgcolor=ft.Colors.INDIGO_800,
                        border_radius=10,
                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                        margin=ft.margin.only(top=8, left=8, right=8),
                        content=ft.Column([
                            ft.Text("TOPLAM TUTAR", size=10, color=ft.Colors.WHITE70,
                                    weight=ft.FontWeight.W_600),
                            self.lbl_total,
                        ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.END),
                    ),
                    # ── Sepet sekmeleri ────────────────────────────
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=8),
                        content=self._basket_tab_row,
                    ),
                    # ── Barkod + Adet ─────────────────────────────
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=8),
                        content=ft.Column(
                            [
                                ft.Row([self.txt_barcode, self.txt_qty], spacing=6),
                                self.unknown_barcode_hint,
                            ],
                            spacing=4,
                        ),
                    ),
                    # dd_product_picker görünmez — sadece senkronizasyon için tutulur
                    ft.Container(content=self.dd_product_picker, visible=False, height=0),
                    # ── İskonto ───────────────────────────────────
                    ft.Container(
                        bgcolor=ft.Colors.WHITE,
                        border_radius=8,
                        border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
                        padding=ft.padding.symmetric(horizontal=10, vertical=6),
                        margin=ft.margin.symmetric(horizontal=8),
                        content=ft.Column([
                            ft.Text("İSKONTO", size=10, color=ft.Colors.BLUE_GREY_500,
                                    weight=ft.FontWeight.W_600),
                            ft.Row([self.txt_discount_pct, self.txt_discount_amt], spacing=4),
                        ], spacing=4),
                    ),
                    # ── Alınan para ───────────────────────────────
                    ft.Container(
                        bgcolor=ft.Colors.WHITE,
                        border_radius=8,
                        border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
                        padding=ft.padding.symmetric(horizontal=10, vertical=6),
                        margin=ft.margin.symmetric(horizontal=8),
                        content=ft.Column([
                            ft.Text("ALINAN PARA (₺)", size=10, color=ft.Colors.BLUE_GREY_500),
                            self.txt_received,
                        ], spacing=4),
                    ),
                    # ── Para üstü / kalan bakiye ──────────────────
                    self.change_box,
                    # ── Hızlı nakit ───────────────────────────────
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=8),
                        content=ft.Column([
                            ft.Text("HIZLI NAKİT SEÇİMİ", size=10,
                                    color=ft.Colors.BLUE_GREY_400, weight=ft.FontWeight.W_600),
                            banknote_row,
                        ], spacing=4),
                    ),
                    # ── Veresiye müşteri ──────────────────────────
                    ft.Container(
                        padding=ft.padding.only(left=8, right=8, bottom=10),
                        content=self.dd_customer,
                    ),
                ],
            ),
        )

    # ── Sağ panel ─────────────────────────────────────────────────────────────

    def _build_right_panel(self):
        def _pay_btn(label, icon, color, action):
            return ft.ElevatedButton(
                label, icon=icon,
                style=ft.ButtonStyle(
                    bgcolor=color, color=ft.Colors.WHITE,
                    shape=ft.RoundedRectangleBorder(radius=6),
                    padding=ft.padding.symmetric(horizontal=10, vertical=0),
                ),
                height=40,
                on_click=lambda _: action(),
            )

        # ── Ödeme butonları (üst bar) ──────────────────────────────────────
        action_bar = ft.Container(
            bgcolor=ft.Colors.GREY_50,
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.BLUE_GREY_200)),
            padding=ft.padding.symmetric(horizontal=8, vertical=6),
            content=ft.Column([
                # 1. satır: ödeme butonları
                ft.Row([
                    _pay_btn("NAKİT (F1)", ft.Icons.PAYMENTS,
                             ft.Colors.GREEN_700, lambda: self._quick_pay("NAKIT")),
                    _pay_btn("KREDİ KARTI (F2)", ft.Icons.CREDIT_CARD,
                             ft.Colors.BLUE_700, lambda: self._quick_pay("POS")),
                    _pay_btn("NAKIT+KART (F3)", ft.Icons.CALL_SPLIT,
                             ft.Colors.ORANGE_700, self._show_payment_split_dialog),
                    _pay_btn("HAVALE (F4)", ft.Icons.ACCOUNT_BALANCE,
                             ft.Colors.TEAL_700, lambda: self._quick_pay("HAVALE")),
                    _pay_btn("VERESİYE (F5)", ft.Icons.PERSON_PIN,
                             ft.Colors.PURPLE_700, lambda: self._quick_pay("VERESIYE")),
                ], spacing=6, wrap=True),
                # 2. satır: iptal + iade
                ft.Row([
                    ft.OutlinedButton(
                        "Satışı İptal (F6)", icon=ft.Icons.CANCEL,
                        style=ft.ButtonStyle(
                            color=ft.Colors.RED_600,
                            side=ft.BorderSide(1, ft.Colors.RED_300),
                            shape=ft.RoundedRectangleBorder(radius=6),
                        ),
                        height=36,
                        on_click=lambda _: self._clear_cart(),
                    ),
                    ft.OutlinedButton(
                        "İade Al (F7)", icon=ft.Icons.KEYBOARD_RETURN,
                        style=ft.ButtonStyle(
                            color=ft.Colors.ORANGE_700,
                            side=ft.BorderSide(1, ft.Colors.ORANGE_300),
                            shape=ft.RoundedRectangleBorder(radius=6),
                        ),
                        height=36,
                        on_click=self._complete_return,
                    ),
                ], spacing=6),
            ], spacing=5),
        )

        # ── Sepet başlığı ─────────────────────────────────────────────────
        cart_header = ft.Container(
            bgcolor=ft.Colors.INDIGO_50,
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.INDIGO_100)),
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            content=ft.Row([
                ft.Text("ÜRÜN ADI", size=11, weight=ft.FontWeight.W_700,
                        color=ft.Colors.INDIGO_800, expand=True),
                ft.Text("MİKTAR", size=11, weight=ft.FontWeight.W_700,
                        color=ft.Colors.INDIGO_800, width=65, text_align=ft.TextAlign.RIGHT),
                ft.Text("FİYAT", size=11, weight=ft.FontWeight.W_700,
                        color=ft.Colors.INDIGO_800, width=70, text_align=ft.TextAlign.RIGHT),
                ft.Text("TUTAR", size=11, weight=ft.FontWeight.W_700,
                        color=ft.Colors.INDIGO_800, width=75, text_align=ft.TextAlign.RIGHT),
                ft.Container(width=44),
            ]),
        )

        # ── Arama + kategori satırı ────────────────────────────────────────
        search_row = ft.Container(
            bgcolor=ft.Colors.WHITE,
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.BLUE_GREY_100)),
            padding=ft.padding.symmetric(horizontal=6, vertical=4),
            content=ft.Column([
                ft.Row([self.txt_search], spacing=6),
                self.unknown_search_hint,
                self.tabs_category,
            ], spacing=4),
        )

        return ft.Container(
            expand=True,
            bgcolor=ft.Colors.WHITE,
            content=ft.Column(
                expand=True, spacing=0,
                controls=[
                    action_bar,
                    cart_header,
                    # Sepet listesi — expand ile dinamik yükseklik
                    ft.Container(
                        content=self.cart_list,
                        bgcolor=ft.Colors.GREY_50,
                        expand=2,
                        padding=ft.padding.all(4),
                    ),
                    search_row,
                    # Ürün grid — expand ile daha büyük alan
                    ft.Container(
                        content=self.products_grid,
                        expand=3,
                        bgcolor=ft.Colors.GREY_100,
                        padding=ft.padding.all(6),
                    ),
                ],
            ),
        )

    # ── Yardımcı ──────────────────────────────────────────────────────────────

    def _safe_update(self):
        try:
            _ = self.page
            self.update()
        except RuntimeError:
            pass

    def _run_ui_call(self, result):
        if inspect.isawaitable(result):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(result)
            except RuntimeError:
                pass

    def handle_keyboard_shortcut(self, e: ft.KeyboardEvent) -> bool:
        """POS ekranı için global kısayol tuşları."""
        key = (e.key or "").upper()
        if not key:
            return False
        if bool(getattr(e, "ctrl", False)) or bool(getattr(e, "alt", False)) or bool(getattr(e, "meta", False)):
            return False

        actions = {
            "F1": lambda: self._quick_pay("NAKIT"),
            "F2": lambda: self._quick_pay("POS"),
            "F3": self._show_payment_split_dialog,
            "F4": lambda: self._quick_pay("HAVALE"),
            "F5": lambda: self._quick_pay("VERESIYE"),
            "F6": self._clear_cart,
            "F7": lambda: self._complete_return(None),
        }
        action = actions.get(key)
        if not action:
            return False
        action()
        return True

    def _snack(self, text: str):
        try:
            self.page.snack_bar = ft.SnackBar(ft.Text(text), open=True)
            self.page.update()
        except RuntimeError:
            pass

    def _to_float(self, value, default: float = 0.0) -> float:
        try:
            return float((str(value) or "").replace(",", "."))
        except (ValueError, TypeError):
            return default

    # ── Sepet sekmeleri ───────────────────────────────────────────────────────

    @property
    def cart(self) -> list[dict]:
        return self._baskets[self._active_basket]

    def _build_basket_tabs(self):
        self._basket_tab_row.controls = []
        for i in range(4):
            n = len(self._baskets[i])
            subtotal = sum(x["line_total"] for x in self._baskets[i])
            label = f"SEPET {i+1}"
            if n:
                label += f"\n{subtotal:.2f}₺"
            selected = i == self._active_basket
            self._basket_tab_row.controls.append(
                ft.ElevatedButton(
                    label,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.INDIGO_700 if selected else ft.Colors.WHITE,
                        color=ft.Colors.WHITE if selected else ft.Colors.BLUE_GREY_700,
                        side=ft.BorderSide(1, ft.Colors.INDIGO_300),
                        shape=ft.RoundedRectangleBorder(radius=6),
                        padding=ft.padding.symmetric(horizontal=6, vertical=4),
                    ),
                    height=46,
                    on_click=lambda _, idx=i: self._switch_basket(idx),
                )
            )

    def _switch_basket(self, idx: int):
        self._active_basket = idx
        self._build_basket_tabs()
        self._refresh_cart_ui()

    # ── Kategori sekmeleri ────────────────────────────────────────────────────

    def _build_category_tabs(self):
        try:
            cats_db = self.db.list_categories()
        except Exception:
            cats_db = []
        cats = ["TUMU"] + cats_db
        self.tabs_category.controls = []
        for cat in cats:
            selected = (self._category_filter == cat) or (cat == "TUMU" and not self._category_filter)
            self.tabs_category.controls.append(
                ft.ElevatedButton(
                    cat,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.INDIGO_700 if selected else ft.Colors.WHITE,
                        color=ft.Colors.WHITE if selected else ft.Colors.BLUE_GREY_700,
                        side=ft.BorderSide(1, ft.Colors.BLUE_GREY_200),
                        shape=ft.RoundedRectangleBorder(radius=16),
                        padding=ft.padding.symmetric(horizontal=10, vertical=2),
                    ),
                    height=30,
                    on_click=lambda _, c=cat: self._filter_category(c),
                )
            )

    def _filter_category(self, cat: str):
        self._category_filter = "" if cat == "TUMU" else cat
        self.refresh_products_grid()

    # ── Barkod / dropdown senkron ─────────────────────────────────────────────

    def _on_barcode_changed(self):
        barcode = self._normalize_barcode(self.txt_barcode.value)
        self._hide_unknown_prompt("barcode")
        if not barcode:
            return
        all_rows = self.db.list_products()

        # Tam barkod eşleşmesi → otomatik sepete ekle (barkod okuyucu gibi)
        exact = next((r for r in all_rows if (r[2] or "") == barcode), None)
        if exact:
            self._add_product_to_cart(exact)
            self.txt_barcode.value = ""
            self.dd_product_picker.value = None
            self._safe_update()
            return

        # Kısmi eşleşme → dropdown'ı güncelle (elle yazarken yardımcı)
        partial = next((r for r in all_rows if (r[2] or "").startswith(barcode)), None)
        if partial:
            key = f"{partial[0]} - {partial[1]}"
            if self.dd_product_picker.value != key:
                self.dd_product_picker.value = key
                self._safe_update()
            return
        if self._looks_like_barcode(barcode):
            self._show_unknown_prompt("barcode", barcode)

    def _on_search_changed(self):
        query = self._normalize_barcode(self.txt_search.value)
        # Her değişimde grid filtresi çalışsın
        self.refresh_products_grid()
        self._hide_unknown_prompt("search")
        if not query:
            return
        # Barkod formatındaysa Enter beklemeden otomatik eklemeyi dene
        if not self._looks_like_barcode(query):
            return
        row = self.db.get_product_by_barcode(query)
        if row:
            self._add_product_to_cart(row)
            self.txt_search.value = ""
            self.refresh_products_grid()
            self._safe_update()
            return
        if self._looks_like_barcode(query):
            self._show_unknown_prompt("search", query)

    def _on_dropdown_changed(self):
        if not self.dd_product_picker.value:
            return
        try:
            pid = int(self.dd_product_picker.value.split(" - ")[0])
        except (ValueError, IndexError):
            return
        row = next((r for r in self.db.list_products() if r[0] == pid), None)
        if row and self.txt_barcode.value != (row[2] or ""):
            self.txt_barcode.value = row[2] or ""
            self._safe_update()

    def _search_and_add(self):
        """Ürün Ara alanından Enter'a basıldığında çalışır.
        Önce tam barkod eşleşmesi arar, yoksa isim eşleşmesi dener.
        Tek sonuç varsa direkt ekler, yoksa dialog gösterir."""
        query = self._normalize_barcode(self.txt_search.value)
        if not query:
            return

        # 1) Tam barkod eşleşmesi
        row = self.db.get_product_by_barcode(query)
        if row:
            self._add_product_to_cart(row)
            self.txt_search.value = ""
            self._hide_unknown_prompt("search")
            self.refresh_products_grid()
            self._safe_update()
            return

        # 2) İsme göre arama — tek eşleşme varsa direkt ekle
        all_rows = self.db.list_products()
        q_lower = query.lower()
        matches = [r for r in all_rows
                   if q_lower in (r[1] or "").lower() or q_lower in (r[2] or "").lower()]

        if len(matches) == 1:
            self._add_product_to_cart(matches[0])
            self.txt_search.value = ""
            self.refresh_products_grid()
            self._safe_update()
            return

        if len(matches) > 1:
            # Birden fazla sonuç — grid zaten filtreli gösteriyor, kullanıcı seçsin
            self._snack(f"{len(matches)} ürün bulundu — listeden seçin")
            return

        # 3) Hiç bulunamadı
        if self._looks_like_barcode(query):
            self._show_barcode_not_found_dialog(query)
        else:
            self._snack("Ürün bulunamadı")

    def _add_by_barcode(self):
        barcode = self._normalize_barcode(self.txt_barcode.value)
        if not barcode:
            return
        row = self.db.get_product_by_barcode(barcode)
        if row:
            self._add_product_to_cart(row)
            self.txt_barcode.value = ""
            self._hide_unknown_prompt("barcode")
            self.dd_product_picker.value = None
            self._safe_update()
        else:
            self._show_barcode_not_found_dialog(barcode)

    def _show_barcode_not_found_dialog(self, barcode: str, force: bool = False) -> bool:
        """Barkod yoksa kullanıcıyı Ürün Ekle sayfasına yönlendirmeyi sor."""
        if not barcode:
            return False
        # Aynı barkod için tekrar tekrar dialog spam'ini engelle
        if (not force) and self._last_unknown_barcode == barcode:
            return False
        self._last_unknown_barcode = barcode

        def _close(_e):
            dlg.open = False
            self.page.update()
            self._last_unknown_barcode = ""

        def _go_add(_e):
            dlg.open = False
            self.page.update()
            self._last_unknown_barcode = ""
            self.txt_barcode.value = ""
            self.txt_search.value = ""
            self._hide_unknown_prompt("all")
            self._safe_update()
            if callable(self.on_unknown_barcode):
                self.on_unknown_barcode(barcode)
            else:
                self._snack("Ürün ekleme sayfasına geçilemedi")

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.QR_CODE_SCANNER, color=ft.Colors.ORANGE_700, size=22),
                ft.Text("Ürün bulunamadı", size=14, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ORANGE_700),
            ], spacing=8),
            content=ft.Container(
                width=440,
                content=ft.Column([
                    ft.Text(f"Barkod: {barcode}", size=13, color=ft.Colors.BLUE_GREY_700),
                    ft.Text("Bu ürün sistemde kayıtlı değil.", size=13, color=ft.Colors.GREY_700),
                    ft.Text("Ürün eklemek ister misiniz?", size=13, color=ft.Colors.GREY_700),
                ], spacing=8, tight=True),
            ),
            actions=[
                ft.TextButton("Hayır", icon=ft.Icons.CLOSE, on_click=_close),
                ft.ElevatedButton(
                    "Evet, Ürün Ekle",
                    icon=ft.Icons.ADD_BOX,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE),
                    on_click=_go_add,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        try:
            self.page.dialog = dlg
            dlg.open = True
            self.page.update()
            return True
        except Exception:
            return False

    def _open_unknown_from_hint(self, source: str):
        if source == "barcode":
            barcode = self._normalize_barcode(
                self._unknown_barcode_value or self.txt_barcode.value or self._last_unknown_barcode
            )
        else:
            barcode = self._normalize_barcode(
                self._unknown_search_value or self.txt_search.value or self._last_unknown_barcode
            )
        if not barcode:
            self._snack("Önce barkod giriniz")
            return
        # Hintteki "Ürünü Ekle" tıklamasında doğrudan ürün ekleme sayfasına git.
        # (Dialog akışı Enter/Submit senaryosunda zaten devam ediyor.)
        if callable(self.on_unknown_barcode):
            try:
                self.on_unknown_barcode(barcode)
            except Exception as ex:
                self._snack(f"Ürün ekleme sayfası açılamadı: {ex}")
        else:
            self._snack("Ürün ekleme sayfasına geçiş bağlı değil")

    def _normalize_barcode(self, value: str | None) -> str:
        raw = str(value or "")
        v = raw.strip().replace(" ", "").replace("\t", "").replace("\r", "").replace("\n", "")
        # Scanner kaynaklı kontrol karakterlerini temizle
        v = "".join(ch for ch in v if ord(ch) >= 32)
        # Baş/son tırnakları temizle (örn: '123456...)
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"', "`"):
            v = v[1:-1]
        if v.startswith(("'", '"', "`")):
            v = v[1:]
        if v.endswith(("'", '"', "`")):
            v = v[:-1]
        return v.strip()

    def _looks_like_barcode(self, value: str) -> bool:
        # Sabit hane yok: boş değilse ve boşluk içermiyorsa barkod adayı kabul et
        v = (value or "").strip()
        return bool(v) and (" " not in v) and (len(v) >= 3)

    def _show_unknown_prompt(self, source: str, barcode: str):
        if source == "barcode":
            self._unknown_barcode_value = barcode
            self.unknown_barcode_hint.visible = True
        elif source == "search":
            self._unknown_search_value = barcode
            self.unknown_search_hint.visible = True
        self._safe_update()

    def _hide_unknown_prompt(self, source: str):
        if source in ("barcode", "all"):
            self._unknown_barcode_value = ""
            self.unknown_barcode_hint.visible = False
        if source in ("search", "all"):
            self._unknown_search_value = ""
            self.unknown_search_hint.visible = False

    def _add_selected_product(self):
        if not self.dd_product_picker.value:
            return
        try:
            pid = int(self.dd_product_picker.value.split(" - ")[0])
        except (ValueError, IndexError):
            return
        row = next((r for r in self.db.list_products() if r[0] == pid), None)
        if row:
            self._add_product_to_cart(row)

    # ── Ürün grid ─────────────────────────────────────────────────────────────

    def refresh_products_grid(self):
        search = (self.txt_search.value or "").strip().lower()
        all_rows = self.db.list_products()

        if self._category_filter:
            filtered = []
            for r in all_rows:
                try:
                    full = self.db.get_product_full(r[0])
                    if full and (full[4] or "") == self._category_filter:
                        filtered.append(r)
                except Exception:
                    pass
            rows = filtered
        else:
            rows = all_rows

        if search:
            rows = [r for r in rows if search in (r[1] or "").lower() or search in (r[2] or "").lower()]

        self._build_category_tabs()
        self.products_grid.controls = [self._product_card(r) for r in rows]
        self.dd_product_picker.options = [ft.dropdown.Option(f"{r[0]} - {r[1]}") for r in all_rows]
        self._safe_update()

    def refresh_customers(self):
        rows = self.db.list_customers()
        self.dd_customer.options = [ft.dropdown.Option(f"{r[0]} - {r[1]}") for r in rows]
        self._safe_update()

    def _product_card(self, row):
        _product_id, name, _barcode, unit, price_incl, vat_rate, stock, image_path, _is_scale, *_ = row
        has_img = image_path and os.path.exists(image_path)
        stok_color = ft.Colors.RED_700 if stock <= 0 else (ft.Colors.ORANGE_700 if stock < 5 else ft.Colors.GREEN_800)

        inner = ft.Container(
            padding=ft.padding.all(6),
            bgcolor=ft.Colors.WHITE,
            border_radius=8,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=3, tight=True,
                controls=[
                    ft.Image(src=image_path, height=60, fit=ft.BoxFit.COVER, border_radius=4)
                    if has_img else
                    ft.Container(height=50, alignment=ft.Alignment(0, 0),
                                  content=ft.Icon(ft.Icons.SHOPPING_BAG, size=32,
                                                  color=ft.Colors.BLUE_GREY_300)),
                    ft.Text(name, size=10, weight=ft.FontWeight.W_600,
                            text_align=ft.TextAlign.CENTER, max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(f"{price_incl:.2f} ₺", size=12, weight=ft.FontWeight.BOLD,
                            color=ft.Colors.INDIGO_700),
                    ft.Text(f"Stok: {stock:.0f}", size=9, color=stok_color),
                ],
            ),
        )
        return ft.GestureDetector(
            on_tap=lambda _, r=row: self._add_product_to_cart(r),
            mouse_cursor=ft.MouseCursor.CLICK,
            content=ft.Card(elevation=1, margin=ft.margin.all(2), content=inner),
        )

    # ── Sepet işlemleri ───────────────────────────────────────────────────────

    def _add_product_to_cart(self, row):
        qty = self._to_float(self.txt_qty.value, 1.0)
        if qty <= 0:
            qty = 1.0
        product_id, name, barcode, unit, price_incl, vat_rate, stock, image_path = (
            row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7] if len(row) > 7 else ""
        )
        already = sum(i["qty"] for i in self.cart if i["product_id"] == product_id)
        if stock < already + qty:
            self._snack(f"Yetersiz stok: {name}  (mevcut: {stock:.0f})")
            return
        existing = next((i for i in self.cart if i["product_id"] == product_id), None)
        if existing:
            existing["qty"] += qty
            existing["line_total"] = existing["qty"] * existing["price"] - existing["item_discount"]
        else:
            self.cart.append({
                "product_id": product_id, "name": name, "barcode": barcode,
                "unit": unit, "price": float(price_incl), "vat_rate": float(vat_rate),
                "image_path": image_path or "",
                "qty": qty, "item_discount": 0.0, "line_total": qty * float(price_incl),
            })
        self._after_successful_add()
        self._refresh_cart_ui()

    def _after_successful_add(self):
        """Ürün eklendikten sonra barkod/arama alanlarını otomatik temizle."""
        self.txt_barcode.value = ""
        self.txt_search.value = ""
        self._hide_unknown_prompt("all")
        try:
            self._run_ui_call(self.txt_barcode.focus())
        except Exception:
            pass

    def _change_qty(self, bi: int, ii: int, delta: float):
        basket = self._baskets[bi]
        item = basket[ii]
        new_qty = item["qty"] + delta
        if new_qty <= 0:
            basket.pop(ii)
        else:
            item["qty"] = new_qty
            item["line_total"] = item["qty"] * item["price"] - item["item_discount"]
        if bi == self._active_basket:
            self._refresh_cart_ui()

    def _remove_item(self, bi: int, ii: int):
        self._baskets[bi].pop(ii)
        if bi == self._active_basket:
            self._refresh_cart_ui()

    def _refresh_cart_ui(self):
        self._build_basket_tabs()
        if not self.cart:
            self.cart_list.controls = [
                ft.Container(
                    padding=ft.padding.symmetric(vertical=20),
                    alignment=ft.Alignment(0, 0),
                    content=ft.Text("Sepet boş", color=ft.Colors.BLUE_GREY_400, italic=True),
                )
            ]
            self._update_totals()
            self._safe_update()
            return
        bi = self._active_basket
        controls = []
        for idx, item in enumerate(self.cart):
            img_path = item.get("image_path", "")
            has_img = bool(img_path) and os.path.exists(img_path)
            controls.append(
                ft.Container(
                    bgcolor=ft.Colors.WHITE if idx % 2 == 0 else ft.Colors.BLUE_GREY_50,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    content=ft.Row([
                        ft.Container(
                            width=30,
                            height=30,
                            border_radius=4,
                            clip_behavior=ft.ClipBehavior.HARD_EDGE,
                            bgcolor=ft.Colors.GREY_100,
                            content=(
                                ft.Image(src=img_path, fit=ft.BoxFit.COVER, width=30, height=30)
                                if has_img else
                                ft.Icon(ft.Icons.IMAGE, size=16, color=ft.Colors.GREY_500)
                            ),
                        ),
                        ft.Text(f"• {item['name']}", size=11, expand=True,
                                weight=ft.FontWeight.W_500, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(f"{item['qty']:.2f}", size=11, width=56,
                                text_align=ft.TextAlign.RIGHT),
                        ft.Text(item['unit'], size=11, width=38, text_align=ft.TextAlign.RIGHT,
                                color=ft.Colors.BLUE_GREY_600),
                        ft.Text(f"{item['price']:.2f}", size=11, width=58,
                                text_align=ft.TextAlign.RIGHT),
                        ft.Text(f"{item['line_total']:.2f}", size=11, width=62,
                                weight=ft.FontWeight.W_600, text_align=ft.TextAlign.RIGHT,
                                color=ft.Colors.INDIGO_700),
                        ft.Row([
                            ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, icon_size=14,
                                          padding=0, icon_color=ft.Colors.ORANGE_600,
                                          on_click=lambda _, b=bi, i=idx: self._change_qty(b, i, -1)),
                            ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE, icon_size=14,
                                          padding=0, icon_color=ft.Colors.GREEN_600,
                                          on_click=lambda _, b=bi, i=idx: self._change_qty(b, i, 1)),
                            ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=14,
                                          padding=0, icon_color=ft.Colors.RED_400,
                                          on_click=lambda _, b=bi, i=idx: self._remove_item(b, i)),
                        ], spacing=0, width=50),
                    ]),
                )
            )
        self.cart_list.controls = controls
        self._update_totals()
        self._safe_update()

    def _on_discount_pct_changed(self):
        subtotal = sum(i["line_total"] for i in self.cart)
        pct = self._to_float(self.txt_discount_pct.value, 0)
        amt = subtotal * pct / 100.0
        self.txt_discount_amt.value = f"{amt:.2f}"
        self._update_totals()

    def _update_totals(self):
        subtotal = sum(i["line_total"] for i in self.cart)
        discount = self._to_float(self.txt_discount_amt.value, 0)
        total = max(0.0, subtotal - discount)
        received = self._to_float(self.txt_received.value, 0)
        delta = received - total
        self.lbl_total.value = f"{total:,.2f} ₺"
        self.lbl_change_val.value = f"{delta:,.2f}"
        if delta >= 0:
            self.lbl_change_title.value = "PARA ÜSTÜ"
            self.lbl_change_title.color = ft.Colors.GREEN_700
            self.lbl_change_val.color = ft.Colors.GREEN_700
            self.ico_change.name = ft.Icons.CURRENCY_LIRA
            self.ico_change.color = ft.Colors.GREEN_700
            self.change_box.bgcolor = ft.Colors.GREEN_50
            self.change_box.border = ft.border.all(1, ft.Colors.GREEN_300)
        else:
            self.lbl_change_title.value = "KALAN BAKİYE"
            self.lbl_change_title.color = ft.Colors.RED_700
            self.lbl_change_val.color = ft.Colors.RED_700
            self.ico_change.name = ft.Icons.ERROR_OUTLINE
            self.ico_change.color = ft.Colors.RED_700
            self.change_box.bgcolor = ft.Colors.RED_50
            self.change_box.border = ft.border.all(1, ft.Colors.RED_300)
        self._safe_update()

    def _add_banknote(self, amount: float):
        current = self._to_float(self.txt_received.value, 0)
        self.txt_received.value = str(current + amount)
        self._update_totals()

    def _clear_cart(self):
        self._baskets[self._active_basket] = []
        self._refresh_cart_ui()

    # ── Ödeme ─────────────────────────────────────────────────────────────────

    def _resolve_payment(self, payment: str, total: float) -> tuple[float, float, float]:
        if payment == "NAKIT":
            return total, 0.0, 0.0
        if payment == "POS":
            return 0.0, total, 0.0
        if payment == "HAVALE":
            return 0.0, 0.0, total
        return 0.0, 0.0, 0.0  # VERESIYE / özel

    def _quick_pay(self, payment_type: str):
        if not self.cart:
            self._snack("Sepet boş")
            return
        if payment_type == "NAKIT":
            subtotal = sum(i["line_total"] for i in self.cart)
            discount = self._to_float(self.txt_discount_amt.value, 0)
            total = max(0.0, subtotal - discount)
            received = self._to_float(self.txt_received.value, 0)
            if received + 0.001 < total:
                self._show_insufficient_cash_dialog(total, received)
                return
        if payment_type == "VERESIYE":
            if not self.dd_customer.visible:
                self.dd_customer.visible = True
                self._safe_update()
                self._snack("Müşteri seçip tekrar 'Veresiye' butonuna basın")
                return
            if not self.dd_customer.value:
                self._snack("Veresiye için müşteri seçiniz")
                return
        self._do_complete_sale(payment_type)

    def _show_insufficient_cash_dialog(self, total: float, received: float):
        missing = max(0.0, total - received)

        def _close(_e):
            dlg.open = False
            self.page.update()

        def _to_veresiye(_e):
            dlg.open = False
            self.page.update()
            if not self.dd_customer.visible:
                self.dd_customer.visible = True
                self._safe_update()
            if not self.dd_customer.value:
                self._snack("Eksik tutarı veresiye eklemek için müşteri seçiniz")
                return
            # Nakit alınan kısmı kasaya, kalan kısmı müşteri borcuna yaz
            self._do_complete_sale("VERESIYE", cash_override=received, card_override=0.0)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER, color=ft.Colors.ORANGE_700, size=22),
                ft.Text("Alınan para yetersiz", color=ft.Colors.ORANGE_700,
                        weight=ft.FontWeight.BOLD, size=14),
            ], spacing=8),
            content=ft.Container(
                width=420,
                content=ft.Column([
                    ft.Text(f"Toplam Tutar: {total:,.2f} ₺"),
                    ft.Text(f"Alınan Para: {received:,.2f} ₺"),
                    ft.Text(f"Kalan Bakiye: {missing:,.2f} ₺", color=ft.Colors.RED_700,
                            weight=ft.FontWeight.W_600),
                    ft.Text("Eksik tutarı veresiye olarak eklemek ister misiniz?"),
                ], spacing=8, tight=True),
            ),
            actions=[
                ft.TextButton("İptal", on_click=_close),
                ft.ElevatedButton(
                    "Veresiyeye Ekle",
                    icon=ft.Icons.PERSON_ADD_ALT_1,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.PURPLE_700, color=ft.Colors.WHITE),
                    on_click=_to_veresiye,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def _do_complete_sale(self, payment_type: str, cash_override: float | None = None,
                          card_override: float | None = None):
        if not self.cart:
            self._snack("Sepet boş")
            return
        discount = self._to_float(self.txt_discount_amt.value, 0)
        if discount < 0:
            discount = 0.0
        if discount > 0 and not self.current_user.get("can_discount") and self.current_user.get("role") != "ADMIN":
            self._snack("İndirim uygulama yetkiniz yok")
            return
        customer_id = None
        if payment_type == "VERESIYE" and self.dd_customer.value:
            customer_id = int(self.dd_customer.value.split(" - ")[0])
        total = max(0.0, sum(i["line_total"] for i in self.cart) - discount)
        if cash_override is not None or card_override is not None:
            cash_amount = cash_override or 0.0
            card_amount = card_override or 0.0
            transfer_amount = 0.0
        else:
            cash_amount, card_amount, transfer_amount = self._resolve_payment(payment_type, total)
        sale_cart = list(self.cart)
        # Para üstü: receipt'e geçmeden ÖNCE hesapla (sonra txt_received sıfırlanacak)
        received_amount = self._to_float(self.txt_received.value, 0)
        change_amount = max(0.0, received_amount - total) if payment_type == "NAKIT" else 0.0
        try:
            self.db.create_sale(
                sale_cart, discount=discount, payment_type=payment_type,
                cash_amount=cash_amount, card_amount=card_amount, transfer_amount=transfer_amount,
                customer_id=customer_id, is_return=False, user_id=self.current_user.get("id"),
            )
        except ValueError as ex:
            self._snack(str(ex))
            return
        self._clear_cart()
        self.dd_customer.visible = False
        self.txt_received.value = "0"
        self.txt_discount_pct.value = "0"
        self.txt_discount_amt.value = "0.00"
        self.refresh_products_grid()
        if self.on_sale_completed:
            self.on_sale_completed()
        self._show_receipt(sale_cart, total, discount, payment_type,
                           cash_amount, card_amount, received_amount, change_amount)

    def _complete_return(self, _e):
        if not self.current_user.get("can_return") and self.current_user.get("role") != "ADMIN":
            self._snack("İade yetkiniz yok")
            return
        if not self.cart:
            self._snack("İade için sepet boş")
            return
        discount = self._to_float(self.txt_discount_amt.value, 0)
        total = max(0.0, sum(i["line_total"] for i in self.cart) - discount)
        customer_id = (int(self.dd_customer.value.split(" - ")[0])
                       if self.dd_customer.visible and self.dd_customer.value else None)
        try:
            self.db.create_sale(
                list(self.cart), discount=discount, payment_type="NAKIT",
                cash_amount=total, card_amount=0, transfer_amount=0,
                customer_id=customer_id, is_return=True, user_id=self.current_user.get("id"),
            )
        except ValueError as ex:
            self._snack(str(ex))
            return
        self._clear_cart()
        self.refresh_products_grid()
        if self.on_sale_completed:
            self.on_sale_completed()
        self._snack("İade kaydedildi")

    # ── Ödeme Böl Dialog ─────────────────────────────────────────────────────

    def _show_payment_split_dialog(self):
        if not self.cart:
            self._snack("Sepet boş")
            return
        subtotal = sum(i["line_total"] for i in self.cart)
        discount = self._to_float(self.txt_discount_amt.value, 0)
        total = max(0.0, subtotal - discount)

        txt_nakit = ft.TextField(
            label="NAKİT",
            value="0",
            text_size=22,
            text_align=ft.TextAlign.RIGHT,
            bgcolor=ft.Colors.WHITE,
            width=200,
        )
        txt_kredi = ft.TextField(
            label="KREDİ KARTI",
            value=f"{total:.2f}",
            text_size=22,
            text_align=ft.TextAlign.RIGHT,
            bgcolor=ft.Colors.WHITE,
            width=200,
        )
        lbl_warn = ft.Text("", color=ft.Colors.RED_600, size=12)

        def on_nakit_change(_e):
            n = self._to_float(txt_nakit.value, 0)
            k = max(0.0, total - n)
            txt_kredi.value = f"{k:.2f}"
            if abs(n + k - total) > 0.01:
                lbl_warn.value = f"Toplam: {n+k:.2f} ≠ {total:.2f}"
            else:
                lbl_warn.value = ""
            try:
                self.page.update()
            except Exception:
                pass

        txt_nakit.on_change = on_nakit_change

        def do_split(_e):
            n = self._to_float(txt_nakit.value, 0)
            k = self._to_float(txt_kredi.value, 0)
            if abs(n + k - total) > 0.05:
                lbl_warn.value = f"Nakit+Kart={n+k:.2f} toplamı {total:.2f} TL olmalı"
                self.page.update()
                return
            self.page.dialog.open = False
            self.page.update()
            self._do_complete_sale("NAKIT+POS", cash_override=n, card_override=k)

        def cancel(_e):
            self.page.dialog.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.CALL_SPLIT, color=ft.Colors.ORANGE_600),
                ft.Text("Ödeme Böl"),
            ], spacing=8),
            content=ft.Container(
                width=280,
                content=ft.Column([
                    ft.Text(f"Toplam: {total:.2f} ₺", size=16,
                            weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_700),
                    ft.Divider(),
                    txt_nakit,
                    txt_kredi,
                    lbl_warn,
                ], spacing=12, tight=True),
            ),
            actions=[
                ft.TextButton("Vazgeç", on_click=cancel),
                ft.ElevatedButton(
                    "Tamam",
                    icon=ft.Icons.CHECK,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE),
                    on_click=do_split,
                ),
            ],
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    # ── Fiş Dialog ────────────────────────────────────────────────────────────

    def _show_receipt(self, cart, total, discount, payment,
                      cash, card, received: float = 0.0, change: float = 0.0):
        try:
            now = datetime.now().strftime("%d.%m.%Y %H:%M")
            try:
                with self.db.conn() as conn:
                    settings = {r[0]: r[1] for r in conn.execute(
                        "SELECT key, value FROM settings").fetchall()}
            except Exception:
                settings = {}
            company = settings.get("company_name", "Temel Market")

            lines = [
                ft.Text(company, size=15, weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER),
                ft.Text("MALİ DEĞERİ OLMAYAN BİLGİ FİŞİ", size=9,
                        color=ft.Colors.BLUE_GREY_500, text_align=ft.TextAlign.CENTER),
                ft.Text(now, size=10, color=ft.Colors.BLUE_GREY_600,
                        text_align=ft.TextAlign.CENTER),
                ft.Divider(),
            ]
            for item in cart:
                lines.append(ft.Row([
                    ft.Text(item["name"], size=11, expand=True, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(f"{item['qty']:.0f}x{item['price']:.2f}", size=11,
                            color=ft.Colors.BLUE_GREY_600, width=80, text_align=ft.TextAlign.RIGHT),
                    ft.Text(f"{item['line_total']:.2f} ₺", size=11,
                            weight=ft.FontWeight.W_600, width=70, text_align=ft.TextAlign.RIGHT),
                ]))
            lines += [
                ft.Divider(),
                ft.Row([ft.Text("Toplam:", weight=ft.FontWeight.BOLD),
                        ft.Text(f"{total:.2f} ₺", weight=ft.FontWeight.BOLD,
                                color=ft.Colors.INDIGO_700, size=14)],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ]
            if discount > 0:
                lines.append(ft.Row([
                    ft.Text("İndirim:", color=ft.Colors.ORANGE_700),
                    ft.Text(f"-{discount:.2f} ₺", color=ft.Colors.ORANGE_700)],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
            if received > 0:
                lines.append(ft.Row([
                    ft.Text("Alınan:", color=ft.Colors.BLUE_GREY_600),
                    ft.Text(f"{received:.2f} ₺", color=ft.Colors.BLUE_GREY_600)],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
            if change > 0:
                lines.append(ft.Row([
                    ft.Text("Para Üstü:", color=ft.Colors.GREEN_700,
                            weight=ft.FontWeight.W_600),
                    ft.Text(f"{change:.2f} ₺", color=ft.Colors.GREEN_700,
                            weight=ft.FontWeight.BOLD, size=14)],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
            lines += [
                ft.Divider(),
                ft.Text("Teşekkürler, iyi günler!", size=11, italic=True,
                        text_align=ft.TextAlign.CENTER, color=ft.Colors.BLUE_GREY_500),
            ]

            def close(_e=None):
                self.page.dialog.open = False
                self.page.update()

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Row([ft.Icon(ft.Icons.RECEIPT, color=ft.Colors.INDIGO_600),
                               ft.Text("Satış Fişi")], spacing=6),
                content=ft.Container(
                    width=340,
                    content=ft.Column(lines, spacing=4, scroll=ft.ScrollMode.AUTO),
                ),
                actions=[
                    ft.TextButton("Kapat", on_click=close),
                    ft.ElevatedButton("Yazdır", icon=ft.Icons.PRINT,
                                       on_click=lambda _: self._snack("Yazıcı entegrasyonu yakında...")),
                ],
            )
            self.page.dialog = dlg
            dlg.open = True
            self.page.update()
        except Exception:
            self._snack(f"Satış kaydedildi  |  Toplam: {total:.2f} ₺")

    # ── Responsive ────────────────────────────────────────────────────────────

    def set_responsive(self, width: float):
        if width < 900:
            self.products_grid.max_extent = 120
            self.products_grid.child_aspect_ratio = 0.85
        elif width < 1200:
            self.products_grid.max_extent = 145
            self.products_grid.child_aspect_ratio = 0.88
        else:
            self.products_grid.max_extent = 160
            self.products_grid.child_aspect_ratio = 0.90
        self._safe_update()
