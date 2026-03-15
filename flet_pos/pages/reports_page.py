from datetime import datetime, timedelta
import flet as ft


def _stat_card(title: str, lbl: ft.Text, icon, color) -> ft.Container:
    return ft.Container(
        bgcolor=ft.Colors.WHITE,
        border_radius=12,
        padding=12,
        border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
        content=ft.Column(tight=True, horizontal_alignment=ft.CrossAxisAlignment.START, spacing=6, controls=[
            ft.Container(bgcolor=color, border_radius=10, padding=8,
                         content=ft.Icon(icon, color=ft.Colors.WHITE, size=22)),
            lbl,
            ft.Text(title, size=12, color=ft.Colors.BLUE_GREY_600),
        ]),
    )


def _bar_chart(data: list[tuple[str, float]], max_val: float, bar_color) -> ft.Column:
    """Basit yatay bar chart (flet native)."""
    controls = []
    for name, val in data:
        pct = (val / max_val) if max_val > 0 else 0
        bar_w = max(4.0, pct * 280)
        controls.append(ft.Row([
            ft.Container(
                ft.Text(name, size=10, overflow=ft.TextOverflow.ELLIPSIS,
                        max_lines=1, no_wrap=True),
                width=130,
            ),
            ft.Container(
                bgcolor=bar_color, border_radius=4, height=18, width=bar_w,
                content=ft.Text(f"{val:.1f}", size=9, color=ft.Colors.WHITE,
                                text_align=ft.TextAlign.RIGHT),
                padding=ft.padding.only(right=4),
                alignment=ft.Alignment(1, 0),
            ),
        ], spacing=6))
    return ft.Column(controls, spacing=3)


