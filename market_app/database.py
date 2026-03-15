import sqlite3
from datetime import datetime


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._setup()

    def conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _setup(self) -> None:
        with self.conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    barcode TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    cost_price REAL NOT NULL DEFAULT 0,
                    sell_price REAL NOT NULL DEFAULT 0,
                    sell_price_2 REAL NOT NULL DEFAULT 0,
                    sell_price_3 REAL NOT NULL DEFAULT 0,
                    card_price REAL NOT NULL DEFAULT 0,
                    stock REAL NOT NULL DEFAULT 0,
                    critical_stock REAL NOT NULL DEFAULT 0,
                    image_path TEXT,
                    unit TEXT,
                    category TEXT,
                    supplier TEXT,
                    special_code TEXT,
                    expiry_date TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT,
                    email TEXT,
                    balance REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sale_time TEXT NOT NULL,
                    subtotal REAL NOT NULL,
                    discount REAL NOT NULL,
                    total REAL NOT NULL,
                    payment_type TEXT NOT NULL,
                    cash_amount REAL NOT NULL DEFAULT 0,
                    pos_amount REAL NOT NULL DEFAULT 0,
                    customer_id INTEGER,
                    notes TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS sale_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sale_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    quantity REAL NOT NULL,
                    unit_price REAL NOT NULL,
                    cost_price REAL NOT NULL,
                    line_total REAL NOT NULL,
                    FOREIGN KEY (sale_id) REFERENCES sales(id),
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    payment_time TEXT NOT NULL,
                    amount REAL NOT NULL,
                    payment_method TEXT NOT NULL,
                    note TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'KASIYER',
                    can_discount INTEGER NOT NULL DEFAULT 0,
                    can_reports INTEGER NOT NULL DEFAULT 1,
                    can_settings INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS cash_moves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    move_time TEXT NOT NULL,
                    move_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    note TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT NOT NULL
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_time ON sales(sale_time)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_customers_balance ON customers(balance)")

            self._ensure_column(cur, "products", "image_path", "TEXT")
            self._ensure_column(cur, "products", "sell_price_2", "REAL NOT NULL DEFAULT 0")
            self._ensure_column(cur, "products", "sell_price_3", "REAL NOT NULL DEFAULT 0")
            self._ensure_column(cur, "products", "card_price", "REAL NOT NULL DEFAULT 0")
            self._ensure_column(cur, "products", "unit", "TEXT")
            self._ensure_column(cur, "products", "category", "TEXT")
            self._ensure_column(cur, "products", "supplier", "TEXT")
            self._ensure_column(cur, "products", "special_code", "TEXT")
            self._ensure_column(cur, "products", "expiry_date", "TEXT")
            self._ensure_column(cur, "customers", "email", "TEXT")

            self._seed_settings(cur)
            self._seed_default_admin(cur)
            conn.commit()

    def _ensure_column(self, cur, table: str, column: str, definition: str) -> None:
        cols = cur.execute(f"PRAGMA table_info({table})").fetchall()
        col_names = [row[1] for row in cols]
        if column not in col_names:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _seed_settings(self, cur) -> None:
        defaults = {
            "company_name": "Temel Market",
            "company_phone": "",
            "default_kdv": "20",
            "backup_interval_seconds": "300",
            "quick_button_count": "24",
            "default_price_type": "sell_price",
        }
        for key, value in defaults.items():
            cur.execute(
                "INSERT OR IGNORE INTO settings (setting_key, setting_value) VALUES (?, ?)",
                (key, value),
            )

    def _seed_default_admin(self, cur) -> None:
        existing = cur.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
        if existing:
            return
        cur.execute(
            """
            INSERT INTO users (username, password, role, can_discount, can_reports, can_settings, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("admin", "1234", "ADMIN", 1, 1, 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )

    def get_setting(self, key: str, default: str = "") -> str:
        with self.conn() as conn:
            row = conn.execute(
                "SELECT setting_value FROM settings WHERE setting_key = ?",
                (key,),
            ).fetchone()
        if not row:
            return default
        return row[0]

    def set_setting(self, key: str, value: str) -> None:
        with self.conn() as conn:
            conn.execute(
                """
                INSERT INTO settings (setting_key, setting_value)
                VALUES (?, ?)
                ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value
                """,
                (key, value),
            )
            conn.commit()

    def upsert_product(
        self,
        barcode: str,
        name: str,
        cost_price: float,
        sell_price: float,
        stock: float,
        critical_stock: float,
        sell_price_2: float = 0.0,
        sell_price_3: float = 0.0,
        card_price: float = 0.0,
        image_path: str = "",
        unit: str = "",
        category: str = "",
        supplier: str = "",
        special_code: str = "",
        expiry_date: str = "",
    ) -> bool:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.conn() as conn:
            cur = conn.cursor()
            existing = cur.execute("SELECT id FROM products WHERE barcode = ?", (barcode,)).fetchone()
            if existing:
                cur.execute(
                    """
                    UPDATE products
                    SET name=?, cost_price=?, sell_price=?, stock=?, critical_stock=?,
                        sell_price_2=?, sell_price_3=?, card_price=?, image_path=?,
                        unit=?, category=?, supplier=?, special_code=?, expiry_date=?
                    WHERE barcode=?
                    """,
                    (
                        name,
                        cost_price,
                        sell_price,
                        stock,
                        critical_stock,
                        sell_price_2,
                        sell_price_3,
                        card_price,
                        image_path,
                        unit,
                        category,
                        supplier,
                        special_code,
                        expiry_date,
                        barcode,
                    ),
                )
                conn.commit()
                return False

            cur.execute(
                """
                INSERT INTO products (
                    barcode, name, cost_price, sell_price, stock, critical_stock,
                    sell_price_2, sell_price_3, card_price, image_path,
                    unit, category, supplier, special_code, expiry_date, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    barcode,
                    name,
                    cost_price,
                    sell_price,
                    stock,
                    critical_stock,
                    sell_price_2,
                    sell_price_3,
                    card_price,
                    image_path,
                    unit,
                    category,
                    supplier,
                    special_code,
                    expiry_date,
                    now,
                ),
            )
            conn.commit()
            return True
