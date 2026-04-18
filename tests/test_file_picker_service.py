from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import flet as ft

from flet_pos.services.file_picker import ensure_page_file_picker, resolve_initial_directory


class FilePickerServiceTests(unittest.TestCase):
    def test_ensure_page_file_picker_reuses_single_service(self):
        updates: list[str] = []
        page = SimpleNamespace(services=[], update=lambda: updates.append("updated"))

        picker_a = ensure_page_file_picker(page)
        picker_b = ensure_page_file_picker(page)

        self.assertIsInstance(picker_a, ft.FilePicker)
        self.assertIs(picker_a, picker_b)
        self.assertEqual(page.services, [picker_a])
        self.assertEqual(len(updates), 1)

    def test_resolve_initial_directory_prefers_file_parent_then_fallback(self):
        image_file = r"C:\data\images\urun.png"
        images_dir = r"C:\data\images"
        fallback_dir = r"C:\backup"
        existing_dirs = {images_dir, fallback_dir}
        existing_files = {image_file}

        with (
            patch("flet_pos.services.file_picker.os.path.isfile", side_effect=lambda path: path in existing_files),
            patch("flet_pos.services.file_picker.os.path.isdir", side_effect=lambda path: path in existing_dirs),
        ):
            self.assertEqual(resolve_initial_directory(image_file), images_dir)
            self.assertEqual(resolve_initial_directory(images_dir), images_dir)
            self.assertEqual(resolve_initial_directory(r"C:\missing.png", fallback_dir), fallback_dir)
            self.assertIsNone(resolve_initial_directory(r"C:\missing.png"))

    def test_pages_no_longer_depend_on_tkinter_dialogs(self):
        root = Path(__file__).resolve().parent.parent
        pages = [
            root / "flet_pos" / "pages" / "backup_page.py",
            root / "flet_pos" / "pages" / "products_page.py",
            root / "flet_pos" / "pages" / "pos_page.py",
        ]

        for page_file in pages:
            source = page_file.read_text(encoding="utf-8")
            self.assertNotIn("tkinter", source, page_file)


if __name__ == "__main__":
    unittest.main()
