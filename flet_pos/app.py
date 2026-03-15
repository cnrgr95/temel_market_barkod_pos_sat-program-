import os
import flet as ft

from flet_pos.db import DB
from flet_pos.pages.backup_page import BackupPage
from flet_pos.pages.cash_page import CashPage
from flet_pos.pages.customers_page import CustomersPage
from flet_pos.pages.hardware_page import HardwarePage
from flet_pos.pages.pos_page import POSPage
from flet_pos.pages.products_page import ProductsPage
from flet_pos.pages.reports_page import ReportsPage
from flet_pos.pages.sales_history_page import SalesHistoryPage
from flet_pos.pages.stock_page import StockPage
from flet_pos.pages.suppliers_page import SuppliersPage
from flet_pos.pages.users_page import UsersPage


class FletMarketApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db = DB(os.path.join(self.base_dir, "market.db"))
        self.media_dir = os.path.join(self.base_dir, "product_images")
        os.makedirs(self.media_dir, exist_ok=True)

        self.page.title = "Temel Market POS - Flet"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.theme = ft.Theme(
            color_scheme_seed=ft.Colors.INDIGO,
            visual_density=ft.VisualDensity.COMPACT,
            use_material3=True,
        )
        self.page.padding = 0
        self.page.bgcolor = ft.Colors.GREY_100
        self.page.window_min_width = 960
        self.page.window_min_height = 640

        self.current_user = None
        self.pages = {}
        self._active_nav_key = ""
        self.content_host = ft.Container(expand=True)
        self.page.on_resize = self._on_page_resized
        self.page.on_keyboard_event = self._on_keyboard

        # Tüm sayfa içeriği bu tek root container içinde swap edilir
        self._root = ft.Container(expand=True)
        self.page.controls.append(self._root)
        self.page.update()

        self._show_login()

    def _build_pages(self):
        self.pages["pos"] = POSPage(
            self.db,
            on_sale_completed=self._after_data_change,
            current_user=self.current_user,
            on_unknown_barcode=self._open_product_add_from_pos,
        )
        products_page = ProductsPage(self.db, self.media_dir, on_products_changed=self._products_changed)
        self.pages["products"] = products_page
        self.pages["stock"] = StockPage(self.db)
        self.pages["customers"] = CustomersPage(self.db)
        self.pages["suppliers"] = SuppliersPage(self.db)
        self.pages["reports"] = ReportsPage(self.db)
        self.pages["sales_history"] = SalesHistoryPage(self.db)
        self.pages["cash"] = CashPage(self.db)
        self.pages["users"] = UsersPage(self.db)
        self.pages["backup"] = BackupPage(self.base_dir)
        self.pages["hardware"] = HardwarePage()

    def _build_layout(self):
        destinations = [
            ("Hizli Satis", "pos", ft.Icons.POINT_OF_SALE),
            ("Urunler", "products", ft.Icons.INVENTORY_2),
            ("Stok", "stock", ft.Icons.WAREHOUSE),
            ("Cari Hesap", "customers", ft.Icons.PEOPLE_ALT),
            ("Tedarikciler", "suppliers", ft.Icons.LOCAL_SHIPPING),
            ("Kasa", "cash", ft.Icons.ACCOUNT_BALANCE_WALLET),
            ("Kullanicilar", "users", ft.Icons.ADMIN_PANEL_SETTINGS),
            ("Yedekleme", "backup", ft.Icons.BACKUP),
            ("Donanim", "hardware", ft.Icons.DEVICES_OTHER),
        ]
        if self.current_user and self.current_user.get("can_reports"):
            destinations.insert(5, ("Raporlar", "reports", ft.Icons.QUERY_STATS))
        if self.current_user and self.current_user.get("can_sales_history"):
            destinations.insert(6, ("Satis Hareketleri", "sales_history", ft.Icons.RECEIPT_LONG))
        destinations = [d for d in destinations if self._has_access(d[1])]
        self.key_order = [d[1] for d in destinations]
        self._active_nav_key = "pos"

        # ── Üst menü toolbar butonları ─────────────────────────────────────
        def _nav_btn(label, key, icon):
            return ft.TextButton(
                content=ft.Column(
                    [ft.Icon(icon, size=20), ft.Text(label, size=10)],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=2,
                    tight=True,
                ),
                style=ft.ButtonStyle(
                    padding=ft.padding.symmetric(horizontal=8, vertical=6),
                    shape=ft.RoundedRectangleBorder(radius=6),
                ),
                on_click=lambda _, k=key: self._nav_to(k),
                data=key,
            )

        self._nav_buttons = {d[1]: _nav_btn(d[0], d[1], d[2]) for d in destinations}

        menu_bar = ft.Container(
            bgcolor=ft.Colors.INDIGO_800,
            padding=ft.padding.symmetric(horizontal=8, vertical=0),
            content=ft.Row(
                controls=[
                    # Sol: Logo + butonlar
                    ft.Row(
                        [
                            ft.Row([
                                ft.Icon(ft.Icons.STORE_MALL_DIRECTORY, color=ft.Colors.WHITE, size=22),
                                ft.Text("Temel Market", size=14, weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.WHITE),
                            ], spacing=6),
                            ft.VerticalDivider(width=1, color=ft.Colors.with_opacity(0.3, ft.Colors.WHITE)),
                            *[self._update_nav_btn_style(b, b.data == "pos")
                              for b in self._nav_buttons.values()],
                        ],
                        spacing=2,
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                    ),
                    # Sağ: Kullanıcı + çıkış
                    ft.Row([
                        ft.Container(
                            bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
                            border_radius=16,
                            padding=ft.padding.symmetric(horizontal=10, vertical=4),
                            content=ft.Row([
                                ft.Icon(ft.Icons.PERSON, color=ft.Colors.WHITE, size=16),
                                ft.Text(self.current_user.get("username", "-"),
                                        color=ft.Colors.WHITE, size=12),
                            ], spacing=4),
                        ),
                        ft.IconButton(
                            ft.Icons.LOGOUT, icon_color=ft.Colors.WHITE,
                            tooltip="Cikis Yap",
                            on_click=lambda _: self._show_login(),
                        ),
                    ], spacing=4),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        )

        self.page.bgcolor = ft.Colors.GREY_50
        main_col = ft.Column(
            expand=True, spacing=0,
            controls=[menu_bar, self.content_host],
        )
        # Overlay bozulmasın: page.add yerine root container swap
        self._root.content = main_col
        self.page.update()

    def _update_nav_btn_style(self, btn: ft.TextButton, active: bool) -> ft.TextButton:
        if active:
            btn.style = ft.ButtonStyle(
                bgcolor=ft.Colors.with_opacity(0.25, ft.Colors.WHITE),
                color=ft.Colors.WHITE,
                padding=ft.padding.symmetric(horizontal=8, vertical=6),
                shape=ft.RoundedRectangleBorder(radius=6),
            )
        else:
            btn.style = ft.ButtonStyle(
                bgcolor=ft.Colors.TRANSPARENT,
                color=ft.Colors.with_opacity(0.8, ft.Colors.WHITE),
                padding=ft.padding.symmetric(horizontal=8, vertical=6),
                shape=ft.RoundedRectangleBorder(radius=6),
            )
        return btn

    def _nav_to(self, key: str):
        if not self._has_access(key):
            self.page.snack_bar = ft.SnackBar(ft.Text("Bu bolume erisim yetkiniz yok"), open=True)
            self.page.update()
            return
        self._active_nav_key = key
        for k, btn in self._nav_buttons.items():
            self._update_nav_btn_style(btn, k == key)
        self.show(key)
        self.page.update()

    def _has_access(self, key: str) -> bool:
        user = self.current_user or {}
        if not user:
            return False
        if user.get("role") == "ADMIN":
            return True
        if key == "pos":
            return True
        mapping = {
            "products": "can_products",
            "stock": "can_stock",
            "customers": "can_customers",
            "suppliers": "can_suppliers",
            "cash": "can_cash",
            "users": "can_users",
            "backup": "can_backup",
            "hardware": "can_hardware",
            "reports": "can_reports",
            "sales_history": "can_sales_history",
        }
        perm = mapping.get(key)
        return bool(user.get(perm)) if perm else True

    def _on_nav_change(self, e: ft.ControlEvent):
        idx = int(e.data)
        self._nav_to(self.key_order[idx])

    def _products_changed(self):
        pos = self.pages["pos"]
        pos.refresh_products_grid()
        if "stock" in self.pages:
            self.pages["stock"].refresh()

    def _after_data_change(self):
        if "reports" in self.pages:
            self.pages["reports"].refresh()
        if "stock" in self.pages:
            self.pages["stock"].refresh()
        if "customers" in self.pages:
            self.pages["customers"].refresh()
        if "pos" in self.pages:
            self.pages["pos"].refresh_customers()
            self.pages["pos"].refresh_products_grid()

    def _open_product_add_from_pos(self, barcode: str):
        if not self._has_access("products"):
            self.page.snack_bar = ft.SnackBar(ft.Text("Urun ekleme yetkiniz yok"), open=True)
            self.page.update()
            return
        self._nav_to("products")
        page = self.pages.get("products")
        if page and hasattr(page, "start_add_with_barcode"):
            page.start_add_with_barcode(barcode)

    def _apply_responsive_nav(self):
        width = self.page.width or 1280
        if "pos" in self.pages:
            self.pages["pos"].set_responsive(width)
        self.page.update()

    def _on_page_resized(self, _e):
        self._apply_responsive_nav()

    def _on_keyboard(self, e: ft.KeyboardEvent):
        # F11 → tam ekran aç/kapat
        if e.key == "F11":
            try:
                # Flet 0.82: page.window nesnesi üzerinden
                self.page.window.full_screen = not self.page.window.full_screen
            except AttributeError:
                try:
                    # Eski API fallback
                    self.page.window_full_screen = not self.page.window_full_screen
                except AttributeError:
                    pass
            self.page.update()
            return

        # POS kısayolları (yalnızca aktif sayfa POS iken)
        if getattr(self, "_active_nav_key", "") == "pos":
            pos_page = self.pages.get("pos")
            if pos_page and hasattr(pos_page, "handle_keyboard_shortcut"):
                try:
                    if pos_page.handle_keyboard_shortcut(e):
                        return
                except Exception:
                    pass

    def show(self, key: str):
        self.content_host.content = self.pages[key]
        self.page.update()

    def _show_login(self):
        username = ft.TextField(
            label="Kullanici Adi",
            prefix_icon=ft.Icons.PERSON,
            width=320,
            autofocus=True,
        )
        password = ft.TextField(
            label="Sifre",
            prefix_icon=ft.Icons.LOCK,
            password=True,
            can_reveal_password=True,
            width=320,
        )
        msg = ft.Text("", color=ft.Colors.RED_600, size=13)

        def do_login(_e):
            user = self.db.authenticate_user((username.value or "").strip(), (password.value or "").strip())
            if not user:
                msg.value = "Kullanici adi veya sifre hatali!"
                self.page.update()
                return
            self.current_user = user
            self._start_main_shell()

        password.on_submit = do_login

        card = ft.Container(
            width=440,
            bgcolor=ft.Colors.WHITE,
            border_radius=20,
            padding=ft.padding.symmetric(horizontal=36, vertical=40),
            shadow=ft.BoxShadow(blur_radius=30, color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK), spread_radius=2),
            content=ft.Column(
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
                controls=[
                    ft.Container(
                        bgcolor=ft.Colors.INDIGO_50,
                        border_radius=50,
                        padding=18,
                        content=ft.Icon(ft.Icons.STORE_MALL_DIRECTORY, size=44, color=ft.Colors.INDIGO_700),
                    ),
                    ft.Text("Temel Market POS", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900),
                    ft.Text("Devam etmek icin giris yapin", size=13, color=ft.Colors.BLUE_GREY_500),
                    ft.Divider(height=4, color=ft.Colors.TRANSPARENT),
                    username,
                    password,
                    msg,
                    ft.ElevatedButton(
                        "Giris Yap",
                        icon=ft.Icons.LOGIN,
                        width=320,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                        on_click=do_login,
                    ),
                    ft.Text("Kullanici adi ve sifrenizi giriniz", color=ft.Colors.BLUE_GREY_400, size=12),
                ],
            ),
        )
        self.page.bgcolor = ft.Colors.GREY_100
        self._root.content = ft.Container(
            expand=True, alignment=ft.Alignment(0, 0), content=card,
        )
        self.page.update()

    def _start_main_shell(self):
        # Overlay bozulmasın — page controls hiç temizlenmez,
        # sadece _root.content swap edilir
        self.pages = {}
        self.content_host = ft.Container(
            expand=True,
            padding=ft.padding.only(left=10, right=10, bottom=10, top=6),
        )
        self._build_pages()
        self._build_layout()  # → self._root.content = main_col
        self._apply_responsive_nav()
        self._nav_to("pos")


def main(page: ft.Page):
    FletMarketApp(page)
