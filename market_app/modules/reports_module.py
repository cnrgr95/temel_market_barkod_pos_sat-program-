from datetime import datetime
import tkinter as tk
from tkinter import ttk


class ReportsModule(ttk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        today = datetime.now().strftime("%Y-%m-%d")
        self.var_from = tk.StringVar(value=today)
        self.var_to = tk.StringVar(value=today)
        self._build()
        self.refresh()

    def _build(self):
        filters = ttk.LabelFrame(self, text="Rapor Filtresi")
        filters.pack(fill="x", padx=10, pady=10)
        ttk.Label(filters, text="Baslangic (YYYY-AA-GG)").grid(row=0, column=0, padx=4, pady=6)
        ttk.Entry(filters, textvariable=self.var_from, width=15).grid(row=0, column=1, padx=4, pady=6)
        ttk.Label(filters, text="Bitis (YYYY-AA-GG)").grid(row=0, column=2, padx=4, pady=6)
        ttk.Entry(filters, textvariable=self.var_to, width=15).grid(row=0, column=3, padx=4, pady=6)
        ttk.Button(filters, text="Raporu Getir", style="Accent.TButton", command=self.refresh).grid(row=0, column=4, padx=8)

        cards = ttk.Frame(self)
        cards.pack(fill="x", padx=10)
        self.lbl_sales = ttk.Label(cards, text="Toplam Ciro: 0.00")
        self.lbl_sales.pack(anchor="w", pady=2)
        self.lbl_profit = ttk.Label(cards, text="Tahmini Kar: 0.00")
        self.lbl_profit.pack(anchor="w", pady=2)
        self.lbl_cash = ttk.Label(cards, text="Nakit: 0.00")
        self.lbl_cash.pack(anchor="w", pady=2)
        self.lbl_pos = ttk.Label(cards, text="POS: 0.00")
        self.lbl_pos.pack(anchor="w", pady=2)
        self.lbl_credit = ttk.Label(cards, text="Veresiye: 0.00")
        self.lbl_credit.pack(anchor="w", pady=2)

        critical = ttk.LabelFrame(self, text="Kritik Stok")
        critical.pack(fill="both", expand=True, padx=10, pady=10)
        cols = ("barcode", "name", "stock", "critical_stock")
        self.tree = ttk.Treeview(critical, columns=cols, show="headings")
        self.tree.heading("barcode", text="Barkod")
        self.tree.heading("name", text="Urun")
        self.tree.heading("stock", text="Stok")
        self.tree.heading("critical_stock", text="Kritik")
        self.tree.column("barcode", width=180, anchor="center")
        self.tree.column("name", width=360, anchor="center")
        self.tree.column("stock", width=120, anchor="center")
        self.tree.column("critical_stock", width=120, anchor="center")
        self.tree.pack(fill="both", expand=True)

    def refresh(self):
        dt_from = f"{self.var_from.get().strip()} 00:00:00"
        dt_to = f"{self.var_to.get().strip()} 23:59:59"

        with self.db.conn() as conn:
            sales = conn.execute(
                "SELECT COALESCE(SUM(total), 0) FROM sales WHERE sale_time BETWEEN ? AND ?",
                (dt_from, dt_to),
            ).fetchone()[0]
            profit = conn.execute(
                """
                SELECT COALESCE(SUM((si.unit_price - si.cost_price) * si.quantity), 0)
                FROM sale_items si
                JOIN sales s ON s.id = si.sale_id
                WHERE s.sale_time BETWEEN ? AND ?
                """,
                (dt_from, dt_to),
            ).fetchone()[0]
            cash = conn.execute(
                "SELECT COALESCE(SUM(cash_amount), 0) FROM sales WHERE sale_time BETWEEN ? AND ?",
                (dt_from, dt_to),
            ).fetchone()[0]
            pos = conn.execute(
                "SELECT COALESCE(SUM(pos_amount), 0) FROM sales WHERE sale_time BETWEEN ? AND ?",
                (dt_from, dt_to),
            ).fetchone()[0]
            credit = conn.execute(
                "SELECT COALESCE(SUM(total), 0) FROM sales WHERE payment_type='VERESIYE' AND sale_time BETWEEN ? AND ?",
                (dt_from, dt_to),
            ).fetchone()[0]
            critical_rows = conn.execute(
                """
                SELECT barcode, name, stock, critical_stock
                FROM products
                WHERE stock <= critical_stock
                ORDER BY stock ASC
                """
            ).fetchall()

        self.lbl_sales.config(text=f"Toplam Ciro: {sales:.2f}")
        self.lbl_profit.config(text=f"Tahmini Kar: {profit:.2f}")
        self.lbl_cash.config(text=f"Nakit: {cash:.2f}")
        self.lbl_pos.config(text=f"POS: {pos:.2f}")
        self.lbl_credit.config(text=f"Veresiye: {credit:.2f}")

        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in critical_rows:
            self.tree.insert("", "end", values=row)
