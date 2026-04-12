import os
import sqlite3
import threading
import zipfile
from datetime import datetime

import flet as ft


class BackupPage(ft.Container):
    def __init__(self, base_dir: str, backup_manager=None, db=None):
        self.base_dir = base_dir
        self.db_path = os.path.join(base_dir, "market.db")
        self.backup_dir = os.path.join(base_dir, "backups")
        self.backup_manager = backup_manager
        self.db = db
        self._stop_live = threading.Event()
        os.makedirs(self.backup_dir, exist_ok=True)

        self.lbl_db_size = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_600)
        self.lbl_auto_backup = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_600)
        self.lbl_target_status = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_600)
        self.lbl_drive_status = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_600)
        self.lbl_countdown = ft.Text("", size=20, weight=ft.FontWeight.W_700, color=ft.Colors.INDIGO_700)
        self.lbl_last_result = ft.Text("", size=12, color=ft.Colors.BLUE_GREY_600)

        self.dd_target_mode = ft.Dropdown(
            label="Yedek hedefi",
            width=220,
            options=[
                ft.dropdown.Option("LOCAL", "Sadece Local"),
                ft.dropdown.Option("DRIVE", "Sadece Google Drive"),
                ft.dropdown.Option("BOTH", "Local + Google Drive"),
            ],
            value="BOTH",
        )
        self.txt_drive_dir = ft.TextField(label="Google Drive klasoru", expand=True)
        self.txt_local_dir = ft.TextField(
            label="Yerel yedek klasörü (boş = varsayılan)", expand=True, read_only=True
        )
        self.txt_interval_minutes = ft.TextField(label="Otomatik yedek dakika", value="120", width=180)

        self.files_list = ft.Column(spacing=8)
        self.logs_list = ft.Column(spacing=8)

        content = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=12,
            controls=[
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Veri Güvenliği ve Yedekleme", size=24, weight=ft.FontWeight.W_700),
                                ft.Text(
                                    "Yedek hedefini seçin, bir sonraki otomatik yedeğe kalan süreyi izleyin.",
                                    size=12,
                                    color=ft.Colors.BLUE_GREY_600,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ft.Row(
                            [
                                ft.ElevatedButton(
                                    "Şimdi Yedek Al",
                                    icon=ft.Icons.BACKUP,
                                    style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_600, color=ft.Colors.WHITE),
                                    on_click=self._backup_now,
                                ),
                                ft.OutlinedButton(
                                    "ZIP Yedek Al",
                                    icon=ft.Icons.FOLDER_ZIP,
                                    on_click=self._backup_zip,
                                ),
                            ],
                            spacing=8,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self._summary_card(),
                self._settings_card(),
                ft.Row(
                    [
                        ft.Container(expand=True, content=self._files_card()),
                        ft.Container(expand=True, content=self._logs_card()),
                    ],
                    wrap=True,
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
        )
        super().__init__(expand=True, padding=12, content=content)

        self._start_live_refresh()

    def _summary_card(self):
        return ft.Container(
            bgcolor=ft.Colors.WHITE,
            border_radius=12,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            padding=14,
            content=ft.Row(
                [
                    ft.Container(
                        width=240,
                        bgcolor=ft.Colors.INDIGO_50,
                        border_radius=12,
                        padding=ft.padding.all(14),
                        content=ft.Column(
                            [
                                ft.Text("Bir Sonraki Otomatik Yedek", size=12, color=ft.Colors.INDIGO_700),
                                self.lbl_countdown,
                            ],
                            spacing=6,
                        ),
                    ),
                    ft.Column(
                        [
                            self.lbl_db_size,
                            self.lbl_auto_backup,
                            self.lbl_target_status,
                            self.lbl_drive_status,
                            self.lbl_last_result,
                        ],
                        spacing=6,
                        expand=True,
                    ),
                ],
                wrap=True,
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        )

    def _settings_card(self):
        return ft.Container(
            bgcolor=ft.Colors.WHITE,
            border_radius=12,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            padding=14,
            content=ft.Column(
                [
                    ft.Text("Ayarlar", size=16, weight=ft.FontWeight.W_700, color=ft.Colors.INDIGO_800),
                    ft.Row(
                        [
                            self.dd_target_mode,
                            self.txt_interval_minutes,
                            ft.ElevatedButton(
                                "Ayarları Kaydet",
                                icon=ft.Icons.SAVE,
                                style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
                                on_click=self._save_settings,
                            ),
                        ],
                        wrap=True,
                        spacing=10,
                    ),
                    ft.Row(
                        [
                            self.txt_local_dir,
                            ft.OutlinedButton(
                                "Klasör Seç",
                                icon=ft.Icons.FOLDER_OPEN,
                                on_click=self._pick_local_dir,
                            ),
                            ft.OutlinedButton(
                                "Varsayılana Sıfırla",
                                icon=ft.Icons.RESTORE,
                                on_click=self._reset_local_dir,
                            ),
                        ],
                        wrap=True,
                        spacing=10,
                    ),
                    ft.Row(
                        [
                            self.txt_drive_dir,
                            ft.OutlinedButton("Drive Yolunu Kaydet", icon=ft.Icons.CLOUD_DONE, on_click=self._save_drive_dir),
                            ft.OutlinedButton("Otomatik Bul", icon=ft.Icons.SEARCH, on_click=self._detect_drive_dir),
                        ],
                        wrap=True,
                        spacing=10,
                    ),
                ],
                spacing=10,
            ),
        )

    def _files_card(self):
        return ft.Container(
            bgcolor=ft.Colors.WHITE,
            border_radius=12,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            padding=14,
            content=ft.Column(
                [
                    ft.Text("Yedek Dosyalari", size=16, weight=ft.FontWeight.W_700, color=ft.Colors.ORANGE_800),
                    self.files_list,
                ],
                spacing=10,
            ),
        )

    def _logs_card(self):
        return ft.Container(
            bgcolor=ft.Colors.WHITE,
            border_radius=12,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            padding=14,
            content=ft.Column(
                [
                    ft.Text("Yedekleme Kayitlari", size=16, weight=ft.FontWeight.W_700, color=ft.Colors.GREEN_800),
                    self.logs_list,
                ],
                spacing=10,
            ),
        )

    def _start_live_refresh(self):
        def _worker():
            while not self._stop_live.wait(1.0):
                try:
                    self.refresh()
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()

    def _safe_update(self):
        if self.page is None:
            return
        try:
            self.page.update()
        except Exception:
            pass

    def _snack(self, text: str, color=ft.Colors.INDIGO_700):
        try:
            self.page.snack_bar = ft.SnackBar(ft.Text(text, color=ft.Colors.WHITE), bgcolor=color, open=True)
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

    def _close_dialog(self, dlg):
        try:
            dlg.open = False
            self.page.update()
        except RuntimeError:
            pass

    def _save_settings(self, _e):
        try:
            minutes = int(float((self.txt_interval_minutes.value or "120").replace(",", ".")))
        except ValueError:
            self._snack("Gecerli dakika giriniz", ft.Colors.RED_600)
            return
        if minutes < 5:
            minutes = 5
            self.txt_interval_minutes.value = "5"

        target = self.dd_target_mode.value or "BOTH"
        if self.backup_manager:
            self.backup_manager.set_interval_minutes(minutes)
            self.backup_manager.set_target_mode(target)
        if self.db:
            self.db.set_setting("backup_interval_minutes", str(minutes))
            self.db.set_setting("backup_target_mode", target)
        self.refresh()
        self._snack("Yedekleme ayarlari kaydedildi", ft.Colors.GREEN_700)

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
        self._snack("Google Drive yolu kaydedildi", ft.Colors.GREEN_700)

    def _pick_local_dir(self, _e):
        """tkinter ile yerel yedek klasörü seç (arka planda çalışır)."""
        def _pick():
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                chosen = filedialog.askdirectory(title="Yedek Klasörü Seç")
                root.destroy()
                if chosen:
                    self.backup_dir = chosen
                    self.txt_local_dir.value = chosen
                    os.makedirs(chosen, exist_ok=True)
                    if self.db:
                        self.db.set_setting("local_backup_dir", chosen)
                    self.refresh()
                    self._snack(f"Yerel yedek klasörü: {chosen}", ft.Colors.GREEN_700)
            except Exception as ex:
                self._snack(f"Klasör seçilemedi: {ex}", ft.Colors.RED_600)

        threading.Thread(target=_pick, daemon=True).start()

    def _reset_local_dir(self, _e):
        self.backup_dir = os.path.join(self.base_dir, "backups")
        self.txt_local_dir.value = ""
        os.makedirs(self.backup_dir, exist_ok=True)
        if self.db:
            self.db.set_setting("local_backup_dir", "")
        self.refresh()
        self._snack("Varsayılan klasöre döndürüldü", ft.Colors.GREEN_700)

    def _backup_zip(self, _e):
        """Veritabanını ZIP olarak dışa aktarır."""
        def _do_zip():
            try:
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                zip_path = os.path.join(self.backup_dir, f"market_zip_{stamp}.zip")
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.write(self.db_path, arcname="market.db")
                self.refresh()
                self._snack(f"ZIP yedek alındı: market_zip_{stamp}.zip", ft.Colors.GREEN_700)
            except Exception as ex:
                self._snack(f"ZIP yedekleme hatası: {ex}", ft.Colors.RED_600)

        threading.Thread(target=_do_zip, daemon=True).start()

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
            self._snack("Google Drive klasoru bulunamadi", ft.Colors.ORANGE_700)

    def _fmt_size(self, path: str) -> str:
        try:
            size = os.path.getsize(path)
        except OSError:
            return "-"
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.2f} MB"

    def _sqlite_backup_copy(self, src_path: str, dst_path: str):
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
                result = self.backup_manager.backup_now(prefix="manual", target_mode=self.dd_target_mode.value or None)
                target_text = {
                    "LOCAL": "local",
                    "DRIVE": "Google Drive",
                    "BOTH": "local + Google Drive",
                }.get(result.target_mode, result.target_mode)
                self.refresh()
                self._snack(f"Yedek alindi ({target_text})", ft.Colors.GREEN_700)
                return
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target = os.path.join(self.backup_dir, f"market_manual_{stamp}.db")
            self._sqlite_backup_copy(self.db_path, target)
            self.refresh()
            self._snack("Yerel yedek alindi", ft.Colors.GREEN_700)
        except Exception as ex:
            self.refresh()
            self._snack(f"Yedekleme hatasi: {ex}", ft.Colors.RED_600)

    def _confirm_restore(self, backup_path: str, backup_name: str):
        def _do_restore(_e):
            self._close_dialog(dlg)
            try:
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                auto_backup = os.path.join(self.backup_dir, f"market_before_restore_{stamp}.db")
                self._sqlite_backup_copy(self.db_path, auto_backup)
                self._sqlite_backup_copy(backup_path, self.db_path)
                self.refresh()
                self._snack("Geri yukleme tamamlandi. Uygulamayi yeniden baslatin.", ft.Colors.GREEN_700)
            except Exception as ex:
                self._snack(f"Geri yukleme hatasi: {ex}", ft.Colors.RED_600)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Yedegi Geri Yukle"),
            content=ft.Text(f'"{backup_name}" dosyasi mevcut veritabani uzerine yuklensin mi?'),
            actions=[
                ft.TextButton("Vazgec", on_click=lambda _: self._close_dialog(dlg)),
                ft.ElevatedButton(
                    "Geri Yukle",
                    icon=ft.Icons.RESTORE,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_700, color=ft.Colors.WHITE),
                    on_click=_do_restore,
                ),
            ],
        )
        self._open_dialog(dlg)

    def _confirm_delete_backup(self, path: str, name: str):
        def _do_delete(_e):
            self._close_dialog(dlg)
            try:
                os.remove(path)
                self.refresh()
                self._snack(f"{name} silindi")
            except Exception as ex:
                self._snack(f"Silinemedi: {ex}", ft.Colors.RED_600)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Yedek Sil"),
            content=ft.Text(f'"{name}" dosyasi silinsin mi?'),
            actions=[
                ft.TextButton("Vazgec", on_click=lambda _: self._close_dialog(dlg)),
                ft.ElevatedButton(
                    "Sil",
                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED_600, color=ft.Colors.WHITE),
                    on_click=_do_delete,
                ),
            ],
        )
        self._open_dialog(dlg)

    def _build_file_rows(self):
        files = []
        if os.path.isdir(self.backup_dir):
            for name in os.listdir(self.backup_dir):
                path = os.path.join(self.backup_dir, name)
                if os.path.isfile(path) and name.endswith(".db"):
                    modified = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
                    files.append((name, modified, self._fmt_size(path), path))
        files.sort(key=lambda item: item[1], reverse=True)

        if not files:
            self.files_list.controls = [
                ft.Container(
                    padding=ft.padding.symmetric(vertical=12),
                    content=ft.Text("Henuz yerel yedek dosyasi yok", color=ft.Colors.BLUE_GREY_400),
                )
            ]
            return

        rows = []
        for name, modified, size_text, path in files:
            rows.append(
                ft.Container(
                    bgcolor=ft.Colors.GREY_50,
                    border_radius=10,
                    border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                    padding=ft.padding.all(10),
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(name, weight=ft.FontWeight.W_600, expand=True),
                                    ft.Text(size_text, size=11, color=ft.Colors.BLUE_GREY_500),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Text(modified, size=11, color=ft.Colors.BLUE_GREY_500),
                            ft.Row(
                                [
                                    ft.TextButton("Geri Yukle", icon=ft.Icons.RESTORE, on_click=lambda _, p=path, n=name: self._confirm_restore(p, n)),
                                    ft.TextButton("Sil", icon=ft.Icons.DELETE, style=ft.ButtonStyle(color=ft.Colors.RED_600), on_click=lambda _, p=path, n=name: self._confirm_delete_backup(p, n)),
                                ],
                                spacing=4,
                            ),
                        ],
                        spacing=6,
                    ),
                )
            )
        self.files_list.controls = rows

    def _build_log_rows(self):
        logs = self.backup_manager.list_logs(40) if self.backup_manager else []
        if not logs:
            self.logs_list.controls = [
                ft.Container(
                    padding=ft.padding.symmetric(vertical=12),
                    content=ft.Text("Henuz yedekleme kaydi yok", color=ft.Colors.BLUE_GREY_400),
                )
            ]
            return

        rows = []
        for stamp, status, kind, local_path, drive_path, message in logs:
            color = {
                "SUCCESS": ft.Colors.GREEN_700,
                "WARNING": ft.Colors.ORANGE_700,
                "ERROR": ft.Colors.RED_700,
            }.get(status, ft.Colors.BLUE_GREY_700)
            path_text = drive_path or local_path or "-"
            rows.append(
                ft.Container(
                    bgcolor=ft.Colors.GREY_50,
                    border_radius=10,
                    border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                    padding=ft.padding.all(10),
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(stamp, size=11, color=ft.Colors.BLUE_GREY_500),
                                    ft.Text(status, size=11, weight=ft.FontWeight.W_700, color=color),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Text(kind or "-", size=12, weight=ft.FontWeight.W_600),
                            ft.Text(path_text, size=11, color=ft.Colors.BLUE_GREY_600, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(message or "Basarili", size=11, color=color if message else ft.Colors.GREEN_700),
                        ],
                        spacing=6,
                    ),
                )
            )
        self.logs_list.controls = rows

    def refresh(self):
        if os.path.exists(self.db_path):
            self.lbl_db_size.value = f"Veritabanı boyutu: {self._fmt_size(self.db_path)}"
        else:
            self.lbl_db_size.value = "Veritabanı bulunamadı"

        # Restore saved local backup dir
        if self.db:
            saved_local = self.db.get_setting("local_backup_dir", "") or ""
            if saved_local and os.path.isdir(saved_local):
                self.backup_dir = saved_local
                self.txt_local_dir.value = saved_local
            else:
                self.txt_local_dir.value = ""

        if self.backup_manager:
            minutes = int(self.backup_manager.interval_seconds / 60)
            self.lbl_auto_backup.value = f"Otomatik yedekleme: {minutes} dakikada bir"
            self.lbl_countdown.value = self.backup_manager.next_backup_label()
            self.dd_target_mode.value = self.backup_manager.target_mode
            self.txt_interval_minutes.value = str(minutes)
            self.txt_drive_dir.value = self.backup_manager.google_drive_dir or ""
            drive_dir = self.backup_manager.google_backup_dir()
            target_map = {
                "LOCAL": "Hedef: Sadece local",
                "DRIVE": "Hedef: Sadece Google Drive",
                "BOTH": "Hedef: Local + Google Drive",
            }
            self.lbl_target_status.value = target_map.get(self.backup_manager.target_mode, self.backup_manager.target_mode)
            self.lbl_target_status.color = ft.Colors.INDIGO_700
            if drive_dir:
                self.lbl_drive_status.value = f"Drive klasoru: {drive_dir}"
                self.lbl_drive_status.color = ft.Colors.GREEN_700
            else:
                self.lbl_drive_status.value = "Drive klasoru ayarli degil"
                self.lbl_drive_status.color = ft.Colors.ORANGE_700
            last = self.backup_manager.last_result
            if last:
                result_bits = []
                if last.local_path:
                    result_bits.append("local")
                if last.drive_path:
                    result_bits.append("drive")
                where = " + ".join(result_bits) if result_bits else last.target_mode.lower()
                status_text = f"Son islem: {last.created_at or '-'} | {where}"
                if last.error:
                    status_text += f" | Hata: {last.error}"
                    self.lbl_last_result.color = ft.Colors.RED_700
                else:
                    self.lbl_last_result.color = ft.Colors.GREEN_700
                self.lbl_last_result.value = status_text
            else:
                self.lbl_last_result.value = "Son islem kaydi henuz yok"
                self.lbl_last_result.color = ft.Colors.BLUE_GREY_600
        else:
            self.lbl_auto_backup.value = "Otomatik yedekleme bu oturumda bagli degil"
            self.lbl_target_status.value = "Hedef: Sadece local"
            self.lbl_drive_status.value = ""
            self.lbl_countdown.value = "--:--"
            self.lbl_last_result.value = "Son islem kaydi henuz yok"

        self._build_file_rows()
        self._build_log_rows()
        self._safe_update()
