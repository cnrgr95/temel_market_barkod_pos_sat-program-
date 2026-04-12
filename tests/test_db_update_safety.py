import os
import shutil
import sqlite3
import unittest
import uuid

from flet_pos.db import DB
from flet_pos.services.backup import BackupManager


class DBUpdateSafetyTests(unittest.TestCase):
    def _temp_db_path(self):
        base = os.path.join(os.path.dirname(__file__), "_tmp", uuid.uuid4().hex)
        os.makedirs(base, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(base, ignore_errors=True))
        return os.path.join(base, "market.db")

    def test_legacy_schema_keeps_existing_product_sale_and_settings(self):
        db_path = self._temp_db_path()
        with sqlite3.connect(db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    barcode TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    cost_price REAL NOT NULL DEFAULT 0,
                    sell_price REAL NOT NULL DEFAULT 0,
                    stock REAL NOT NULL DEFAULT 0,
                    critical_stock REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                INSERT INTO products (barcode, name, cost_price, sell_price, stock, critical_stock, created_at)
                VALUES ('8690000000010', 'Legacy Tea', 12.5, 20.0, 7, 2, '2026-01-01 10:00:00');

                CREATE TABLE sale_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sale_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    quantity REAL NOT NULL,
                    unit_price REAL NOT NULL,
                    cost_price REAL NOT NULL,
                    line_total REAL NOT NULL
                );
                INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, cost_price, line_total)
                VALUES (1, 1, 2, 20, 12.5, 40);

                CREATE TABLE settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT NOT NULL
                );
                INSERT INTO settings (setting_key, setting_value)
                VALUES ('company_name', 'Legacy Market');
                """
            )

        db = DB(db_path)
        product = db.get_product_by_barcode("8690000000010")
        self.assertIsNotNone(product)
        self.assertEqual(product[1], "Legacy Tea")
        self.assertEqual(float(product[4]), 20.0)
        self.assertEqual(float(product[6]), 7.0)
        self.assertEqual(db.list_settings()["company_name"], "Legacy Market")

        with db.conn() as conn:
            item = conn.execute(
                "SELECT product_name, qty, unit_price, line_total FROM sale_items WHERE id=1"
            ).fetchone()
        self.assertEqual(item[0], "Legacy Tea")
        self.assertEqual(float(item[1]), 2.0)
        self.assertEqual(float(item[2]), 20.0)
        self.assertEqual(float(item[3]), 40.0)

    def test_failed_sale_rolls_back_and_keeps_stock(self):
        db = DB(self._temp_db_path())
        db.upsert_product(
            barcode="8690000000027",
            name="Limited Stock",
            sell_price_incl_vat=15,
            stock=1,
        )
        product = db.get_product_by_barcode("8690000000027")

        with self.assertRaises(ValueError):
            db.create_sale(
                [
                    {
                        "product_id": product[0],
                        "name": product[1],
                        "qty": 2,
                        "price": product[4],
                        "vat_rate": product[5],
                    }
                ],
                discount=0,
                payment_type="NAKIT",
                cash_amount=30,
                card_amount=0,
                transfer_amount=0,
            )

        with db.conn() as conn:
            stock = conn.execute("SELECT stock FROM products WHERE id=?", (product[0],)).fetchone()[0]
            sale_count = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
        self.assertEqual(float(stock), 1.0)
        self.assertEqual(sale_count, 0)

    def test_settings_and_backup_manager_copy_to_drive_folder(self):
        db_path = self._temp_db_path()
        db = DB(db_path)
        drive_dir = os.path.join(os.path.dirname(db_path), "Google Drive")
        backup_dir = os.path.join(os.path.dirname(db_path), "backups")
        os.makedirs(drive_dir, exist_ok=True)

        db.set_setting("google_drive_backup_dir", drive_dir)
        self.assertEqual(db.get_setting("google_drive_backup_dir"), drive_dir)

        manager = BackupManager(
            base_dir=os.path.dirname(db_path),
            db_path=db_path,
            backup_dir=backup_dir,
            interval_seconds=7200,
            google_drive_dir=db.get_setting("google_drive_backup_dir"),
        )
        result = manager.backup_now(prefix="test")

        self.assertTrue(os.path.exists(result.local_path))
        self.assertEqual(result.error, "")
        self.assertTrue(result.drive_path, "Drive path was not set")
        self.assertTrue(os.path.exists(result.drive_path), result.drive_path)


if __name__ == "__main__":
    unittest.main()
