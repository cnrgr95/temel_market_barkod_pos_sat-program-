from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox


class CustomersModule(ttk.Frame):
    def __init__(self, parent, db, on_after_change):
        super().__init__(parent)
        self.db = db
        self.on_after_change = on_after_change

        self.var_name = tk.StringVar()
        self.var_phone = tk.StringVar()
        self.var_pay_customer = tk.StringVar()
        self.var_pay_amount = tk.StringVar(value="0")
        self.var_pay_method = tk.StringVar(value="NAKIT")
        self.var_pay_note = tk.StringVar()

        self._build()
        self.refresh()

    def _build(self) -> None:
        form = ttk.LabelFrame(self, text="Musteri Ekle")
        form.pack(fill="x", padx=10, pady=10)
        ttk.Label(form, text="Ad Soyad").grid(row=0, column=0, padx=4, pady=6)
        ttk.Entry(form, textvariable=self.var_name, width=30).grid(row=0, column=1, padx=4, pady=6)
        ttk.Label(form, text="Telefon").grid(row=0, column=2, padx=4, pady=6)
        ttk.Entry(form, textvariable=self.var_phone, width=20).grid(row=0, column=3, padx=4, pady=6)
        ttk.Button(form, text="Musteri Kaydet", style="Accent.TButton", command=self.save_customer).grid(
            row=0, column=4, padx=8
        )

        pay = ttk.LabelFrame(self, text="Tahsilat")
        pay.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Label(pay, text="Musteri").grid(row=0, column=0, padx=4, pady=6)
        self.combo_customer = ttk.Combobox(pay, textvariable=self.var_pay_customer, width=30, state="readonly")
        self.combo_customer.grid(row=0, column=1, padx=4, pady=6)
        ttk.Label(pay, text="Tutar").grid(row=0, column=2, padx=4, pady=6)
        ttk.Entry(pay, textvariable=self.var_pay_amount, width=12).grid(row=0, column=3, padx=4, pady=6)
        ttk.Label(pay, text="Yontem").grid(row=0, column=4, padx=4, pady=6)
        ttk.Combobox(
            pay,
            textvariable=self.var_pay_method,
            values=["NAKIT", "KREDI_KARTI", "BANKA", "CEK", "ACIK_HESAP"],
            state="readonly",
            width=16,
        ).grid(row=0, column=5, padx=4, pady=6)
        ttk.Label(pay, text="Not").grid(row=0, column=6, padx=4, pady=6)
        ttk.Entry(pay, textvariable=self.var_pay_note, width=24).grid(row=0, column=7, padx=4, pady=6)
        ttk.Button(pay, text="Tahsilat Kaydet", command=self.save_payment).grid(row=0, column=8, padx=8)

        table = ttk.Frame(self, style="Card.TFrame")
        table.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        cols = ("id", "name", "phone", "balance")
        self.tree = ttk.Treeview(table, columns=cols, show="headings")
        for c, text in [("id", "ID"), ("name", "Musteri"), ("phone", "Telefon"), ("balance", "Bakiye")]:
            self.tree.heading(c, text=text)
            self.tree.column(c, width=120 if c != "name" else 320, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=sb.set)
        sb.pack(side="right", fill="y")

    def _parse_customer_id(self, value: str):
        if not value:
            return None
        try:
            return int(value.split(" - ")[0])
        except (ValueError, IndexError):
            return None

    def _float(self, value: str) -> float:
        return float(value.replace(",", "."))

    def refresh(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        with self.db.conn() as conn:
            rows = conn.execute("SELECT id, name, phone, balance FROM customers ORDER BY id DESC").fetchall()
            combo_rows = conn.execute("SELECT id, name FROM customers ORDER BY name").fetchall()
        for row in rows:
            self.tree.insert("", "end", values=row)
        self.combo_customer["values"] = [f"{r[0]} - {r[1]}" for r in combo_rows]

    def save_customer(self) -> None:
        name = self.var_name.get().strip()
        phone = self.var_phone.get().strip()
        if not name:
            messagebox.showwarning("Eksik Bilgi", "Musteri adi zorunlu.")
            return

        with self.db.conn() as conn:
            conn.execute(
                "INSERT INTO customers (name, phone, balance, created_at) VALUES (?, ?, 0, ?)",
                (name, phone, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()
        self.var_name.set("")
        self.var_phone.set("")
        self.refresh()
        self.on_after_change()
        messagebox.showinfo("Basarili", "Musteri eklendi.")

    def save_payment(self) -> None:
        customer_id = self._parse_customer_id(self.var_pay_customer.get())
        if not customer_id:
            messagebox.showwarning("Eksik Bilgi", "Musteri seciniz.")
            return
        try:
            amount = self._float(self.var_pay_amount.get())
        except ValueError:
            messagebox.showerror("Hatali Tutar", "Tutar sayisal olmalidir.")
            return
        if amount <= 0:
            messagebox.showerror("Hatali Tutar", "Tutar 0'dan buyuk olmali.")
            return

        with self.db.conn() as conn:
            conn.execute(
                "INSERT INTO payments (customer_id, payment_time, amount, payment_method, note) VALUES (?, ?, ?, ?, ?)",
                (
                    customer_id,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    amount,
                    self.var_pay_method.get(),
                    self.var_pay_note.get().strip(),
                ),
            )
            conn.execute("UPDATE customers SET balance = balance - ? WHERE id = ?", (amount, customer_id))
            conn.commit()

        self.var_pay_amount.set("0")
        self.var_pay_note.set("")
        self.refresh()
        self.on_after_change()
        messagebox.showinfo("Basarili", "Tahsilat kaydedildi.")
