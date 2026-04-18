from pathlib import Path
import unittest


class PackagingAssetsTests(unittest.TestCase):
    def test_webview2_installer_script_exists_for_inno_setup(self):
        root = Path(__file__).resolve().parent.parent
        installer_script = root / "installer" / "install_webview2.ps1"
        iss_text = (root / "installer.iss").read_text(encoding="utf-8")
        spec_text = (root / "TemelMarket.spec").read_text(encoding="utf-8")

        self.assertIn(r"installer\install_webview2.ps1", iss_text)
        self.assertTrue(installer_script.exists(), installer_script)
        self.assertIn('install_webview2.ps1', spec_text)

    def test_build_uses_compatibility_focused_spec_without_upx(self):
        root = Path(__file__).resolve().parent.parent
        build_bat = (root / "Build-Setup.bat").read_text(encoding="utf-8")
        spec_text = (root / "TemelMarket.spec").read_text(encoding="utf-8")

        self.assertIn("TemelMarket.spec", build_bat)
        self.assertIn('("flet", "flet_desktop", "flet_web")', spec_text)
        self.assertIn("collect_all(package_name)", spec_text)
        self.assertIn("upx=False", spec_text)


if __name__ == "__main__":
    unittest.main()
