import os
import sys
import flet as ft

from flet_pos.db import DB
from flet_pos.pages.backup_page import BackupPage
from flet_pos.pages.barcode_page import BarcodePage
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
from flet_pos.services.backup import BackupManager


class FletMarketApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db = DB(os.path.join(self.base_dir, "market.db"))
        self.media_dir = os.path.join(self.base_dir, "product_images")
        os.makedirs(self.media_dir, exist_ok=True)
        saved_backup_dir = self.db.get_setting("local_backup_dir", "") or ""
        backup_dir = saved_backup_dir if saved_backup_dir and os.path.isdir(saved_backup_dir) else os.path.join(self.base_dir, "backups")
        self.backup_manager = BackupManager(
            base_dir=self.base_dir,
            db_path=os.path.join(self.base_dir, "market.db"),
            backup_dir=backup_dir,
            interval_seconds=int(self.db.get_setting("backup_interval_minutes", "120") or "120") * 60,
            google_drive_dir=self.db.get_setting("google_drive_backup_dir", ""),
            target_mode=self.db.get_setting("backup_target_mode", "BOTH"),
        )
        self.backup_manager.start()

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
        self._set_window_icon()

        self.current_user = None
        self.pages = {}
        self._dirty_pages = set()
        self._active_nav_key = ""
        self.content_host = ft.Container(expand=True)
        self.page.on_resize = self._on_page_resized
        self.page.on_keyboard_event = self._on_keyboard
        self.page.window.on_close = self._on_window_close

        # Tüm sayfa içeriği bu tek root container içinde swap edilir
        self._root = ft.Container(expand=True)
        self.page.controls.append(self._root)
        self.page.update()

        self._show_login()

    def _set_window_icon(self):
        """Uygulama penceresi/gorev cubugu simgesini ayarla."""
        candidates = []
        if getattr(sys, "frozen", False):
            base = getattr(sys, "_MEIPASS", "")
            if base:
                candidates.extend(
                    [
                        os.path.join(base, "assets", "temelmarket.ico"),
                        os.path.join(base, "assets", "temelmarket_icon.png"),
                    ]
                )
        candidates.extend(
            [
                os.path.join(self.base_dir, "assets", "temelmarket.ico"),
                os.path.join(self.base_dir, "assets", "temelmarket_icon.png"),
            ]
        )
        # Windows desktop için .ico daha güvenilir
        ico_first = [p for p in candidates if p.lower().endswith(".ico")]
        other = [p for p in candidates if not p.lower().endswith(".ico")]
        icon_path = next((p for p in ico_first + other if p and os.path.exists(p)), "")
        if not icon_path:
            return
        try:
            self.page.window.icon = os.path.abspath(icon_path)
        except Exception:
            pass

    def _build_pages(self):
        self._page_factories = {
            "pos": lambda: POSPage(
                self.db,
                on_sale_completed=self._after_data_change,
                current_user=self.current_user,
                on_unknown_barcode=self._open_product_add_from_pos,
            ),
            "products": lambda: ProductsPage(self.db, self.media_dir, on_products_changed=self._products_changed),
            "barcode_center": lambda: BarcodePage(self.db, self.base_dir),
            "stock": lambda: StockPage(self.db, on_stock_changed=self._products_changed),
            "customers": lambda: CustomersPage(self.db),
            "suppliers": lambda: SuppliersPage(self.db),
            "reports": lambda: ReportsPage(self.db),
            "sales_history": lambda: SalesHistoryPage(self.db),
            "cash": lambda: CashPage(self.db),
            "users": lambda: UsersPage(self.db),
            "backup": lambda: BackupPage(self.base_dir, backup_manager=self.backup_manager, db=self.db),
            "hardware": lambda: HardwarePage(),
        }
        # Create only POS page immediately; others are lazy-loaded on navigation
        self.pages["pos"] = self._page_factories["pos"]()

    def _ensure_page(self, key: str):
        if key in self.pages:
            return self.pages[key]
        factory = self._page_factories.get(key)
        if not factory:
            return None
        page = factory()
        self.pages[key] = page
        return page

    def _build_layout(self):
        destinations = [
            ("Hizli Satis", "pos", ft.Icons.POINT_OF_SALE),
            ("Urunler", "products", ft.Icons.INVENTORY_2),
            ("Barkod / Etiket", "barcode_center", ft.Icons.QR_CODE_2),
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
                            ft.Icons.KEY,
                            icon_color=ft.Colors.WHITE,
                            tooltip="Sifremi Degistir",
                            on_click=lambda _: self._open_change_password_dialog(),
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
        self._ensure_page(key)
        self.show(key)
        if key in self._dirty_pages:
            self._dirty_pages.discard(key)
            self._schedule_refresh_page_data(key)
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
            "barcode_center": "can_products",
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
        pos.invalidate_product_cache()
        if self._active_nav_key == "pos":
            pos.refresh_products_grid()
        self._mark_or_refresh("barcode_center")
        if "stock" in self.pages:
            self._mark_or_refresh("stock")

    def _after_data_change(self):
        self._mark_or_refresh("reports")
        self._mark_or_refresh("stock")
        self._mark_or_refresh("customers")
        if "pos" in self.pages:
            self.pages["pos"].refresh_customers()
            self.pages["pos"].invalidate_product_cache()
            if self._active_nav_key == "pos":
                self.pages["pos"].refresh_products_grid()

    def _mark_or_refresh(self, key: str):
        if key not in self.pages:
            self._dirty_pages.add(key)
            return
        if self._active_nav_key == key:
            self._schedule_refresh_page_data(key)
        else:
            self._dirty_pages.add(key)

    def _schedule_refresh_page_data(self, key: str, delay: float = 0.05):
        try:
            if not hasattr(self, "_refresh_timers"):
                self._refresh_timers = {}
            t = self._refresh_timers.get(key)
            if t:
                t.cancel()
        except Exception:
            pass
        import threading
        timer = threading.Timer(delay, lambda: self._refresh_page_data(key))
        timer.daemon = True
        self._refresh_timers[key] = timer
        timer.start()

    def _refresh_page_data(self, key: str):
        page = self._ensure_page(key)
        if not page:
            return
        if key == "pos":
            page.refresh_customers()
            page.invalidate_product_cache()
            if hasattr(page, "schedule_refresh_products_grid"):
                page.schedule_refresh_products_grid(force_reload=True)
            else:
                page.refresh_products_grid()
            return
        if key == "products":
            # ProductsPage has no single refresh() — call its data-loading methods
            if hasattr(page, "schedule_refresh_table"):
                page.schedule_refresh_table(force_reload=True)
            elif hasattr(page, "refresh_table"):
                page.refresh_table(force_reload=True)
            if hasattr(page, "_load_suppliers"):
                page._load_suppliers()
            if hasattr(page, "_refresh_taxonomy_lists"):
                page._refresh_taxonomy_lists()
            if hasattr(page, "_load_category_dropdowns"):
                page._load_category_dropdowns()
            return
        if hasattr(page, "refresh"):
            page.refresh()
        elif hasattr(page, "refresh_table"):
            page.refresh_table(force_reload=True)


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

        active_key = getattr(self, "_active_nav_key", "")
        if active_key:
            active_page = self.pages.get(active_key)
            if active_page:
                if hasattr(active_page, "handle_keyboard_shortcut"):
                    try:
                        if active_page.handle_keyboard_shortcut(e):
                            return
                    except Exception:
                        pass
                if hasattr(active_page, "handle_keyboard_event"):
                    try:
                        if active_page.handle_keyboard_event(e):
                            return
                    except Exception:
                        pass

    def show(self, key: str):
        page = self._ensure_page(key)
        if not page:
            return
        self.content_host.content = page
        self.page.update()
        # Trigger initial data load on first visit (did_mount is not called on
        # ft.Container subclasses in Flet 0.84 – we simulate it here)
        if key not in self._shown_pages:
            self._shown_pages.add(key)
            self._schedule_refresh_page_data(key)
            self.page.update()  # Force full repaint after data is loaded

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

    def _on_window_close(self, _e=None):
        """Uygulama kapatılırken otomatik yedek al ve thread kapat."""
        try:
            if getattr(self, "backup_manager", None):
                self.backup_manager.stop()
                if self.backup_manager._thread and self.backup_manager._thread.is_alive():
                    self.backup_manager._thread.join(timeout=2.0)
                self.backup_manager.backup_now(prefix="exit")
        except Exception as ex:
            import traceback
            traceback.print_exc()
        finally:
            try:
                self.page.window.destroy()
            except Exception:
                pass

    def _open_change_password_dialog(self):
        if not self.current_user:
            return
        txt_current = ft.TextField(
            label="Mevcut Şifre",
            password=True,
            can_reveal_password=True,
            width=300,
            autofocus=True,
        )
        txt_new = ft.TextField(
            label="Yeni Şifre",
            password=True,
            can_reveal_password=True,
            width=300,
        )
        txt_confirm = ft.TextField(
            label="Yeni Şifre (Tekrar)",
            password=True,
            can_reveal_password=True,
            width=300,
        )
        lbl_error = ft.Text("", color=ft.Colors.RED_600, size=12)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Şifremi Değiştir"),
            content=ft.Container(
                width=340,
                content=ft.Column(
                    [txt_current, txt_new, txt_confirm, lbl_error],
                    spacing=10,
                    tight=True,
                ),
            ),
        )

        def do_change(_e):
            current = (txt_current.value or "").strip()
            new_pw = (txt_new.value or "").strip()
            confirm = (txt_confirm.value or "").strip()
            if not current or not new_pw:
                lbl_error.value = "Tüm alanları doldurunuz"
                self.page.update()
                return
            if new_pw != confirm:
                lbl_error.value = "Yeni şifreler eşleşmiyor"
                self.page.update()
                return
            try:
                self.db.change_user_password(
                    self.current_user["id"], current, new_pw
                )
                dlg.open = False
                self.page.update()
                self.page.snack_bar = ft.SnackBar(
                    ft.Text("Şifre başarıyla güncellendi"), open=True
                )
                self.page.update()
            except ValueError as ex:
                lbl_error.value = str(ex)
                self.page.update()

        def cancel(_e):
            dlg.open = False
            self.page.update()

        dlg.actions = [
            ft.TextButton("İptal", on_click=cancel),
            ft.ElevatedButton(
                "Değiştir",
                icon=ft.Icons.LOCK_RESET,
                on_click=do_change,
            ),
        ]

        if dlg not in self.page.overlay:
            self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _start_main_shell(self):
        # Overlay bozulmasın — page controls hiç temizlenmez,
        # sadece _root.content swap edilir
        self.pages = {}
        self._dirty_pages = set()
        self._shown_pages = set()          # tracks which pages got their initial data load
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
