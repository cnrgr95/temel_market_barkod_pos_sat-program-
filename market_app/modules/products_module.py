import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from market_app.services.barcode_service import generate_ean13

try:
    from PIL import Image, ImageTk  # type: ignore

    HAS_PILLOW = True
except Exception:
    HAS_PILLOW = False


class ProductsModule(ttk.Frame):
    def __init__(self, parent, db, on_after_change, media_dir: str):
        super().__init__(parent)
        self.db = db
        self.on_after_change = on_after_change
        self.media_dir = media_dir
        os.makedirs(self.media_dir, exist_ok=True)
        self.preview_photo = None

        self.var_barcode = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_cost = tk.StringVar(value="0")
        self.var_sell = tk.StringVar(value="0")
        self.var_sell2 = tk.StringVar(value="0")
        self.var_sell3 = tk.StringVar(value="0")
        self.var_card = tk.StringVar(value="0")
        self.var_stock = tk.StringVar(value="0")
        self.var_critical = tk.StringVar(value="0")
        self.var_unit = tk.StringVar(value="Adet")
        self.var_category = tk.StringVar()
        self.var_supplier = tk.StringVar()
        self.var_special = tk.StringVar()
        self.var_expiry = tk.StringVar()
        self.var_image_path = tk.StringVar()

        self._build()
        self.refresh()

    def _build(self) -> None:
        form = ttk.LabelFrame(self, text="Urun Karti")
        form.pack(fill="x", padx=10, pady=10)

        left = ttk.Frame(form)
        left.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        right = ttk.Frame(form)
        right.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        form.columnconfigure(0, weight=3)
        form.columnconfigure(1, weight=2)

        fields_left = [
            ("Barkod", self.var_barcode),
            ("Urun Adi", self.var_name),
            ("Alis", self.var_cost),
            ("Satis-1", self.var_sell),
            ("Satis-2", self.var_sell2),
            ("Satis-3", self.var_sell3),
            ("Kart Fiyati", self.var_card),
            ("Stok", self.var_stock),
            ("Kritik", self.var_critical),
        ]
        for idx, (label, var) in enumerate(fields_left):
            ttk.Label(left, text=label).grid(row=idx, column=0, sticky="w", padx=4, pady=3)
            ttk.Entry(left, textvariable=var, width=22).grid(row=idx, column=1, sticky="w", padx=4, pady=3)

        ttk.Button(left, text="Barkod Uret", command=self.generate_barcode).grid(row=0, column=2, padx=4, pady=3)

        fields_right = [
            ("Olcu Birimi", self.var_unit),
            ("Kategori", self.var_category),
            ("Tedarikci", self.var_supplier),
            ("Ozel Kod", self.var_special),
            ("SKT (YYYY-AA-GG)", self.var_expiry),
        ]
        for idx, (label, var) in enumerate(fields_right):
            ttk.Label(right, text=label).grid(row=idx, column=0, sticky="w", padx=4, pady=3)
            ttk.Entry(right, textvariable=var, width=22).grid(row=idx, column=1, sticky="w", padx=4, pady=3)

        ttk.Label(right, text="Resim").grid(row=5, column=0, sticky="w", padx=4, pady=3)
        ttk.Entry(right, textvariable=self.var_image_path, width=22, state="readonly").grid(
            row=5, column=1, sticky="w", padx=4, pady=3
        )
        ttk.Button(right, text="Resim Yukle", command=self.pick_image).grid(row=5, column=2, padx=4, pady=3)

        self.preview_label = ttk.Label(right, text="Resim yok", width=26)
        self.preview_label.grid(row=6, column=0, columnspan=3, padx=4, pady=6, sticky="w")

        actions = ttk.Frame(form)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=(6, 2))
        ttk.Button(actions, text="Kaydet / Guncelle", style="Accent.TButton", command=self.save).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(actions, text="Yeni Kart", command=self.clear_form).pack(side="left", padx=6)
        ttk.Button(actions, text="Yenile", command=self.refresh).pack(side="left", padx=6)

        table = ttk.Frame(self, style="Card.TFrame")
        table.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        cols = (
            "id",
            "barcode",
            "name",
            "sell_price",
            "stock",
            "category",
            "unit",
            "supplier",
            "special_code",
        )
        self.tree = ttk.Treeview(table, columns=cols, show="headings")
        labels = {
            "id": "ID",
            "barcode": "Barkod",
            "name": "Urun",
            "sell_price": "Satis-1",
            "stock": "Stok",
            "category": "Kategori",
            "unit": "Birim",
            "supplier": "Tedarikci",
            "special_code": "Ozel Kod",
        }
        for c in cols:
            self.tree.heading(c, text=labels[c])
            self.tree.column(c, width=120 if c != "name" else 250, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)

    def _float(self, value: str) -> float:
        return float(value.replace(",", "."))

    def generate_barcode(self) -> None:
        barcode = generate_ean13("869")
        self.var_barcode.set(barcode)

    def _copy_image_to_media(self, src_path: str, barcode: str) -> str:
        ext = os.path.splitext(src_path)[1].lower() or ".png"
        safe_barcode = "".join(ch for ch in barcode if ch.isdigit()) or "urun"
        target_name = f"{safe_barcode}{ext}"
        target_path = os.path.join(self.media_dir, target_name)
        if os.path.abspath(src_path) == os.path.abspath(target_path):
            return target_path
        shutil.copy2(src_path, target_path)
        return target_path

    def pick_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Urun Resmi Sec",
            filetypes=[
                ("Resim Dosyalari", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"),
                ("Tum Dosyalar", "*.*"),
            ],
        )
        if not path:
            return
        self.var_image_path.set(path)
        self._show_preview(path)

    def _show_preview(self, path: str) -> None:
        if not path or not os.path.exists(path):
            self.preview_label.config(text="Resim yok", image="")
            self.preview_photo = None
            return

        if HAS_PILLOW:
            image = Image.open(path)
            image.thumbnail((180, 120))
            self.preview_photo = ImageTk.PhotoImage(image)
            self.preview_label.config(image=self.preview_photo, text="")
            return

        # Without Pillow, Tk only guarantees PNG/GIF support.
        lower = path.lower()
        if lower.endswith(".png") or lower.endswith(".gif"):
            try:
                self.preview_photo = tk.PhotoImage(file=path)
                self.preview_label.config(image=self.preview_photo, text="")
                return
            except Exception:
                pass
        self.preview_label.config(text="Onizleme icin Pillow gerekli", image="")
        self.preview_photo = None

    def clear_form(self) -> None:
        self.var_barcode.set("")
        self.var_name.set("")
        self.var_cost.set("0")
        self.var_sell.set("0")
        self.var_sell2.set("0")
        self.var_sell3.set("0")
        self.var_card.set("0")
        self.var_stock.set("0")
        self.var_critical.set("0")
        self.var_unit.set("Adet")
        self.var_category.set("")
        self.var_supplier.set("")
        self.var_special.set("")
        self.var_expiry.set("")
        self.var_image_path.set("")
        self._show_preview("")

    def save(self) -> None:
        barcode = self.var_barcode.get().strip()
        name = self.var_name.get().strip()
        if not barcode or not name:
            messagebox.showwarning("Eksik Bilgi", "Barkod ve urun adi zorunlu.")
            return

        try:
            cost = self._float(self.var_cost.get())
            sell = self._float(self.var_sell.get())
            sell2 = self._float(self.var_sell2.get())
            sell3 = self._float(self.var_sell3.get())
            card = self._float(self.var_card.get())
            stock = self._float(self.var_stock.get())
            critical = self._float(self.var_critical.get())
        except ValueError:
            messagebox.showerror("Hatali Giris", "Sayisal alanlar gecersiz.")
            return

        image_path = self.var_image_path.get().strip()
        if image_path and os.path.exists(image_path):
            image_path = self._copy_image_to_media(image_path, barcode)

        is_new = self.db.upsert_product(
            barcode=barcode,
            name=name,
            cost_price=cost,
            sell_price=sell,
            stock=stock,
            critical_stock=critical,
            sell_price_2=sell2,
            sell_price_3=sell3,
            card_price=card,
            image_path=image_path,
            unit=self.var_unit.get().strip(),
            category=self.var_category.get().strip(),
            supplier=self.var_supplier.get().strip(),
            special_code=self.var_special.get().strip(),
            expiry_date=self.var_expiry.get().strip(),
        )
        self.refresh()
        self.on_after_change()
        messagebox.showinfo("Basarili", "Urun eklendi." if is_new else "Urun guncellendi.")

    def _on_row_select(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        row_values = self.tree.item(selected[0], "values")
        if not row_values:
            return
        barcode = row_values[1]
        with self.db.conn() as conn:
            row = conn.execute(
                """
                SELECT barcode, name, cost_price, sell_price, sell_price_2, sell_price_3, card_price,
                       stock, critical_stock, image_path, unit, category, supplier, special_code, expiry_date
                FROM products
                WHERE barcode = ?
                """,
                (barcode,),
            ).fetchone()
        if not row:
            return
        (
            p_barcode,
            name,
            cost,
            sell,
            sell2,
            sell3,
            card,
            stock,
            critical,
            image_path,
            unit,
            category,
            supplier,
            special_code,
            expiry_date,
        ) = row
        self.var_barcode.set(p_barcode or "")
        self.var_name.set(name or "")
        self.var_cost.set(f"{cost:.2f}")
        self.var_sell.set(f"{sell:.2f}")
        self.var_sell2.set(f"{sell2:.2f}")
        self.var_sell3.set(f"{sell3:.2f}")
        self.var_card.set(f"{card:.2f}")
        self.var_stock.set(f"{stock:.2f}")
        self.var_critical.set(f"{critical:.2f}")
        self.var_image_path.set(image_path or "")
        self.var_unit.set(unit or "Adet")
        self.var_category.set(category or "")
        self.var_supplier.set(supplier or "")
        self.var_special.set(special_code or "")
        self.var_expiry.set(expiry_date or "")
        self._show_preview(image_path or "")

    def refresh(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        with self.db.conn() as conn:
            rows = conn.execute(
                """
                SELECT id, barcode, name, sell_price, stock, category, unit, supplier, special_code
                FROM products
                ORDER BY id DESC
                """
            ).fetchall()

        for row in rows:
            self.tree.insert("", "end", values=row)