class ReportsPage(ft.Container):
    def __init__(self, db):
        super().__init__(expand=True)
        self.db = db

        today = datetime.now()
        fmt = "%Y-%m-%d"
        self.txt_date_from = ft.TextField(
            label="Baslangic", value=(today - timedelta(days=30)).strftime(fmt),
            width=140,
        )
        self.txt_date_to = ft.TextField(
            label="Bitis", value=today.strftime(fmt), width=140,
        )

        # Özet kartlar
        self.lbl_daily = ft.Text("0.00 TL", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900)
        self.lbl_cash = ft.Text("0.00 TL", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900)
        self.lbl_card = ft.Text("0.00 TL", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900)
        self.lbl_transfer = ft.Text("0.00 TL", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900)
        self.lbl_weekly = ft.Text("0.00 TL", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900)
        self.lbl_monthly = ft.Text("0.00 TL", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900)
        self.lbl_return = ft.Text("Iade: 0.00 TL", size=12, color=ft.Colors.RED_600)

        # En çok satan chart alanı
        self.chart_top_qty = ft.Container(
            content=ft.Text("Veri yok", color=ft.Colors.BLUE_GREY_400, italic=True),
            bgcolor=ft.Colors.WHITE, border_radius=12, padding=14,
        )

        # Kar raporu tablosu
        self.profit_table = ft.DataTable(
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            heading_row_color=ft.Colors.INDIGO_50,
            column_spacing=14,
            columns=[
                ft.DataColumn(ft.Text("Urun", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Miktar", weight=ft.FontWeight.W_600), numeric=True),
                ft.DataColumn(ft.Text("Toplam Alis", weight=ft.FontWeight.W_600), numeric=True),
                ft.DataColumn(ft.Text("Toplam Satis", weight=ft.FontWeight.W_600), numeric=True),
                ft.DataColumn(ft.Text("KAR (TL)", weight=ft.FontWeight.W_600), numeric=True),
            ],
            rows=[],
        )

        self.lbl_profit_total = ft.Text("", size=14, weight=ft.FontWeight.BOLD,
                                         color=ft.Colors.GREEN_700)

        self.content = ft.Column(
            expand=True, scroll=ft.ScrollMode.AUTO, spacing=12,
            controls=[
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                    padding=ft.padding.symmetric(horizontal=14, vertical=12),
                    content=ft.Row([
                        ft.Column([
                            ft.Text("Raporlar ve Kar Analizi", size=24, weight=ft.FontWeight.BOLD),
                            ft.Text("Satis ozeti, en cok satilan urunler ve kar/zarar gorunumu", size=12, color=ft.Colors.BLUE_GREY_600),
                        ], spacing=2, expand=True),
                        ft.ElevatedButton("Yenile", icon=ft.Icons.REFRESH, on_click=lambda _: self.refresh()),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ),

                # Tarih filtresi
                ft.Container(
                    bgcolor=ft.Colors.WHITE, border_radius=12, border=ft.border.all(1, ft.Colors.BLUE_GREY_100), padding=12,
                    content=ft.Row([
                        ft.Text("Tarih Araligi", size=13, weight=ft.FontWeight.W_600, color=ft.Colors.INDIGO_700),
                        self.txt_date_from, ft.Text("—"), self.txt_date_to,
                        ft.ElevatedButton("Hesapla", icon=ft.Icons.CALCULATE,
                                          on_click=lambda _: self.refresh()),
                        ft.OutlinedButton("Bugun", on_click=lambda _: self._set_today()),
                        ft.OutlinedButton("Bu Ay", on_click=lambda _: self._set_month()),
                    ], wrap=True, spacing=8),
                ),

                ft.Row([self.lbl_return], alignment=ft.MainAxisAlignment.END),

                ft.Text("Sabit Ozet (Bugun / 7 Gun / 30 Gun)", size=14, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_GREY_700),
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(col={"sm": 12, "md": 6, "lg": 3}, content=_stat_card("Bugunun Cirosu", self.lbl_daily, ft.Icons.TODAY, ft.Colors.INDIGO_400)),
                        ft.Container(col={"sm": 12, "md": 6, "lg": 3}, content=_stat_card("Nakit", self.lbl_cash, ft.Icons.PAYMENTS, ft.Colors.GREEN_500)),
                        ft.Container(col={"sm": 12, "md": 6, "lg": 3}, content=_stat_card("Kart (POS)", self.lbl_card, ft.Icons.CREDIT_CARD, ft.Colors.BLUE_500)),
                        ft.Container(col={"sm": 12, "md": 6, "lg": 3}, content=_stat_card("Havale", self.lbl_transfer, ft.Icons.ACCOUNT_BALANCE, ft.Colors.ORANGE_500)),
                        ft.Container(col={"sm": 12, "md": 6, "lg": 3}, content=_stat_card("Son 7 Gun", self.lbl_weekly, ft.Icons.DATE_RANGE, ft.Colors.PURPLE_400)),
                        ft.Container(col={"sm": 12, "md": 6, "lg": 3}, content=_stat_card("Son 30 Gun", self.lbl_monthly, ft.Icons.CALENDAR_MONTH, ft.Colors.TEAL_500)),
                    ],
                    spacing=8,
                    run_spacing=8,
                ),

                # En çok satan grafik
                ft.Text("En Cok Satilan Urunler (Miktar)", size=14, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_GREY_700),
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                    padding=12,
                    content=self.chart_top_qty,
                ),

                # Kar raporu
                ft.Text("Urun Bazli Kar / Zarar Raporu", size=14, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_GREY_700),
                self.lbl_profit_total,
                ft.Container(
                    content=ft.Column([self.profit_table], scroll=ft.ScrollMode.AUTO),
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                    padding=10,
                    height=340,
                ),
            ],
        )
        self.refresh()

    # ── Filtre kısayolları ────────────────────────────────────────────────────

    def _set_today(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.txt_date_from.value = today
        self.txt_date_to.value = today
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

    def _snack(self, text: str):
        try:
            self.page.snack_bar = ft.SnackBar(ft.Text(text), open=True)
            self.page.update()
        except RuntimeError:
            pass

    def _normalized_range(self) -> tuple[str, str]:
        """Geçerli tarih aralığı döndürür; hatalı girişte son 30 güne düşer."""
        raw_from = (self.txt_date_from.value or "").strip()
        raw_to = (self.txt_date_to.value or "").strip()
        today = datetime.now().date()
        fallback_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        fallback_to = today.strftime("%Y-%m-%d")
        try:
            d_from = datetime.strptime(raw_from, "%Y-%m-%d").date() if raw_from else datetime.strptime(fallback_from, "%Y-%m-%d").date()
            d_to = datetime.strptime(raw_to, "%Y-%m-%d").date() if raw_to else datetime.strptime(fallback_to, "%Y-%m-%d").date()
        except ValueError:
            self._snack("Tarih formati hatali. YYYY-AA-GG kullanin.")
            self.txt_date_from.value = fallback_from
            self.txt_date_to.value = fallback_to
            return fallback_from, fallback_to
        if d_from > d_to:
            d_from, d_to = d_to, d_from
            self._snack("Baslangic ve bitis tarihi yer degistirildi.")
        norm_from = d_from.strftime("%Y-%m-%d")
        norm_to = d_to.strftime("%Y-%m-%d")
        self.txt_date_from.value = norm_from
        self.txt_date_to.value = norm_to
        return norm_from, norm_to

    # ── Veri yenile ───────────────────────────────────────────────────────────

    def refresh(self):
        # Tarih filtresi — hem grafik hem kar raporu için kullanılır
        date_from, date_to = self._normalized_range()
        try:
            s = self.db.get_report_summary(date_from=date_from, date_to=date_to)
        except Exception as ex:
            self._snack(f"Rapor verisi alinamadi: {ex}")
            s = {
                "daily_total": 0.0,
                "daily_cash": 0.0,
                "daily_card": 0.0,
                "daily_transfer": 0.0,
                "weekly_total": 0.0,
                "monthly_total": 0.0,
                "return_total": 0.0,
                "top_products": [],
            }

        self.lbl_daily.value = f"{s['daily_total']:.2f} TL"
        self.lbl_cash.value = f"{s['daily_cash']:.2f} TL"
        self.lbl_card.value = f"{s['daily_card']:.2f} TL"
        self.lbl_transfer.value = f"{s['daily_transfer']:.2f} TL"
        self.lbl_weekly.value = f"{s['weekly_total']:.2f} TL"
        self.lbl_monthly.value = f"{s['monthly_total']:.2f} TL"
        ret = s.get("return_total", 0.0)
        self.lbl_return.value = f"Bugun Iade: {ret:.2f} TL"

        # Bar chart — aynı tarih filtresiyle en çok satılan ürünler
        tops = s.get("top_products", [])
        range_label = ""
        if date_from or date_to:
            range_label = f" ({date_from or '...'} – {date_to or '...'})"
        if tops:
            max_qty = max(float(r[1]) for r in tops) or 1
            chart = _bar_chart([(r[0], float(r[1])) for r in tops], max_qty, ft.Colors.INDIGO_400)
            self.chart_top_qty.content = ft.Column([
                ft.Text(f"Miktar{range_label}", size=10, color=ft.Colors.BLUE_GREY_500),
                chart,
            ], spacing=6)
        else:
            self.chart_top_qty.content = ft.Text("Veri yok", color=ft.Colors.BLUE_GREY_400, italic=True)

        # Kar raporu — aynı tarih filtresi
        try:
            profit_rows = self.db.get_profit_report(date_from, date_to)
        except Exception as ex:
            self._snack(f"Kar analizi alinamadi: {ex}")
            profit_rows = []

        self.profit_table.rows = []
        total_profit = 0.0
        for r in profit_rows:
            name, qty, buy, sell, profit = r[0], float(r[1]), float(r[2]), float(r[3]), float(r[4])
            total_profit += profit
            profit_color = ft.Colors.GREEN_700 if profit >= 0 else ft.Colors.RED_700
            self.profit_table.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(name, size=11)),
                ft.DataCell(ft.Text(f"{qty:.2f}", size=11)),
                ft.DataCell(ft.Text(f"{buy:.2f}", size=11, color=ft.Colors.RED_700)),
                ft.DataCell(ft.Text(f"{sell:.2f}", size=11, color=ft.Colors.BLUE_700)),
                ft.DataCell(ft.Text(f"{profit:.2f}", size=11, weight=ft.FontWeight.BOLD,
                                    color=profit_color)),
            ]))
        if not profit_rows:
            self.profit_table.rows = [
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text("Veri yok", color=ft.Colors.BLUE_GREY_400)),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                ])
            ]

        self.lbl_profit_total.value = (
            f"Toplam Kar: {total_profit:.2f} TL" if total_profit >= 0
            else f"Toplam Zarar: {total_profit:.2f} TL"
        )
        self.lbl_profit_total.color = ft.Colors.GREEN_700 if total_profit >= 0 else ft.Colors.RED_700

        self._safe_update()
