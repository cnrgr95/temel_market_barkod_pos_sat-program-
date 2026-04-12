from datetime import date, timedelta
import flet as ft

EXPENSE_CATEGORIES = [
    ("", "— Kategori Yok —"),
    ("Elektrik", "Elektrik"),
    ("Su", "Su"),
    ("Kira", "Kira"),
    ("Tamir", "Tamir / Bakım"),
    ("Personel", "Personel Maaşı"),
    ("Vergi", "Vergi / SGK"),
    ("Diger", "Diğer"),
]


class CashPage(ft.Container):
    def __init__(self, db):
        self.db = db

        # ── Date filters ──────────────────────────────────────────────────────
        self.txt_cash_from = ft.TextField(
            label="Başlangıç",
            width=130,
            value=(date.today() - timedelta(days=30)).strftime("%Y-%m-%d"),
            hint_text="YYYY-AA-GG",
            dense=True,
        )
        self.txt_cash_to = ft.TextField(
            label="Bitiş",
            width=130,
            value=date.today().strftime("%Y-%m-%d"),
            hint_text="YYYY-AA-GG",
            dense=True,
        )

        # ── Movement form ─────────────────────────────────────────────────────
        self.dd_type = ft.Dropdown(
            label="İşlem Tipi",
            value="IN",
            width=160,
            dense=True,
            options=[
                ft.dropdown.Option("IN", "Giriş (IN)"),
                ft.dropdown.Option("OUT", "Çıkış (OUT)"),
            ],
            on_select=self._on_type_changed,
        )
        self.dd_expense_category = ft.Dropdown(
            label="Gider Kategorisi",
            width=200,
            dense=True,
            visible=False,
            options=[
                ft.dropdown.Option(key, label) for key, label in EXPENSE_CATEGORIES
            ],
        )
        self.txt_amount = ft.TextField(
            label="Tutar (₺)", value="0", width=140, dense=True
        )
        self.txt_note = ft.TextField(label="Açıklama", expand=True, dense=True)

        # ── Summary labels ────────────────────────────────────────────────────
        self.lbl_balance = ft.Text(
            "Kasa Bakiyesi: -.-- ₺",
            size=18,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.GREEN_700,
        )
        self.lbl_in_total = ft.Text("Giriş: 0.00 ₺", size=13, color=ft.Colors.GREEN_700)
        self.lbl_out_total = ft.Text("Çıkış: 0.00 ₺", size=13, color=ft.Colors.RED_700)

        # ── Movements table ───────────────────────────────────────────────────
        self.table = ft.DataTable(
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            heading_row_color=ft.Colors.INDIGO_50,
            column_spacing=16,
            columns=[
                ft.DataColumn(ft.Text("Tarih/Saat", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Tip", weight=ft.FontWeight.W_600)),
                ft.DataColumn(
                    ft.Text("Tutar (₺)", weight=ft.FontWeight.W_600), numeric=True
                ),
                ft.DataColumn(ft.Text("Kategori", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Not", weight=ft.FontWeight.W_600)),
            ],
            rows=[],
        )

        # ── Expense summary table ─────────────────────────────────────────────
        self.expense_table = ft.DataTable(
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            heading_row_color=ft.Colors.RED_50,
            column_spacing=16,
            columns=[
                ft.DataColumn(ft.Text("Gider Kategorisi", weight=ft.FontWeight.W_600)),
                ft.DataColumn(
                    ft.Text("Adet", weight=ft.FontWeight.W_600), numeric=True
                ),
                ft.DataColumn(
                    ft.Text("Toplam (₺)", weight=ft.FontWeight.W_600), numeric=True
                ),
            ],
            rows=[],
        )

        content = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=14,
            controls=[
                ft.Text("Kasa Yönetimi", size=26, weight=ft.FontWeight.BOLD),
                # Balance card
                ft.Container(
                    bgcolor=ft.Colors.GREEN_50,
                    border_radius=12,
                    padding=ft.padding.symmetric(horizontal=20, vertical=14),
                    border=ft.border.all(2, ft.Colors.GREEN_200),
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.ACCOUNT_BALANCE_WALLET,
                                color=ft.Colors.GREEN_700,
                                size=32,
                            ),
                            self.lbl_balance,
                            ft.Container(expand=True),
                            self.lbl_in_total,
                            ft.VerticalDivider(width=1, color=ft.Colors.GREEN_200),
                            self.lbl_out_total,
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                # New movement form
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    padding=14,
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "Yeni Kasa Hareketi",
                                size=14,
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.INDIGO_700,
                            ),
                            ft.Row(
                                [
                                    self.dd_type,
                                    self.dd_expense_category,
                                    self.txt_amount,
                                    self.txt_note,
                                    ft.ElevatedButton(
                                        "Kaydet",
                                        icon=ft.Icons.SAVE,
                                        on_click=self._save,
                                    ),
                                ],
                                spacing=10,
                                wrap=True,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ],
                        spacing=10,
                    ),
                ),
                # Movement list with date filter
                ft.Row(
                    [
                        ft.Text(
                            "Kasa Hareketleri",
                            size=14,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.BLUE_GREY_700,
                        ),
                        self.txt_cash_from,
                        ft.Text("—", size=13),
                        self.txt_cash_to,
                        ft.ElevatedButton(
                            "Filtrele",
                            icon=ft.Icons.FILTER_ALT,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.INDIGO_600,
                                color=ft.Colors.WHITE,
                            ),
                            height=38,
                            on_click=lambda _: self._refresh_moves(),
                        ),
                    ],
                    spacing=8,
                    wrap=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(
                    content=ft.Column([self.table], scroll=ft.ScrollMode.AUTO),
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    padding=10,
                ),
                # Expense summary
                ft.Text(
                    "Gider Özeti (Seçili Dönem)",
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=ft.Colors.RED_700,
                ),
                ft.Container(
                    content=ft.Column([self.expense_table], scroll=ft.ScrollMode.AUTO),
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    padding=10,
                ),
            ],
        )
        super().__init__(expand=True, content=content)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _safe_update(self):
        if self.page is None:
            return
        try:
            self.page.update()
        except Exception:
            pass

    def _snack(self, text: str):
        if self.page is None:
            return
        try:
            self.page.snack_bar = ft.SnackBar(ft.Text(text), open=True)
            self.page.update()
        except Exception:
            pass

    def _to_float(self, value: str) -> float:
        try:
            return float((value or "").replace(",", "."))
        except ValueError:
            return 0.0

    def _on_type_changed(self, _e):
        """Gider kategorisi sadece OUT işleminde görünür."""
        self.dd_expense_category.visible = (self.dd_type.value == "OUT")
        self._safe_update()

    # ── Save movement ─────────────────────────────────────────────────────────

    def _save(self, _e: ft.ControlEvent):
        amt = self._to_float(self.txt_amount.value)
        if amt <= 0:
            self._snack("Geçerli bir tutar giriniz")
            return
        move_type = self.dd_type.value or "IN"
        expense_cat = ""
        if move_type == "OUT":
            expense_cat = self.dd_expense_category.value or ""
        self.db.add_cash_move(
            move_type,
            amt,
            (self.txt_note.value or "").strip(),
            expense_category=expense_cat,
        )
        self.txt_amount.value = "0"
        self.txt_note.value = ""
        self.dd_expense_category.value = None
        self.refresh()

    # ── Movement list ─────────────────────────────────────────────────────────

    def _refresh_moves(self):
        date_from = (self.txt_cash_from.value or "").strip()
        date_to = (self.txt_cash_to.value or "").strip()
        try:
            rows = self.db.list_cash_moves(date_from=date_from, date_to=date_to)
        except TypeError:
            rows = self.db.list_cash_moves()

        in_total = out_total = 0.0
        self.table.rows = []
        for r in rows:
            # move_time, move_type, amount, note, expense_category, sale_id
            move_type = r[1] or ""
            amt = float(r[2] or 0)
            note = r[3] or ""
            expense_cat = r[4] if len(r) > 4 else ""
            type_color = (
                ft.Colors.GREEN_700 if move_type == "IN" else ft.Colors.RED_700
            )
            if move_type == "IN":
                in_total += amt
            else:
                out_total += amt
            self.table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(r[0] or "")[:16], size=11)),
                        ft.DataCell(
                            ft.Text(
                                move_type,
                                color=type_color,
                                weight=ft.FontWeight.W_600,
                                size=12,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(f"{amt:,.2f}", color=type_color, size=12)
                        ),
                        ft.DataCell(
                            ft.Text(
                                expense_cat or "—",
                                size=11,
                                color=ft.Colors.RED_700
                                if expense_cat
                                else ft.Colors.BLUE_GREY_300,
                            )
                        ),
                        ft.DataCell(ft.Text(note, size=11)),
                    ]
                )
            )

        self.lbl_in_total.value = f"Giriş: {in_total:,.2f} ₺"
        self.lbl_out_total.value = f"Çıkış: {out_total:,.2f} ₺"

        # Expense summary
        try:
            expense_rows = self.db.get_cash_expense_summary(
                date_from=date_from, date_to=date_to
            )
        except Exception:
            expense_rows = []

        self.expense_table.rows = []
        for er in expense_rows:
            cat_name, count, total_amt = er[0], int(er[1]), float(er[2])
            self.expense_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Text(
                                cat_name or "Diğer",
                                size=12,
                                weight=ft.FontWeight.W_500,
                            )
                        ),
                        ft.DataCell(ft.Text(str(count), size=12)),
                        ft.DataCell(
                            ft.Text(
                                f"{total_amt:,.2f}",
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.RED_700,
                            )
                        ),
                    ]
                )
            )
        if not self.expense_table.rows:
            self.expense_table.rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Text(
                                "Bu dönemde gider kaydı yok",
                                color=ft.Colors.BLUE_GREY_300,
                                italic=True,
                            )
                        ),
                        ft.DataCell(ft.Text("")),
                        ft.DataCell(ft.Text("")),
                    ]
                )
            ]

        self._safe_update()

    # ── Main refresh ──────────────────────────────────────────────────────────

    def refresh(self):
        balance = self.db.get_cash_balance()
        color = ft.Colors.GREEN_700 if balance >= 0 else ft.Colors.RED_700
        self.lbl_balance.value = f"Kasa Bakiyesi: {balance:,.2f} ₺"
        self.lbl_balance.color = color
        self._refresh_moves()
