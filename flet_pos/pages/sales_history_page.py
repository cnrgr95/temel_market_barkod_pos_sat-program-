from datetime import datetime, timedelta
import flet as ft


class SalesHistoryPage(ft.Container):
    def __init__(self, db):
        super().__init__(expand=True)
        self.db = db

        today = datetime.now()
        fmt = "%Y-%m-%d"

        self.txt_date_from = ft.TextField(
            label="Baslangic", value=(today - timedelta(days=30)).strftime(fmt),
            width=140, hint_text="YYYY-AA-GG",
        )
        self.txt_date_to = ft.TextField(
            label="Bitis", value=today.strftime(fmt),
            width=140, hint_text="YYYY-AA-GG",
        )
        self.dd_payment_filter = ft.Dropdown(
            label="Odeme Tipi",
            width=160,
            value="TUMU",
            options=[
                ft.dropdown.Option("TUMU"),
                ft.dropdown.Option("NAKIT"),
                ft.dropdown.Option("POS"),
                ft.dropdown.Option("NAKIT+POS"),
                ft.dropdown.Option("HAVALE"),
                ft.dropdown.Option("VERESIYE"),
            ],
        )
        self.chk_returns = ft.Checkbox(label="Iadeleri Goster", value=False)

        # Özet etiketleri
        self.lbl_count = ft.Text("0 islem", weight=ft.FontWeight.W_600)
        self.lbl_sum = ft.Text("Toplam: 0.00 TL", weight=ft.FontWeight.W_600, color=ft.Colors.INDIGO_700)
        self.lbl_cash = ft.Text("Nakit: 0.00", size=12)
        self.lbl_card = ft.Text("Kart: 0.00", size=12)
        self.lbl_transfer = ft.Text("Havale: 0.00", size=12)

        # Ana satış tablosu
        self.sales_table = ft.DataTable(
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            heading_row_color=ft.Colors.INDIGO_50,
            column_spacing=16,
            columns=[
                ft.DataColumn(ft.Text("#", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Tarih/Saat", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Odeme", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Indirim", weight=ft.FontWeight.W_600), numeric=True),
                ft.DataColumn(ft.Text("Toplam (TL)", weight=ft.FontWeight.W_600), numeric=True),
                ft.DataColumn(ft.Text("Tip", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Detay", weight=ft.FontWeight.W_600)),
            ],
            rows=[],
        )

        # Detay paneli
        self.detail_col = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            controls=[ft.Text("Satisa tiklayin...", color=ft.Colors.BLUE_GREY_400, italic=True)],
        )

        self.content = ft.Column(
            expand=True, scroll=ft.ScrollMode.AUTO, spacing=14,
            controls=[
                ft.Text("Satis Hareketleri", size=26, weight=ft.FontWeight.BOLD),
                # Filtre paneli
                ft.Container(
                    bgcolor=ft.Colors.WHITE, border_radius=12, padding=14,
                    content=ft.Column(spacing=8, controls=[
                        ft.Text("Filtrele", size=14, weight=ft.FontWeight.W_600,
                                color=ft.Colors.INDIGO_700),
                        ft.Row([
                            self.txt_date_from,
                            ft.Text("—", size=16),
                            self.txt_date_to,
                            self.dd_payment_filter,
                            self.chk_returns,
                            ft.ElevatedButton("Ara", icon=ft.Icons.SEARCH, on_click=lambda _: self.refresh()),
                            ft.OutlinedButton("Bugun", on_click=lambda _: self._set_today()),
                            ft.OutlinedButton("Bu Hafta", on_click=lambda _: self._set_week()),
                            ft.OutlinedButton("Bu Ay", on_click=lambda _: self._set_month()),
                        ], wrap=True, spacing=8),
                    ]),
                ),
                # Özet kartlar
                ft.Container(
                    bgcolor=ft.Colors.WHITE, border_radius=12, padding=14,
                    content=ft.Row([
                        self._summary_card("ISLEM", self.lbl_count, ft.Colors.INDIGO_100),
                        self._summary_card("TOPLAM", self.lbl_sum, ft.Colors.GREEN_100),
                        self._summary_card("NAKIT", self.lbl_cash, ft.Colors.BLUE_100),
                        self._summary_card("KART", self.lbl_card, ft.Colors.ORANGE_100),
                        self._summary_card("HAVALE", self.lbl_transfer, ft.Colors.PURPLE_100),
                    ], wrap=True, spacing=10),
                ),
                # Tablo + detay
                ft.Row(expand=True, spacing=10, controls=[
                    ft.Container(
                        expand=3,
                        content=ft.Column([self.sales_table], scroll=ft.ScrollMode.AUTO),
                        bgcolor=ft.Colors.WHITE, border_radius=12, padding=8,
                    ),
                    ft.Container(
                        expand=2,
                        bgcolor=ft.Colors.WHITE, border_radius=12, padding=12,
                        content=ft.Column([
                            ft.Text("Satis Detayi", size=14, weight=ft.FontWeight.W_600,
                                    color=ft.Colors.INDIGO_700),
                            ft.Divider(),
                            self.detail_col,
                        ]),
                    ),
                ]),
            ],
        )
        self.refresh()

    def _summary_card(self, title: str, lbl: ft.Text, color) -> ft.Container:
        return ft.Container(
            bgcolor=color, border_radius=10, padding=10, width=150,
            content=ft.Column([
                ft.Text(title, size=11, color=ft.Colors.BLUE_GREY_700),
                lbl,
            ], spacing=2),
        )

    # ── Filtre kısayolları ────────────────────────────────────────────────────

    def _set_today(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.txt_date_from.value = today
        self.txt_date_to.value = today
        self.refresh()
        self._safe_update()

    def _set_week(self):
        today = datetime.now()
        self.txt_date_from.value = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        self.txt_date_to.value = today.strftime("%Y-%m-%d")
        self.refresh()
        self._safe_update()

    def _set_month(self):
        today = datetime.now()
        self.txt_date_from.value = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        self.txt_date_to.value = today.strftime("%Y-%m-%d")
        self.refresh()
        self._safe_update()

    # ── Yardımcı ──────────────────────────────────────────────────────────────

    def _safe_update(self):
        try:
            _ = self.page
            self.update()
        except RuntimeError:
            pass

    # ── Veri çek ─────────────────────────────────────────────────────────────

    def refresh(self):
        date_from = (self.txt_date_from.value or "").strip()
        date_to = (self.txt_date_to.value or "").strip()
        pay_filter = self.dd_payment_filter.value or "TUMU"
        show_returns = self.chk_returns.value

        rows = self.db.list_sales_range(date_from, date_to, pay_filter, show_returns)

        # İadeleri net hesapta negatif kabul et
        total_sum = sum(((-1.0 if int(r[8] or 0) else 1.0) * float(r[3] or 0)) for r in rows)
        cash_sum = sum(((-1.0 if int(r[8] or 0) else 1.0) * float(r[5] or 0)) for r in rows)
        card_sum = sum(((-1.0 if int(r[8] or 0) else 1.0) * float(r[6] or 0)) for r in rows)
        transfer_sum = sum(((-1.0 if int(r[8] or 0) else 1.0) * float(r[7] or 0)) for r in rows)

        self.lbl_count.value = f"{len(rows)} islem"
        self.lbl_sum.value = f"Net Toplam: {total_sum:,.2f} TL"
        self.lbl_cash.value = f"Nakit: {cash_sum:,.2f} TL"
        self.lbl_card.value = f"Kart: {card_sum:,.2f} TL"
        self.lbl_transfer.value = f"Havale: {transfer_sum:,.2f} TL"

        self.sales_table.rows = []
        for r in rows:
            sale_id, sale_time, pay_type, total, discount, cash, card, transfer, is_return = (
                r[0], r[1], r[2], float(r[3] or 0), float(r[4] or 0),
                float(r[5] or 0), float(r[6] or 0), float(r[7] or 0), int(r[8] or 0)
            )
            type_color = ft.Colors.RED_700 if is_return else ft.Colors.GREEN_700
            type_text = "IADE" if is_return else "SATIS"
            pay_color = {
                "NAKIT": ft.Colors.GREEN_700,
                "POS": ft.Colors.BLUE_700,
                "VERESIYE": ft.Colors.ORANGE_700,
                "HAVALE": ft.Colors.PURPLE_700,
            }.get(pay_type, ft.Colors.BLUE_GREY_700)

            self.sales_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(sale_id), size=11)),
                        ft.DataCell(ft.Text(sale_time or "", size=11)),
                        ft.DataCell(ft.Text(pay_type or "", size=11, color=pay_color,
                                            weight=ft.FontWeight.W_600)),
                        ft.DataCell(ft.Text(f"{discount:.2f}", size=11,
                                            color=ft.Colors.ORANGE_700 if discount > 0 else ft.Colors.BLUE_GREY_500)),
                        ft.DataCell(ft.Text(f"{total:.2f}", size=11,
                                            weight=ft.FontWeight.BOLD, color=type_color)),
                        ft.DataCell(ft.Text(type_text, size=11, color=type_color,
                                            weight=ft.FontWeight.W_600)),
                        ft.DataCell(ft.TextButton(
                            "Goruntule",
                            style=ft.ButtonStyle(padding=ft.padding.all(0)),
                            on_click=lambda _, sid=sale_id: self._show_detail(sid),
                        )),
                    ]
                )
            )
        self._safe_update()

    def _show_detail(self, sale_id: int):
        items = self.db.get_sale_items(sale_id)
        controls = [
            ft.Text(f"Satis #{sale_id}", size=14, weight=ft.FontWeight.W_600,
                    color=ft.Colors.INDIGO_700),
            ft.Divider(),
        ]
        subtotal = 0.0
        for it in items:
            name, qty, unit_price, discount, vat_rate, line_total = (
                it[0], float(it[1] or 0), float(it[2] or 0),
                float(it[3] or 0), float(it[4] or 0), float(it[5] or 0)
            )
            subtotal += line_total
            controls.append(ft.Container(
                bgcolor=ft.Colors.INDIGO_50, border_radius=8, padding=8,
                content=ft.Column(spacing=2, controls=[
                    ft.Text(name, weight=ft.FontWeight.W_600, size=12),
                    ft.Row([
                        ft.Text(f"{qty:.2f} x {unit_price:.2f} TL", size=11,
                                color=ft.Colors.BLUE_GREY_700),
                        ft.Text(f"= {line_total:.2f} TL", size=12,
                                weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_700),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(f"KDV: %{vat_rate:.0f}  |  Urun Indirim: {discount:.2f} TL",
                            size=10, color=ft.Colors.BLUE_GREY_600),
                ]),
            ))
        controls.append(ft.Divider())
        controls.append(ft.Row([
            ft.Text("GENEL TOPLAM:", weight=ft.FontWeight.BOLD),
            ft.Text(f"{subtotal:.2f} TL", weight=ft.FontWeight.BOLD,
                    color=ft.Colors.INDIGO_700, size=14),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

        self.detail_col.controls = controls
        self._safe_update()
