import os
import sqlite3
import shutil
from datetime import datetime
import flet as ft


class BackupPage(ft.Container):
    def __init__(self, base_dir: str, backup_manager=None, db=None):
        super().__init__(expand=True, padding=10)
        self.base_dir = base_dir
        self.db_path = os.path.join(base_dir, "market.db")
        self.backup_dir = os.path.join(base_dir, "backups")
        self.backup_manager = backup_manager
        self.db = db
        os.makedirs(self.backup_dir, exist_ok=True)

        self.lbl_db_size = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_500)
        self.lbl_auto_backup = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_600)
        self.lbl_drive_status = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_600)
        self.txt_drive_dir = ft.TextField(label="Google Drive klasoru", expand=True)

        self.table = ft.DataTable(
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            border_radius=8,
            heading_row_color=ft.Colors.INDIGO_50,
            heading_row_height=38,
            data_row_min_height=44,
            columns=[
                ft.DataColumn(ft.Text("Dosya Adı", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Tarih", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Boyut", weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("İşlemler", weight=ft.FontWeight.W_600)),
            ],
            rows=[],
        )

        self.content = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=12,
            controls=[
                ft.Row([
                    ft.Icon(ft.Icons.SECURITY, color=ft.Colors.INDIGO_700, size=26),
                    ft.Text("Veri Güvenliği & Yedekleme", size=22,
                            weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_800),
                ], spacing=8),

                # Bilgi kartı
                ft.Card(
                    elevation=2,
                    content=ft.Container(
                        padding=ft.padding.all(14),
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.STORAGE, color=ft.Colors.BLUE_600, size=20),
                                ft.Text("Veritabanı Durumu", size=14,
                                        weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_800),
                            ], spacing=6),
                            ft.Row([
                                ft.Text("Konum:", size=12, color=ft.Colors.BLUE_GREY_600),
                                ft.Text(self.db_path, size=11, color=ft.Colors.BLUE_GREY_500,
                                        expand=True, overflow=ft.TextOverflow.ELLIPSIS),
                            ]),
                            self.lbl_db_size,
                            self.lbl_auto_backup,
                            self.lbl_drive_status,
                        ], spacing=6),
                    ),
                ),

                # İşlem butonları
                ft.Card(
                    elevation=2,
                    content=ft.Container(
                        padding=ft.padding.all(14),
                        content=ft.Column([
                            ft.Row([
                                ft.ElevatedButton(
                                    "Yedek Al",
                                    icon=ft.Icons.BACKUP,
                                    style=ft.ButtonStyle(
                                        bgcolor=ft.Colors.INDIGO_600,
                                        color=ft.Colors.WHITE,
                                    ),
                                    on_click=self._backup_now,
                                ),
                                ft.Text(
                                    "Veritabanını backups/ klasörüne kopyalar.",
                                    size=12, color=ft.Colors.BLUE_GREY_500,
                                ),
                            ], spacing=10),
                            ft.Row(
                                [
                                    self.txt_drive_dir,
                                    ft.OutlinedButton(
                                        "Drive Yolunu Kaydet",
                                        icon=ft.Icons.CLOUD_DONE,
                                        on_click=self._save_drive_dir,
                                    ),
                                    ft.OutlinedButton(
                                        "Otomatik Bul",
                                        icon=ft.Icons.SEARCH,
                                        on_click=self._detect_drive_dir,
                                    ),
                                ],
                                spacing=8,
                            ),
                        ], spacing=8),
                    ),
                ),

                # Yedek listesi
                ft.Card(
                    elevation=2,
                    content=ft.Container(
                        padding=ft.padding.all(14),
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.FOLDER_COPY,
                                        color=ft.Colors.ORANGE_600, size=18),
                                ft.Text("Yedek Dosyaları", size=14,
                                        weight=ft.FontWeight.W_600,
                                        color=ft.Colors.ORANGE_800),
                            ], spacing=6),
                            ft.Container(
                                content=self.table,
                                bgcolor=ft.Colors.WHITE,
                            ),
                        ], spacing=10),
                    ),
                ),
            ],
        )

        self.refresh()

    # ── Yardımcı ──────────────────────────────────────────────────────────

    def _safe_update(self):
        try:
            self.update()
        except RuntimeError:
            pass

    def _snack(self, text: str, color=ft.Colors.INDIGO_700):
        try:
            self.page.snack_bar = ft.SnackBar(
                ft.Text(text, color=ft.Colors.WHITE), bgcolor=color, open=True,
            )
            self.page.update()
        except RuntimeError:
            pass

    def _open_dialog(self, dlg):
        try:
            if dlg not in self.page.overlay:
                self.page.overlay.append(dlg)
            dlg.open = True
            self.page.update()
        except RuntimeError:
            pass

    def _save_drive_dir(self, _e):
        path = (self.txt_drive_dir.value or "").strip().strip('"')
        if path and not os.path.isdir(path):
            self._snack("Google Drive klasoru bulunamadi", ft.Colors.RED_600)
            return
        if self.backup_manager:
            self.backup_manager.google_drive_dir = path
        if self.db:
            self.db.set_setting("google_drive_backup_dir", path)
        self.refresh()
        self._snack("Google Drive yedek yolu kaydedildi", ft.Colors.GREEN_700)

    def _detect_drive_dir(self, _e):
        if not self.backup_manager:
            return
        path = self.backup_manager.detect_google_drive_dir()
        self.backup_manager.google_drive_dir = path
        self.txt_drive_dir.value = path
        if self.db:
            self.db.set_setting("google_drive_backup_dir", path)
        self.refresh()
        if path:
            self._snack("Google Drive klasoru bulundu", ft.Colors.GREEN_700)
        else:
            self._snack("Google Drive klasoru otomatik bulunamadi", ft.Colors.ORANGE_700)

    def _fmt_size(self, path: str) -> str:
        try:
            b = os.path.getsize(path)
            if b < 1024:
                return f"{b} B"
            elif b < 1024 * 1024:
                return f"{b / 1024:.1f} KB"
            return f"{b / (1024 * 1024):.2f} MB"
        except Exception:
            return "—"

    # ── Yedek al ──────────────────────────────────────────────────────────

    def _sqlite_backup_copy(self, src_path: str, dst_path: str):
        """SQLite dosyasını güvenli yedekleme API'si ile kopyala."""
        src = sqlite3.connect(src_path)
        dst = sqlite3.connect(dst_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

    def _backup_now(self, _e):
        try:
            if self.backup_manager:
                result = self.backup_manager.backup_now(prefix="manual")
                name = os.path.basename(result.local_path)
                self.refresh()
                if result.error:
                    self._snack(f"Yerel yedek alindi, {result.error}", ft.Colors.ORANGE_700)
                    return
                extra = " + Google Drive" if result.drive_path else ""
                self._snack(f"Yedek alindi{extra}: {name}", ft.Colors.GREEN_700)
                return
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target = os.path.join(self.backup_dir, f"market_{stamp}.db")
            self._sqlite_backup_copy(self.db_path, target)
            self.refresh()
            self._snack(f"✓ Yedek alındı: market_{stamp}.db", ft.Colors.GREEN_700)
        except Exception as ex:
            self._snack(f"Yedekleme hatası: {ex}", ft.Colors.RED_600)

    # ── Geri yükle ────────────────────────────────────────────────────────

    def _confirm_restore(self, backup_path: str, backup_name: str):
        """Seçilen yedek dosyasını market.db üzerine kopyala (onay sonrası)."""

        def _do_restore(_e):
            dlg.open = False
            self.page.update()
            try:
                # Önce mevcut DB'yi otomatik yedekle
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                auto_bak = os.path.join(self.backup_dir, f"market_onceki_{stamp}.db")
                self._sqlite_backup_copy(self.db_path, auto_bak)
                # Yedeği geri yükle
                self._sqlite_backup_copy(backup_path, self.db_path)
                self.refresh()
                self._snack(
                    "✓ Geri yükleme tamamlandı. Programı yeniden başlatın.",
                    ft.Colors.GREEN_700,
                )
            except Exception as ex:
                self._snack(f"Geri yükleme hatası: {ex}", ft.Colors.RED_600)

        def _cancel(_e):
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER, color=ft.Colors.ORANGE_700),
                ft.Text("Geri Yükleme Onayı", color=ft.Colors.ORANGE_800),
            ], spacing=8),
            content=ft.Container(
                width=420,
                content=ft.Column([
                    ft.Text(f"Seçilen yedek:", size=13),
                    ft.Text(backup_name, weight=ft.FontWeight.BOLD, size=13,
                            color=ft.Colors.INDIGO_700),
                    ft.Divider(),
                    ft.Text(
                        "⚠ Mevcut veritabanı bu yedekle değiştirilecek.\n"
                        "İşlem öncesinde otomatik yedek alınacaktır.\n"
                        "Devam etmek istiyor musunuz?",
                        size=13, color=ft.Colors.ORANGE_800,
                    ),
                ], spacing=8, tight=True),
            ),
            actions=[
                ft.TextButton("İptal", on_click=_cancel),
                ft.ElevatedButton(
                    "Geri Yükle",
                    icon=ft.Icons.RESTORE,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.ORANGE_700, color=ft.Colors.WHITE,
                    ),
                    on_click=_do_restore,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._open_dialog(dlg)

    def _confirm_delete_backup(self, path: str, name: str):
        def _do(_e):
            dlg.open = False
            self.page.update()
            try:
                os.remove(path)
                self.refresh()
                self._snack(f"'{name}' silindi")
            except Exception as ex:
                self._snack(f"Silinemedi: {ex}", ft.Colors.RED_600)

        def _cancel(_e):
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Yedek Sil"),
            content=ft.Text(f"'{name}' yedek dosyası silinsin mi?"),
            actions=[
                ft.TextButton("İptal", on_click=_cancel),
                ft.ElevatedButton(
                    "Sil",
                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED_600, color=ft.Colors.WHITE),
                    on_click=_do,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._open_dialog(dlg)

    # ── Listeyi yenile ────────────────────────────────────────────────────

    def refresh(self):
        # DB boyutu
        if os.path.exists(self.db_path):
            self.lbl_db_size.value = f"Boyut: {self._fmt_size(self.db_path)}"
        else:
            self.lbl_db_size.value = "Veritabanı bulunamadı!"

        # Yedek dosyaları
        if self.backup_manager:
            minutes = int(self.backup_manager.interval_seconds / 60)
            self.lbl_auto_backup.value = f"Otomatik yedekleme: {minutes} dakikada bir aktif"
            self.txt_drive_dir.value = self.backup_manager.google_drive_dir or ""
            drive_dir = self.backup_manager.google_backup_dir()
            if drive_dir:
                self.lbl_drive_status.value = f"Google Drive: {drive_dir}"
                self.lbl_drive_status.color = ft.Colors.GREEN_700
            else:
                self.lbl_drive_status.value = "Google Drive klasoru bulunamadi. Yerel yedekleme aktif."
                self.lbl_drive_status.color = ft.Colors.ORANGE_700
        else:
            self.lbl_auto_backup.value = "Otomatik yedekleme bu oturumda bagli degil"
            self.lbl_drive_status.value = ""

        files: list[tuple[str, str, str, str]] = []
        if os.path.isdir(self.backup_dir):
            for f in os.listdir(self.backup_dir):
                p = os.path.join(self.backup_dir, f)
                if os.path.isfile(p) and f.endswith(".db"):
                    mtime = datetime.fromtimestamp(
                        os.path.getmtime(p)
                    ).strftime("%Y-%m-%d %H:%M")
                    files.append((f, mtime, self._fmt_size(p), p))
        files.sort(key=lambda x: x[1], reverse=True)

        def _make_row(name, date, size, path):
            return ft.DataRow(cells=[
                ft.DataCell(ft.Text(name, size=12)),
                ft.DataCell(ft.Text(date, size=12)),
                ft.DataCell(ft.Text(size, size=12)),
                ft.DataCell(ft.Row([
                    ft.ElevatedButton(
                        "Geri Yükle",
                        icon=ft.Icons.RESTORE,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.ORANGE_600,
                            color=ft.Colors.WHITE,
                            padding=ft.padding.symmetric(horizontal=8, vertical=2),
                        ),
                        height=34,
                        on_click=lambda _, p=path, n=name: self._confirm_restore(p, n),
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE, icon_color=ft.Colors.RED_400,
                        tooltip="Sil", icon_size=18,
                        on_click=lambda _, p=path, n=name: self._confirm_delete_backup(p, n),
                    ),
                ], spacing=4)),
            ])

        self.table.rows = [_make_row(*f) for f in files]

        if not files:
            self.table.rows = [ft.DataRow(cells=[
                ft.DataCell(ft.Text("Henüz yedek yok", color=ft.Colors.BLUE_GREY_400,
                                    italic=True)),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
            ])]

        self._safe_update()
