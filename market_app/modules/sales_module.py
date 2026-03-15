import os
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk

try:
    from PIL import Image, ImageTk  # type: ignore

    HAS_PILLOW = True
except Exception:
    HAS_PILLOW = False


class SalesModule(ttk.Frame):
    def __init__(self, parent, db, on_after_sale):
        super().__init__(parent)
        self.db = db
        self.on_after_sale = on_after_sale
        self.cart = []
        self.quick_buttons = []
        self.quick_images = {}

        self.var_barcode = tk.StringVar()
        self.var_qty = tk.StringVar(value="1")
        self.var_discount = tk.StringVar(value="0")
        self.var_payment_type = tk.StringVar(value="NAKIT")
        self.var_cash = tk.StringVar(value="0")
        self.var_pos = tk.StringVar(value="0")
        self.var_customer = tk.StringVar()

        self._build()
        self.refresh_customers()
        self.refresh_quick_buttons()

    def _build(self) -> None:
        split = ttk.Panedwindow(self, orient="horizontal")
        split.pack(fill="both", expand=True, padx=10, pady=10)

        left = ttk.Frame(split)
        right = ttk.Frame(split)
        split.add(left, weight=5)
        split.add(right, weight=3)

        form = ttk.LabelFrame(left, text="Barkod ile Satis")
        form.pack(fill="x", pady=(0, 10))
        ttk.Label(form, text="Barkod").grid(row=0, column=0, padx=4, pady=6)
        entry = ttk.Entry(form, textvariable=self.var_barcode, width=28)
        entry.grid(row=0, column=1, padx=4, pady=6)
        entry.focus_set()
        entry.bind("<Return>", lambda _: self.add_to_cart())
        ttk.Label(form, text="Miktar").grid(row=0, column=2, padx=4, pady=6)
        ttk.Entry(form, textvariable=self.var_qty, width=10).grid(row=0, column=3, padx=4, pady=6)
        ttk.Button(form, text="Ekle", style="Accent.TButton", command=self.add_to_cart).grid(row=0, column=4, padx=6)

        table = ttk.LabelFrame(left, text="Sepet")
        table.pack(fill="both", expand=True)
        cols = ("product_id", "barcode", "name", "qty", "price", "total")
        self.tree = ttk.Treeview(table, columns=cols, show="headings")
        labels = {"product_id": "PID", "barcode": "Barkod", "name": "Urun", "qty": "Miktar", "price": "Birim", "total": "Toplam"}
        for c in cols:
            self.tree.heading(c, text=labels[c])
            self.tree.column(c, width=85 if c in ("product_id", "qty") else 140, anchor="center")
        self.tree.column("name", width=250, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=sb.set)
        sb.pack(side="right", fill="y")

        top_right = ttk.LabelFrame(right, text="Hizli Urun Butonlari")
        top_right.pack(fill="both", expand=True, pady=(0, 8))
        self.quick_frame = ttk.Frame(top_right)
        self.quick_frame.pack(fill="both", expand=True, padx=6, pady=6)

        card = ttk.LabelFrame(right, text="Odeme Paneli")
        card.pack(fill="x")
        ttk.Label(card, text="Ara Toplam").grid(row=0, column=0, sticky="w", padx=8, pady=(10, 4))
        self.lbl_subtotal = ttk.Label(card, text="0.00")
        self.lbl_subtotal.grid(row=0, column=1, sticky="e", padx=8, pady=(10, 4))
        ttk.Label(card, text="Indirim").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(card, textvariable=self.var_discount, width=18).grid(row=1, column=1, padx=8, pady=4)
        ttk.Label(card, text="Odeme Tipi").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        combo = ttk.Combobox(
            card,
            textvariable=self.var_payment_type,
            values=["NAKIT", "POS", "NAKIT+POS", "VERESIYE"],
            state="readonly",
            width=16,
        )
        combo.grid(row=2, column=1, padx=8, pady=4)
        combo.bind("<<ComboboxSelected>>", lambda _: self._toggle_inputs())

        ttk.Label(card, text="Nakit").grid(row=3, column=0, sticky="w", padx=8, pady=4)
        self.ent_cash = ttk.Entry(card, textvariable=self.var_cash, width=18)
        self.ent_cash.grid(row=3, column=1, padx=8, pady=4)
        ttk.Label(card, text="POS").grid(row=4, column=0, sticky="w", padx=8, pady=4)
        self.ent_pos = ttk.Entry(card, textvariable=self.var_pos, width=18)
        self.ent_pos.grid(row=4, column=1, padx=8, pady=4)
        ttk.Label(card, text="Musteri").grid(row=5, column=0, sticky="w", padx=8, pady=4)
        self.combo_customer = ttk.Combobox(card, textvariable=self.var_customer, state="readonly", width=16)
        self.combo_customer.grid(row=5, column=1, padx=8, pady=4)
        ttk.Label(card, text="Net Toplam").grid(row=6, column=0, sticky="w", padx=8, pady=(8, 4))
        self.lbl_total = ttk.Label(card, text="0.00")
        self.lbl_total.grid(row=6, column=1, sticky="e", padx=8, pady=(8, 4))
        ttk.Button(card, text="Satisi Tamamla", style="Accent.TButton", command=self.complete_sale).grid(
            row=7, column=0, columnspan=2, sticky="ew", padx=8, pady=(10, 6)
        )
        ttk.Button(card, text="Sepeti Temizle", command=self.clear_cart).grid(
            row=8, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 10)
        )

        self._toggle_inputs()

    def _float(self, value: str) -> float:
        return float(value.replace(",", "."))

    def _safe_float(self, value: str) -> float:
        try:
            return self._float(value)
        except ValueError:
            return 0.0

    def _parse_customer_id(self):
        try:
            return int(self.var_customer.get().split(" - ")[0])
        except (ValueError, IndexError):
            return None

    def _toggle_inputs(self):
        mode = self.var_payment_type.get()
        if mode == "NAKIT":
            self.ent_cash.configure(state="normal")
            self.ent_pos.configure(state="disabled")
            self.combo_customer.configure(state="disabled")
        elif mode == "POS":
            self.ent_cash.configure(state="disabled")
            self.ent_pos.configure(state="normal")
            self.combo_customer.configure(state="disabled")
        elif mode == "NAKIT+POS":
            self.ent_cash.configure(state="normal")
            self.ent_pos.configure(state="normal")
            self.combo_customer.configure(state="disabled")
        else:
            self.ent_cash.configure(state="disabled")
            self.ent_pos.configure(state="disabled")
            self.combo_customer.configure(state="readonly")

    def refresh_customers(self):
        with self.db.conn() as conn:
            rows = conn.execute("SELECT id, name FROM customers ORDER BY name").fetchall()
        self.combo_customer["values"] = [f"{r[0]} - {r[1]}" for r in rows]

    def _load_thumbnail(self, image_path: str):
        if not image_path or not os.path.exists(image_path):
            return None
        if HAS_PILLOW:
            image = Image.open(image_path)
            image.thumbnail((70, 54))
            return ImageTk.PhotoImage(image)
        if image_path.lower().endswith(".png") or image_path.lower().endswith(".gif"):
            try:
                return tk.PhotoImage(file=image_path)
            except Exception:
                return None
        return None

    def refresh_quick_buttons(self):
        for child in self.quick_frame.winfo_children():
            child.destroy()
        self.quick_images = {}

        limit = int(self.db.get_setting("quick_button_count", "24") or "24")
        with self.db.conn() as conn:
            rows = conn.execute(
                """
                SELECT p.id, p.name, p.image_path, p.barcode
                FROM products p
                ORDER BY p.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        col_count = 4
        for idx, (product_id, name, image_path, barcode) in enumerate(rows):
            r = idx // col_count
            c = idx % col_count
            photo = self._load_thumbnail(image_path or "")
            if photo:
                self.quick_images[product_id] = photo
                btn = ttk.Button(
                    self.quick_frame,
                    text=name[:14],
                    image=photo,
                    compound="top",
                    command=lambda pid=product_id: self.add_product_by_id(pid),
                    width=14,
                )
            else:
                text = f"{name[:12]}\n{barcode or ''}"
                btn = ttk.Button(
                    self.quick_frame,
                    text=text,
                    command=lambda pid=product_id: self.add_product_by_id(pid),
                    width=14,
                )
            btn.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")
            self.quick_buttons.append(btn)

        for col in range(col_count):
            self.quick_frame.columnconfigure(col, weight=1)

    def add_to_cart(self):
        barcode = self.var_barcode.get().strip()
        if not barcode:
            messagebox.showwarning("Eksik Bilgi", "Barkod gerekli.")
            return

        try:
            qty = self._float(self.var_qty.get())
        except ValueError:
            messagebox.showerror("Hatali Giris", "Miktar sayisal olmali.")
            return
        if qty <= 0:
            messagebox.showerror("Hatali Giris", "Miktar 0'dan buyuk olmali.")
            return

        with self.db.conn() as conn:
            row = conn.execute(
                """
                SELECT id, barcode, name, sell_price, sell_price_2, sell_price_3, card_price, cost_price, stock
                FROM products
                WHERE barcode=?
                """,
                (barcode,),
            ).fetchone()
        if not row:
            messagebox.showerror("Bulunamadi", "Urun bulunamadi.")
            return

        product_id, p_barcode, name, sell_price, sell2, sell3, card_price, cost_price, stock = row
        unit_price = self._pick_price(sell_price, sell2, sell3, card_price)
        if stock < qty:
            messagebox.showerror("Yetersiz Stok", f"Mevcut stok: {stock}")
            return

        for item in self.cart:
            if item["product_id"] == product_id:
                if stock < (item["qty"] + qty):
                    messagebox.showerror("Yetersiz Stok", f"Mevcut stok: {stock}")
                    return
                item["qty"] += qty
                item["line_total"] = item["qty"] * item["unit_price"]
                self.refresh_cart()
                self.var_barcode.set("")
                return

        self.cart.append(
            {
                "product_id": product_id,
                "barcode": p_barcode,
                "name": name,
                "qty": qty,
                "unit_price": float(unit_price),
                "cost_price": float(cost_price),
                "line_total": qty * float(unit_price),
            }
        )
        self.var_barcode.set("")
        self.refresh_cart()

    def add_product_by_id(self, product_id: int):
        with self.db.conn() as conn:
            row = conn.execute(
                """
                SELECT id, barcode, name, sell_price, sell_price_2, sell_price_3, card_price, cost_price, stock
                FROM products
                WHERE id=?
                """,
                (product_id,),
            ).fetchone()
        if not row:
            return

        try:
            qty = self._float(self.var_qty.get())
        except ValueError:
            qty = 1.0
            self.var_qty.set("1")

        pid, barcode, name, sell, sell2, sell3, card, cost, stock = row
        if stock < qty:
            messagebox.showerror("Yetersiz Stok", f"{name} urununde stok yetersiz.")
            return
        unit_price = self._pick_price(sell, sell2, sell3, card)
        for item in self.cart:
            if item["product_id"] == pid:
                if stock < item["qty"] + qty:
                    messagebox.showerror("Yetersiz Stok", f"{name} urununde stok yetersiz.")
                    return
                item["qty"] += qty
                item["line_total"] = item["qty"] * item["unit_price"]
                self.refresh_cart()
                return
        self.cart.append(
            {
                "product_id": pid,
                "barcode": barcode,
                "name": name,
                "qty": qty,
                "unit_price": float(unit_price),
                "cost_price": float(cost),
                "line_total": qty * float(unit_price),
            }
        )
        self.refresh_cart()

    def _pick_price(self, sell: float, sell2: float, sell3: float, card: float) -> float:
        key = self.db.get_setting("default_price_type", "sell_price")
        if key == "sell_price_2" and sell2 > 0:
            return float(sell2)
        if key == "sell_price_3" and sell3 > 0:
            return float(sell3)
        if key == "card_price" and card > 0:
            return float(card)
        return float(sell)

    def refresh_cart(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        subtotal = 0.0
        for item in self.cart:
            subtotal += item["line_total"]
            self.tree.insert(
                "",
                "end",
                values=(
                    item["product_id"],
                    item["barcode"],
                    item["name"],
                    f"{item['qty']:.2f}",
                    f"{item['unit_price']:.2f}",
                    f"{item['line_total']:.2f}",
                ),
            )

        discount = self._safe_float(self.var_discount.get())
        if discount < 0:
            discount = 0.0
        if discount > subtotal:
            discount = subtotal

        total = subtotal - discount
        self.lbl_subtotal.config(text=f"{subtotal:.2f}")
        self.lbl_total.config(text=f"{total:.2f}")

    def clear_cart(self):
        self.cart.clear()
        self.var_discount.set("0")
        self.var_cash.set("0")
        self.var_pos.set("0")
        self.var_qty.set("1")
        self.var_barcode.set("")
        self.refresh_cart()

    def complete_sale(self):
        if not self.cart:
            messagebox.showwarning("Bos Sepet", "Sepette urun yok.")
            return

        subtotal = sum(item["line_total"] for item in self.cart)
        discount = self._safe_float(self.var_discount.get())
        if discount < 0 or discount > subtotal:
            messagebox.showerror("Hatali Indirim", "Indirim gecersiz.")
            return
        total = subtotal - discount
        payment_type = self.var_payment_type.get()
        cash_amount = 0.0
        pos_amount = 0.0
        customer_id = None

        if payment_type == "NAKIT":
            cash_amount = total
        elif payment_type == "POS":
            pos_amount = total
        elif payment_type == "NAKIT+POS":
            cash_amount = self._safe_float(self.var_cash.get())
            pos_amount = self._safe_float(self.var_pos.get())
            if abs((cash_amount + pos_amount) - total) > 0.01:
                messagebox.showerror("Odeme Hatasi", "Nakit + POS toplami net toplama esit olmali.")
                return
        elif payment_type == "VERESIYE":
            customer_id = self._parse_customer_id()
            if not customer_id:
                messagebox.showerror("Eksik Bilgi", "Veresiye icin musteri seciniz.")
                return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.db.conn() as conn:
            cur = conn.cursor()
            for item in self.cart:
                stock_row = cur.execute("SELECT stock FROM products WHERE id=?", (item["product_id"],)).fetchone()
                if not stock_row or stock_row[0] < item["qty"]:
                    conn.rollback()
                    messagebox.showerror("Stok Hatasi", f"Yetersiz stok: {item['name']}")
                    return

            cur.execute(
                """
                INSERT INTO sales (sale_time, subtotal, discount, total, payment_type, cash_amount, pos_amount, customer_id, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (now, subtotal, discount, total, payment_type, cash_amount, pos_amount, customer_id, ""),
            )
            sale_id = cur.lastrowid

            for item in self.cart:
                cur.execute(
                    """
                    INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, cost_price, line_total)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sale_id,
                        item["product_id"],
                        item["qty"],
                        item["unit_price"],
                        item["cost_price"],
                        item["line_total"],
                    ),
                )
                cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (item["qty"], item["product_id"]))

            if payment_type == "VERESIYE" and customer_id:
                cur.execute("UPDATE customers SET balance = balance + ? WHERE id = ?", (total, customer_id))
            conn.commit()

        self.clear_cart()
        self.on_after_sale()
        messagebox.showinfo("Basarili", f"Satis kaydedildi. Net: {total:.2f}")
