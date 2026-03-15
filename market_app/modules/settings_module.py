import tkinter as tk
from tkinter import ttk, messagebox


class SettingsModule(ttk.Frame):
    def __init__(self, parent, db, on_saved):
        super().__init__(parent)
        self.db = db
        self.on_saved = on_saved

        self.var_company_name = tk.StringVar()
        self.var_company_phone = tk.StringVar()
        self.var_kdv = tk.StringVar()
        self.var_backup_interval = tk.StringVar()
        self.var_quick_count = tk.StringVar()
        self.var_default_price = tk.StringVar()

        self._build()
        self.load_settings()

    def _build(self):
        card = ttk.LabelFrame(self, text="Genel Ayarlar")
        card.pack(fill="x", padx=10, pady=10)

        rows = [
            ("Firma Adi", self.var_company_name),
            ("Firma Telefon", self.var_company_phone),
            ("Varsayilan KDV (%)", self.var_kdv),
            ("Yedekleme Araligi (sn)", self.var_backup_interval),
            ("Hizli Urun Buton Sayisi", self.var_quick_count),
        ]
        for idx, (label, var) in enumerate(rows):
            ttk.Label(card, text=label).grid(row=idx, column=0, sticky="w", padx=6, pady=5)
            ttk.Entry(card, textvariable=var, width=28).grid(row=idx, column=1, padx=6, pady=5, sticky="w")

        ttk.Label(card, text="Varsayilan Fiyat Tipi").grid(row=5, column=0, sticky="w", padx=6, pady=5)
        ttk.Combobox(
            card,
            textvariable=self.var_default_price,
            values=["sell_price", "sell_price_2", "sell_price_3", "card_price"],
            state="readonly",
            width=25,
        ).grid(row=5, column=1, padx=6, pady=5, sticky="w")

        ttk.Button(card, text="Ayarlari Kaydet", style="Accent.TButton", command=self.save_settings).grid(
            row=6, column=0, columnspan=2, padx=6, pady=10, sticky="ew"
        )

        note = ttk.LabelFrame(self, text="Bilgi")
        note.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Label(
            note,
            text=(
                "Bu ayarlar kaydedildikten sonra tum modullere uygulanir.\n"
                "Yedekleme araligi yeni deger ile otomatik guncellenir."
            ),
        ).pack(anchor="w", padx=8, pady=8)

    def load_settings(self):
        self.var_company_name.set(self.db.get_setting("company_name", "Temel Market"))
        self.var_company_phone.set(self.db.get_setting("company_phone", ""))
        self.var_kdv.set(self.db.get_setting("default_kdv", "20"))
        self.var_backup_interval.set(self.db.get_setting("backup_interval_seconds", "300"))
        self.var_quick_count.set(self.db.get_setting("quick_button_count", "24"))
        self.var_default_price.set(self.db.get_setting("default_price_type", "sell_price"))

    def save_settings(self):
        try:
            kdv = float(self.var_kdv.get().replace(",", "."))
            interval = int(float(self.var_backup_interval.get().replace(",", ".")))
            quick_count = int(float(self.var_quick_count.get().replace(",", ".")))
        except ValueError:
            messagebox.showerror("Hatali Giris", "KDV/Aralik/Buton sayisi sayisal olmali.")
            return

        if interval < 30:
            messagebox.showerror("Hatali Aralik", "Yedekleme araligi en az 30 saniye olmali.")
            return
        if quick_count < 4 or quick_count > 80:
            messagebox.showerror("Hatali Buton Sayisi", "Hizli buton sayisi 4 ile 80 arasinda olmali.")
            return

        self.db.set_setting("company_name", self.var_company_name.get().strip())
        self.db.set_setting("company_phone", self.var_company_phone.get().strip())
        self.db.set_setting("default_kdv", str(kdv))
        self.db.set_setting("backup_interval_seconds", str(interval))
        self.db.set_setting("quick_button_count", str(quick_count))
        self.db.set_setting("default_price_type", self.var_default_price.get().strip() or "sell_price")

        self.on_saved()
        messagebox.showinfo("Basarili", "Ayarlar kaydedildi.")
