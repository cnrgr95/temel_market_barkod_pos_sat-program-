import html
import os
from datetime import datetime

import flet as ft

from flet_pos.services.barcode import ean13_svg


class BarcodePage(ft.Container):
    def __init__(self, db, base_dir: str):
        self.db = db
        self.base_dir = base_dir
        self.output_dir = os.path.join(base_dir, "barcode_labels")
        os.makedirs(self.output_dir, exist_ok=True)

        self._products_cache = []
        self._products_cache_loaded = False
        self._shelf_items: list[dict] = []
        self._last_shelf_output = ""

        self.txt_shelf_search = ft.TextField(
            label="Urun ara",
            prefix_icon=ft.Icons.SEARCH,
            width=420,
            on_change=lambda _: self._refresh_shelf_candidates(),
        )
        self.chk_show_price = ft.Checkbox(label="Fiyati goster", value=True)
        self.chk_show_barcode = ft.Checkbox(label="Barkodu goster", value=True)
        self.lbl_shelf_status = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_600)
        self.lbl_shelf_output = ft.Text("", size=11, color=ft.Colors.BLUE_GREY_600, selectable=True)
        self.shelf_candidates = ft.Column(spacing=8)
        self.shelf_selection = ft.Column(spacing=8)

        content = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=14,
            controls=[
                ft.Text("Raf Etiketleri", size=26, weight=ft.FontWeight.BOLD),
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    border_radius=14,
                    padding=16,
                    content=ft.Column(
                        spacing=14,
                        controls=[
                            ft.Text("Raf Etiketi Hazirlama", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.INDIGO_800),
                            ft.Text(
                                "Urunleri secin, adetleri belirleyin. Olustur dediginizde etiket sayfasi hazirlanir ve otomatik acilir.",
                                size=12,
                                color=ft.Colors.BLUE_GREY_500,
                            ),
                            ft.Row(
                                [
                                    self.txt_shelf_search,
                                    self.chk_show_price,
                                    self.chk_show_barcode,
                                ],
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Container(
                                bgcolor=ft.Colors.GREY_50,
                                border_radius=12,
                                padding=12,
                                content=ft.Column(
                                    [
                                        ft.Text("Urun Sonuclari", size=15, weight=ft.FontWeight.W_700),
                                        self.shelf_candidates,
                                    ],
                                    spacing=10,
                                ),
                            ),
                            ft.Container(
                                bgcolor=ft.Colors.GREY_50,
                                border_radius=12,
                                padding=12,
                                content=ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                ft.Text("Secili Etiketler", size=15, weight=ft.FontWeight.W_700),
                                                ft.TextButton("Listeyi Temizle", on_click=self._clear_shelf_items),
                                            ],
                                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                        ),
                                        self.shelf_selection,
                                    ],
                                    spacing=10,
                                ),
                            ),
                            ft.Row(
                                [
                                    ft.ElevatedButton(
                                        "Raf Etiketi Olustur",
                                        icon=ft.Icons.LABEL,
                                        style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
                                        on_click=self._generate_shelf_labels,
                                    ),
                                    ft.OutlinedButton(
                                        "Son Dosyayi Ac",
                                        icon=ft.Icons.OPEN_IN_NEW,
                                        on_click=lambda _: self._open_file(self._last_shelf_output),
                                    ),
                                    ft.OutlinedButton(
                                        "Windows Yazdir",
                                        icon=ft.Icons.PRINT,
                                        on_click=lambda _: self._print_file(self._last_shelf_output),
                                    ),
                                ],
                                wrap=True,
                                spacing=10,
                            ),
                            self.lbl_shelf_status,
                            self.lbl_shelf_output,
                        ],
                    ),
                ),
            ],
        )

        super().__init__(expand=True, content=content)

    def _safe_update(self):
        try:
            if self.page is None:
                return
            self.update()
        except Exception:
            pass

    def _snack(self, text: str):
        try:
            self.page.snack_bar = ft.SnackBar(ft.Text(text), open=True)
            self.page.update()
        except RuntimeError:
            pass

    def _to_int(self, value: str, default: int = 0) -> int:
        try:
            return int(float((value or "").replace(",", ".")))
        except ValueError:
            return default

    def _load_products(self, force_reload: bool = False):
        if force_reload or not self._products_cache_loaded:
            self._products_cache = list(self.db.list_products())
            self._products_cache_loaded = True
        return self._products_cache

    def refresh(self):
        self._load_products(force_reload=True)
        self._refresh_shelf_candidates()
        self._refresh_shelf_selection()

    def _refresh_shelf_candidates(self):
        query = (self.txt_shelf_search.value or "").strip().lower()
        selected_ids = {item["product_id"] for item in self._shelf_items}
        matches = []
        for row in self._load_products():
            name = (row[1] or "").lower()
            barcode = (row[2] or "").lower()
            if query and query not in name and query not in barcode:
                continue
            if row[0] in selected_ids:
                continue
            matches.append(row)
        matches = matches[:40]

        if not matches:
            self.shelf_candidates.controls = [
                ft.Container(
                    padding=ft.padding.symmetric(vertical=6),
                    content=ft.Text("Urun bulunamadi", color=ft.Colors.BLUE_GREY_400),
                )
            ]
        else:
            self.shelf_candidates.controls = [self._candidate_row(row) for row in matches]
        self._safe_update()

    def _candidate_row(self, row):
        return ft.Container(
            bgcolor=ft.Colors.WHITE,
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(row[1] or "", size=14, weight=ft.FontWeight.W_700),
                            ft.Text(f"Barkod: {row[2] or '-'}", size=11, color=ft.Colors.BLUE_GREY_500),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Text(f"{float(row[4] or 0):.2f} TL", size=14, color=ft.Colors.GREEN_700, weight=ft.FontWeight.W_600),
                    ft.OutlinedButton("Ekle", icon=ft.Icons.ADD, on_click=lambda _, r=row: self._add_shelf_product(r)),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _add_shelf_product(self, row):
        existing = next((item for item in self._shelf_items if item["product_id"] == row[0]), None)
        if existing:
            existing["copies"] += 1
        else:
            self._shelf_items.append(
                {
                    "product_id": int(row[0]),
                    "name": row[1] or "",
                    "barcode": row[2] or "",
                    "price": float(row[4] or 0),
                    "copies": 1,
                }
            )
        self._refresh_shelf_candidates()
        self._refresh_shelf_selection()

    def _set_shelf_copies(self, product_id: int, value: str):
        copies = max(1, min(self._to_int(value, 1), 200))
        for item in self._shelf_items:
            if item["product_id"] == product_id:
                item["copies"] = copies
                break
        self._refresh_shelf_selection()

    def _remove_shelf_product(self, product_id: int):
        self._shelf_items = [item for item in self._shelf_items if item["product_id"] != product_id]
        self._refresh_shelf_candidates()
        self._refresh_shelf_selection()

    def _clear_shelf_items(self, _e):
        self._shelf_items = []
        self.lbl_shelf_status.value = ""
        self.lbl_shelf_output.value = ""
        self._refresh_shelf_candidates()
        self._refresh_shelf_selection()

    def _refresh_shelf_selection(self):
        if not self._shelf_items:
            self.shelf_selection.controls = [
                ft.Container(
                    padding=ft.padding.symmetric(vertical=6),
                    content=ft.Text("Raf etiketi icin henuz urun secilmedi.", color=ft.Colors.BLUE_GREY_400),
                )
            ]
            self._safe_update()
            return

        self.shelf_selection.controls = [
            ft.Container(
                bgcolor=ft.Colors.WHITE,
                border_radius=10,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(item["name"], size=14, weight=ft.FontWeight.W_700),
                                ft.Text(f"Barkod: {item['barcode'] or '-'}", size=11, color=ft.Colors.BLUE_GREY_500),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ft.Text(f"{item['price']:.2f} TL", size=14, color=ft.Colors.GREEN_700, weight=ft.FontWeight.W_600),
                        ft.TextField(
                            label="Adet",
                            value=str(item["copies"]),
                            width=100,
                            on_change=lambda e, pid=item["product_id"]: self._set_shelf_copies(pid, e.control.value),
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE,
                            icon_color=ft.Colors.RED_600,
                            on_click=lambda _, pid=item["product_id"]: self._remove_shelf_product(pid),
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
            for item in self._shelf_items
        ]
        self._safe_update()

    def _generate_shelf_labels(self, _e):
        if not self._shelf_items:
            self._snack("Once raf etiketi icin urun secin")
            return

        labels = []
        for item in self._shelf_items:
            copies = max(1, int(item["copies"]))
            for _ in range(copies):
                labels.append(
                    {
                        "barcode": item["barcode"],
                        "name": item["name"],
                        "price_text": f"{item['price']:.2f} TL" if self.chk_show_price.value else "",
                    }
                )

        path = self._write_shelf_label_file(labels, show_barcode=bool(self.chk_show_barcode.value))
        self._last_shelf_output = path
        self.lbl_shelf_status.value = f"{len(labels)} raf etiketi hazirlandi"
        self.lbl_shelf_output.value = path
        self._safe_update()
        self._open_file(path)

    def _write_shelf_label_file(self, labels: list[dict], show_barcode: bool = True) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.output_dir, f"raf_etiketleri_{stamp}.html")
        cards = []
        for item in labels:
            svg = ""
            if show_barcode and item["barcode"]:
                try:
                    svg = ean13_svg(item["barcode"], module_width=2, bar_height=62)
                except Exception:
                    svg = ""
            barcode_block = ""
            if show_barcode:
                if svg:
                    barcode_block = f'<div class="barcode">{svg}</div>'
                elif item["barcode"]:
                    barcode_block = f'<div class="plain-barcode">{html.escape(item["barcode"])}</div>'
            price_block = f'<div class="price">{html.escape(item["price_text"])}</div>' if item.get("price_text") else ""
            cards.append(
                "<div class=\"label\">"
                f"<div class=\"name\">{html.escape(item['name'])}</div>"
                f"{price_block}"
                f"{barcode_block}"
                "</div>"
            )

        document = f"""<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <title>Raf Etiketleri</title>
  <style>
    @page {{
      size: A4 portrait;
      margin: 10mm;
    }}
    body {{
      font-family: Arial, sans-serif;
      margin: 0;
      color: #111827;
      background: #f8fafc;
    }}
    .header {{
      padding: 12px 0 18px;
    }}
    .title {{
      font-size: 22px;
      font-weight: 700;
    }}
    .meta {{
      font-size: 12px;
      color: #475569;
      margin-top: 4px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, 60mm);
      grid-auto-rows: 50mm;
      gap: 4mm;
      align-items: start;
    }}
    .label {{
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      padding: 3mm;
      width: 60mm;
      height: 50mm;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-sizing: border-box;
      overflow: hidden;
      break-inside: avoid;
      page-break-inside: avoid;
    }}
    .name {{
      font-size: 15px;
      font-weight: 700;
      line-height: 1.25;
      min-height: 9mm;
      max-height: 19mm;
      overflow: hidden;
    }}
    .price {{
      font-size: 24px;
      font-weight: 800;
      color: #047857;
      margin: 1mm 0 2mm;
      line-height: 1;
    }}
    .barcode {{
      margin-top: 1mm;
      text-align: center;
      line-height: 0;
    }}
    .barcode svg {{
      width: 100%;
      max-width: 52mm;
      height: 24mm;
      display: block;
      margin: 0 auto;
    }}
    .plain-barcode {{
      margin-top: 2mm;
      padding: 3mm 2mm;
      border: 1px dashed #94a3b8;
      border-radius: 6px;
      text-align: center;
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 1px;
    }}
    @media print {{
      body {{
        background: #ffffff;
      }}
      .header {{
        display: none;
      }}
      .grid {{
        gap: 3mm;
      }}
      .label {{
        box-shadow: none;
      }}
    }}
  </style>
</head>
<body>
  <div class="header">
    <div class="title">Raf Etiketleri</div>
    <div class="meta">Olusturma: {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}</div>
  </div>
  <div class="grid">
    {"".join(cards)}
  </div>
</body>
</html>
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(document)
        return path

    def _open_file(self, path: str):
        if not path or not os.path.exists(path):
            self._snack("Acilacak dosya bulunamadi")
            return
        try:
            os.startfile(path)
        except Exception as ex:
            self._snack(f"Dosya acilamadi: {ex}")

    def _print_file(self, path: str):
        if not path or not os.path.exists(path):
            self._snack("Yazdirilacak dosya bulunamadi")
            return
        try:
            os.startfile(path, "print")
            self._snack("Yazdirma komutu gonderildi")
        except Exception as ex:
            self._snack(f"Yazdirma baslatilamadi: {ex}")
