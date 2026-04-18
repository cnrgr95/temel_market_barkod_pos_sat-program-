import os
import shutil
import sys
import unittest
import uuid
from unittest.mock import patch

from flet_pos.runtime_paths import get_runtime_paths, migrate_legacy_runtime_data


class RuntimePathsTests(unittest.TestCase):
    def _temp_dir(self) -> str:
        path = os.path.join(os.path.dirname(__file__), "_tmp", uuid.uuid4().hex)
        os.makedirs(path, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_source_mode_uses_project_directory_for_data(self):
        paths = get_runtime_paths()
        self.assertEqual(paths.install_dir, paths.data_dir)
        self.assertTrue(paths.db_path.endswith("market.db"))
        self.assertTrue(paths.media_dir.endswith("product_images"))

    def test_frozen_mode_uses_localappdata_and_migrates_legacy_files(self):
        temp_root = self._temp_dir()
        install_dir = os.path.join(temp_root, "install")
        local_appdata = os.path.join(temp_root, "LocalAppData")
        os.makedirs(install_dir, exist_ok=True)
        os.makedirs(local_appdata, exist_ok=True)

        with open(os.path.join(install_dir, "market.db"), "w", encoding="utf-8") as f:
            f.write("legacy-db")
        os.makedirs(os.path.join(install_dir, "product_images"), exist_ok=True)
        with open(os.path.join(install_dir, "product_images", "demo.txt"), "w", encoding="utf-8") as f:
            f.write("image-placeholder")
        os.makedirs(os.path.join(install_dir, "backups"), exist_ok=True)
        with open(os.path.join(install_dir, "backups", "manual.db"), "w", encoding="utf-8") as f:
            f.write("backup")

        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "executable", os.path.join(install_dir, "TemelMarket.exe")),
            patch.dict(os.environ, {"LOCALAPPDATA": local_appdata}, clear=False),
        ):
            paths = get_runtime_paths()

        self.assertEqual(paths.install_dir, install_dir)
        self.assertEqual(paths.data_dir, os.path.join(local_appdata, "TemelMarket"))
        self.assertTrue(os.path.exists(paths.db_path))
        self.assertTrue(os.path.exists(os.path.join(paths.media_dir, "demo.txt")))
        self.assertTrue(os.path.exists(os.path.join(paths.backup_dir, "manual.db")))

    def test_migrate_legacy_runtime_data_does_not_overwrite_existing_data(self):
        temp_root = self._temp_dir()
        install_dir = os.path.join(temp_root, "install")
        data_dir = os.path.join(temp_root, "data")
        os.makedirs(install_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)

        with open(os.path.join(install_dir, "market.db"), "w", encoding="utf-8") as f:
            f.write("legacy")
        with open(os.path.join(data_dir, "market.db"), "w", encoding="utf-8") as f:
            f.write("current")

        with patch.object(sys, "frozen", True, create=True):
            migrate_legacy_runtime_data(install_dir, data_dir)

        with open(os.path.join(data_dir, "market.db"), "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "current")


if __name__ == "__main__":
    unittest.main()
