import os
import tkinter as tk
from tkinter import ttk

from market_app.database import Database
from market_app.modules.customers_module import CustomersModule
from market_app.modules.products_module import ProductsModule
from market_app.modules.reports_module import ReportsModule
from market_app.modules.sales_module import SalesModule
from market_app.modules.settings_module import SettingsModule
from market_app.services.backup_service import BackupService
from market_app.theme import apply_theme


class MarketApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Temel Market POS - Moduler Surum")
        self.geometry("1320x820")
        self.minsize(1160, 700)

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(base_dir, "market.db")
        backup_dir = os.path.join(base_dir, "backups")
        self.media_dir = os.path.join(base_dir, "product_images")
        os.makedirs(self.media_dir, exist_ok=True)

        self.db = Database(db_path)
        interval = int(self.db.get_setting("backup_interval_seconds", "300") or "300")
        self.backup_service = BackupService(db_path, backup_dir, interval_seconds=interval)
        self.backup_service.start()

        apply_theme(self)
        self._build_layout()

    def _build_layout(self):
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root, style="Header.TFrame")
        header.pack(fill="x")
        company_name = self.db.get_setting("company_name", "Temel Market POS")
        ttk.Label(header, text=company_name, style="Header.TLabel").pack(side="left", padx=12, pady=10)
        self.status_var = tk.StringVar(value="Hazir")
        ttk.Label(header, textvariable=self.status_var, style="Header.TLabel").pack(side="right", padx=12, pady=10)

        body = ttk.Frame(root)
        body.pack(fill="both", expand=True)

        sidebar = ttk.Frame(body, style="Sidebar.TFrame", width=210)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        content = ttk.Frame(body)
        content.pack(side="left", fill="both", expand=True)

        self.pages = {}
        self.pages["sales"] = SalesModule(content, self.db, on_after_sale=self.refresh_all)
        self.pages["products"] = ProductsModule(
            content,
            self.db,
            on_after_change=self.refresh_all,
            media_dir=self.media_dir,
        )
        self.pages["customers"] = CustomersModule(content, self.db, on_after_change=self.refresh_all)
        self.pages["reports"] = ReportsModule(content, self.db)
        self.pages["settings"] = SettingsModule(content, self.db, on_saved=self.on_settings_saved)

        for page in self.pages.values():
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

        buttons = [
            ("Hizli Satis", "sales"),
            ("Urun / Stok", "products"),
            ("Musteri / Veresiye", "customers"),
            ("Raporlar", "reports"),
            ("Ayarlar", "settings"),
        ]
        for text, key in buttons:
            ttk.Button(sidebar, text=text, style="Sidebar.TButton", command=lambda k=key: self.show_page(k)).pack(
                fill="x", padx=10, pady=6
            )

        ttk.Button(sidebar, text="Yedek Al", style="Sidebar.TButton", command=self.manual_backup).pack(
            fill="x", padx=10, pady=(30, 6)
        )

        self.show_page("sales")
        self.refresh_all()

    def show_page(self, key: str):
        self.pages[key].tkraise()
        titles = {
            "sales": "Hizli satis modu aktif",
            "products": "Urun ve stok yonetimi",
            "customers": "Musteri ve tahsilat takibi",
            "reports": "Satis ve stok raporlari",
            "settings": "Program ayarlari",
        }
        self.status_var.set(titles.get(key, "Hazir"))

    def manual_backup(self):
        self.backup_service.backup_now()
        self.status_var.set("Manuel yedek alindi")

    def refresh_all(self):
        self.pages["products"].refresh()
        self.pages["customers"].refresh()
        self.pages["sales"].refresh_customers()
        self.pages["sales"].refresh_quick_buttons()
        self.pages["reports"].refresh()

    def on_settings_saved(self):
        interval = int(self.db.get_setting("backup_interval_seconds", "300") or "300")
        self.backup_service.set_interval(interval)
        self.title(f"{self.db.get_setting('company_name', 'Temel Market POS')} - Moduler Surum")
        self.refresh_all()


def run():
    app = MarketApp()
    app.mainloop()
