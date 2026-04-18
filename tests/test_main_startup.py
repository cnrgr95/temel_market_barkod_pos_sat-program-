import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import main


class MainStartupTests(unittest.TestCase):
    def test_configure_embedded_flet_view_path_prefers_bundled_client(self):
        install_dir = r"C:\bundle"
        bundled_dir = os.path.join(install_dir, "_internal", "flet_desktop", "app", "flet")
        bundled_exe = os.path.join(bundled_dir, "flet.exe")

        with (
            patch.dict(os.environ, {}, clear=False),
            patch("main.get_runtime_paths", return_value=SimpleNamespace(install_dir=install_dir)),
            patch("main.os.path.isfile", side_effect=lambda path: path == bundled_exe),
        ):
            os.environ.pop("FLET_VIEW_PATH", None)
            main._configure_embedded_flet_view_path()
            self.assertEqual(os.environ.get("FLET_VIEW_PATH"), bundled_dir)

    def test_configure_embedded_flet_view_path_keeps_existing_override(self):
        with patch.dict(os.environ, {"FLET_VIEW_PATH": r"C:\custom\flet"}, clear=False):
            main._configure_embedded_flet_view_path()
            self.assertEqual(os.environ.get("FLET_VIEW_PATH"), r"C:\custom\flet")


if __name__ == "__main__":
    unittest.main()
