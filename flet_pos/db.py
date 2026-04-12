import hashlib
import os
import sqlite3
from datetime import datetime


def _hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256 ile sifre hashle."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return salt.hex() + ":" + dk.hex()


def _verify_password(password: str, stored: str) -> bool:
    """Hashli sifre dogrula. Eski duz-metin sifreleri de destekle."""
    if ":" not in stored:
        return password == stored
    salt_hex, dk_hex = stored.split(":", 1)
    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return password == stored
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return dk.hex() == dk_hex


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class DB:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._setup()

    def conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path, timeout=15)
        c.execute("PRAGMA foreign_keys = ON")
        c.execute("PRAGMA busy_timeout = 15000")
        c.execute("PRAGMA journal_mode = WAL")
        c.execute("PRAGMA synchronous = NORMAL")
        c.execute("PRAGMA temp_store = MEMORY")
        return c

    def _setup(self) -> None:
        with self.conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    barcode TEXT UNIQUE NOT NULL,
                    description TEXT,
                    category TEXT,
                    sub_category TEXT,
                    unit TEXT NOT NULL DEFAULT 'adet',
                    buy_price REAL NOT NULL DEFAULT 0,
                    sell_price_excl_vat REAL NOT NULL DEFAULT 0,
                    sell_price_incl_vat REAL NOT NULL DEFAULT 0,
                    vat_rate REAL NOT NULL DEFAULT 20,
                    vat_mode TEXT NOT NULL DEFAULT 'INCL',
                    stock REAL NOT NULL DEFAULT 0,
                    critical_stock REAL NOT NULL DEFAULT 5,
                    image_path TEXT,
                    is_scale_product INTEGER NOT NULL DEFAULT 0,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    supplier_id INTEGER,
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
                    address TEXT,
                    email TEXT,
                    balance REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS suppliers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT,
                    address TEXT,
                    debt REAL NOT NULL DEFAULT 0,
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
                    discount REAL NOT NULL DEFAULT 0,
                    total REAL NOT NULL,
                    payment_type TEXT NOT NULL,
                    cash_amount REAL NOT NULL DEFAULT 0,
                    card_amount REAL NOT NULL DEFAULT 0,
                    transfer_amount REAL NOT NULL DEFAULT 0,
                    customer_id INTEGER,
                    is_return INTEGER NOT NULL DEFAULT 0,
                    user_id INTEGER,
                    note TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS sale_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sale_id INTEGER NOT NULL,
                    product_id INTEGER,
                    product_name TEXT NOT NULL DEFAULT '',
                    qty REAL NOT NULL DEFAULT 0,
                    unit_price REAL NOT NULL DEFAULT 0,
                    item_discount REAL NOT NULL DEFAULT 0,
                    vat_rate REAL NOT NULL DEFAULT 0,
                    line_total REAL NOT NULL DEFAULT 0
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS stock_moves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    move_time TEXT NOT NULL,
                    product_id INTEGER,
                    product_name TEXT NOT NULL DEFAULT '',
                    move_type TEXT NOT NULL,
                    qty REAL NOT NULL,
                    note TEXT
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
                    sale_id INTEGER,
                    note TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS app_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL,
                    can_discount INTEGER NOT NULL DEFAULT 0,
                    can_price_change INTEGER NOT NULL DEFAULT 0,
                    can_return INTEGER NOT NULL DEFAULT 0,
                    can_reports INTEGER NOT NULL DEFAULT 0,
                    can_products INTEGER NOT NULL DEFAULT 0,
                    can_stock INTEGER NOT NULL DEFAULT 0,
                    can_customers INTEGER NOT NULL DEFAULT 0,
                    can_suppliers INTEGER NOT NULL DEFAULT 0,
                    can_cash INTEGER NOT NULL DEFAULT 0,
                    can_users INTEGER NOT NULL DEFAULT 0,
                    can_backup INTEGER NOT NULL DEFAULT 0,
                    can_hardware INTEGER NOT NULL DEFAULT 0,
                    can_sales_history INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

            cur.execute("CREATE INDEX IF NOT EXISTS idx_prod_barcode ON products(barcode)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_time ON sales(sale_time)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_return ON sales(is_return)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_stock_moves_time ON stock_moves(move_time)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sale_items_sale_id ON sale_items(sale_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sale_items_product_id ON sale_items(product_id)")

            self._migrate_all(cur)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_prod_active_barcode ON products(is_active, barcode)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_prod_active_name ON products(is_active, name)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_prod_active_category ON products(is_active, category)")

            # Varsayilan admin - ilk kurulumda olustur
            admin_exists = cur.execute("SELECT COUNT(*) FROM app_users WHERE role='ADMIN'").fetchone()[0]
            if admin_exists == 0:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO app_users
                    (username, password, role, can_discount, can_price_change, can_return, can_reports,
                     can_products, can_stock, can_customers, can_suppliers, can_cash, can_users, can_backup, can_hardware, can_sales_history)
                    VALUES (?,?,?,1,1,1,1,1,1,1,1,1,1,1,1,1)
                    """,
                    ("admin", _hash_password("1234"), "ADMIN"),
                )

            key_col, value_col = self._settings_columns(cur)
            cur.execute(f"INSERT OR IGNORE INTO settings ({key_col}, {value_col}) VALUES ('company_name', 'Temel Market')")
            cur.execute(f"INSERT OR IGNORE INTO settings ({key_col}, {value_col}) VALUES ('currency', 'TRY')")
            conn.commit()

    # ── Migration ────────────────────────────────────────────────────────────

    def _table_columns(self, cur, table: str) -> list[str]:
        return [row[1] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()]

    def _ensure_column(self, cur, table: str, column: str, definition: str) -> None:
        if column not in self._table_columns(cur, table):
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _migrate_all(self, cur) -> None:
        self._migrate_products_columns(cur)
        self._migrate_customers_columns(cur)
        self._migrate_suppliers_columns(cur)
        self._migrate_sales_columns(cur)
        self._migrate_sale_items_columns(cur)
        self._migrate_stock_moves_columns(cur)
        self._migrate_cash_moves_columns(cur)
        self._migrate_users_columns(cur)
        self._migrate_passwords(cur)

    def _migrate_products_columns(self, cur) -> None:
        self._ensure_column(cur, "products", "description", "TEXT")
        self._ensure_column(cur, "products", "category", "TEXT")
        self._ensure_column(cur, "products", "sub_category", "TEXT")
        self._ensure_column(cur, "products", "unit", "TEXT NOT NULL DEFAULT 'adet'")
        self._ensure_column(cur, "products", "buy_price", "REAL NOT NULL DEFAULT 0")
        self._ensure_column(cur, "products", "sell_price_excl_vat", "REAL NOT NULL DEFAULT 0")
        self._ensure_column(cur, "products", "sell_price_incl_vat", "REAL NOT NULL DEFAULT 0")
        self._ensure_column(cur, "products", "vat_rate", "REAL NOT NULL DEFAULT 20")
        self._ensure_column(cur, "products", "vat_mode", "TEXT NOT NULL DEFAULT 'INCL'")
        self._ensure_column(cur, "products", "image_path", "TEXT")
        self._ensure_column(cur, "products", "is_scale_product", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column(cur, "products", "is_active", "INTEGER NOT NULL DEFAULT 1")
        self._ensure_column(cur, "products", "supplier_id", "INTEGER")
        cols = self._table_columns(cur, "products")
        if "cost_price" in cols:
            cur.execute("UPDATE products SET buy_price = cost_price WHERE COALESCE(buy_price,0)=0")
        if "sell_price" in cols:
            cur.execute("UPDATE products SET sell_price_incl_vat = sell_price WHERE COALESCE(sell_price_incl_vat,0)=0")
            cur.execute("UPDATE products SET sell_price_excl_vat = sell_price_incl_vat/(1+(vat_rate/100.0)) WHERE COALESCE(sell_price_excl_vat,0)=0")
            cur.execute("UPDATE products SET vat_mode='INCL' WHERE vat_mode IS NULL OR vat_mode=''")

    def _migrate_customers_columns(self, cur) -> None:
        self._ensure_column(cur, "customers", "phone", "TEXT")
        self._ensure_column(cur, "customers", "address", "TEXT")
        self._ensure_column(cur, "customers", "email", "TEXT")
        self._ensure_column(cur, "customers", "balance", "REAL NOT NULL DEFAULT 0")

    def _migrate_suppliers_columns(self, cur) -> None:
        self._ensure_column(cur, "suppliers", "phone", "TEXT")
        self._ensure_column(cur, "suppliers", "address", "TEXT")
        self._ensure_column(cur, "suppliers", "debt", "REAL NOT NULL DEFAULT 0")
        self._ensure_column(cur, "suppliers", "created_at", "TEXT")
        cur.execute("UPDATE suppliers SET created_at=datetime('now') WHERE created_at IS NULL OR created_at=''")

    def _migrate_sales_columns(self, cur) -> None:
        self._ensure_column(cur, "sales", "cash_amount", "REAL NOT NULL DEFAULT 0")
        self._ensure_column(cur, "sales", "card_amount", "REAL NOT NULL DEFAULT 0")
        self._ensure_column(cur, "sales", "transfer_amount", "REAL NOT NULL DEFAULT 0")
        self._ensure_column(cur, "sales", "customer_id", "INTEGER")
        self._ensure_column(cur, "sales", "is_return", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column(cur, "sales", "user_id", "INTEGER")
        self._ensure_column(cur, "sales", "note", "TEXT")

    def _migrate_sale_items_columns(self, cur) -> None:
        cols = self._table_columns(cur, "sale_items")
        needs_rebuild = "cost_price" in cols or ("quantity" in cols and "qty" not in cols)
        if needs_rebuild:
            qty_src = "quantity" if "quantity" in cols else ("qty" if "qty" in cols else "0")
            lt_src = "line_total" if "line_total" in cols else f"({qty_src}*unit_price)"
            id_src = "id" if "id" in cols else "rowid"
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS sale_items_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sale_id INTEGER NOT NULL,
                    product_id INTEGER,
                    product_name TEXT NOT NULL DEFAULT '',
                    qty REAL NOT NULL DEFAULT 0,
                    unit_price REAL NOT NULL DEFAULT 0,
                    item_discount REAL NOT NULL DEFAULT 0,
                    vat_rate REAL NOT NULL DEFAULT 0,
                    line_total REAL NOT NULL DEFAULT 0
                )
                """
            )
            cur.execute(
                f"""
                INSERT INTO sale_items_new (id, sale_id, product_id, qty, unit_price, item_discount, vat_rate, line_total)
                SELECT {id_src}, sale_id, product_id,
                       COALESCE({qty_src},0), COALESCE(unit_price,0),
                       COALESCE({'item_discount' if 'item_discount' in cols else '0'},0),
                       COALESCE({'vat_rate' if 'vat_rate' in cols else '0'},0),
                       COALESCE({lt_src},0)
                FROM sale_items
                """
            )
            cur.execute("DROP TABLE sale_items")
            cur.execute("ALTER TABLE sale_items_new RENAME TO sale_items")
        else:
            self._ensure_column(cur, "sale_items", "qty", "REAL NOT NULL DEFAULT 0")
            self._ensure_column(cur, "sale_items", "item_discount", "REAL NOT NULL DEFAULT 0")
            self._ensure_column(cur, "sale_items", "vat_rate", "REAL NOT NULL DEFAULT 0")
            self._ensure_column(cur, "sale_items", "line_total", "REAL NOT NULL DEFAULT 0")
            self._ensure_column(cur, "sale_items", "product_name", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(cur, "sale_items", "product_id", "INTEGER")
            cols = self._table_columns(cur, "sale_items")
            if "quantity" in cols:
                cur.execute("UPDATE sale_items SET qty=quantity WHERE COALESCE(qty,0)=0")
            if "line_total" in cols and "qty" in cols and "unit_price" in cols:
                cur.execute("UPDATE sale_items SET line_total=qty*unit_price WHERE COALESCE(line_total,0)=0")
        # product_name snapshot'larini doldur
        cur.execute(
            """
            UPDATE sale_items SET product_name = (
                SELECT name FROM products WHERE products.id = sale_items.product_id
            )
            WHERE (product_name IS NULL OR product_name='') AND product_id IS NOT NULL
            """
        )

    def _migrate_stock_moves_columns(self, cur) -> None:
        self._ensure_column(cur, "stock_moves", "product_name", "TEXT NOT NULL DEFAULT ''")
        cur.execute(
            """
            UPDATE stock_moves SET product_name = (
                SELECT name FROM products WHERE products.id = stock_moves.product_id
            )
            WHERE (product_name IS NULL OR product_name='') AND product_id IS NOT NULL
            """
        )

    def _migrate_cash_moves_columns(self, cur) -> None:
        self._ensure_column(cur, "cash_moves", "sale_id", "INTEGER")

    def _migrate_users_columns(self, cur) -> None:
        self._ensure_column(cur, "app_users", "can_products", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column(cur, "app_users", "can_stock", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column(cur, "app_users", "can_customers", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column(cur, "app_users", "can_suppliers", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column(cur, "app_users", "can_cash", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column(cur, "app_users", "can_users", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column(cur, "app_users", "can_backup", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column(cur, "app_users", "can_hardware", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column(cur, "app_users", "can_sales_history", "INTEGER NOT NULL DEFAULT 0")
        cur.execute(
            """
            UPDATE app_users
            SET can_products=1, can_stock=1, can_customers=1, can_suppliers=1,
                can_cash=1, can_users=1, can_backup=1, can_hardware=1, can_sales_history=1
            WHERE role='ADMIN'
            """
        )

    def _migrate_passwords(self, cur) -> None:
        """Duz-metin sifreleri hash'e donustur."""
        rows = cur.execute("SELECT id, password FROM app_users").fetchall()
        for uid, pwd in rows:
            if ":" not in pwd:
                cur.execute("UPDATE app_users SET password=? WHERE id=?", (_hash_password(pwd), uid))

    def _settings_columns(self, cur) -> tuple[str, str]:
        cols = [row[1] for row in cur.execute("PRAGMA table_info(settings)").fetchall()]
        if "key" in cols and "value" in cols:
            return "key", "value"
        if "setting_key" in cols and "setting_value" in cols:
            return "setting_key", "setting_value"
        return "key", "value"

    def list_settings(self) -> dict[str, str]:
        with self.conn() as conn:
            key_col, value_col = self._settings_columns(conn.cursor())
            rows = conn.execute(f"SELECT {key_col}, {value_col} FROM settings").fetchall()
        return {str(k): str(v) for k, v in rows}

    def get_setting(self, key: str, default: str = "") -> str:
        with self.conn() as conn:
            key_col, value_col = self._settings_columns(conn.cursor())
            row = conn.execute(
                f"SELECT {value_col} FROM settings WHERE {key_col}=?",
                (key,),
            ).fetchone()
        return str(row[0]) if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.conn() as conn:
            cur = conn.cursor()
            key_col, value_col = self._settings_columns(cur)
            cur.execute(
                f"""
                INSERT INTO settings ({key_col}, {value_col})
                VALUES (?, ?)
                ON CONFLICT({key_col}) DO UPDATE SET {value_col}=excluded.{value_col}
                """,
                (key, value),
            )
            conn.commit()

    # ── Ürünler ──────────────────────────────────────────────────────────────

    def upsert_product(
        self,
        *,
        barcode: str,
        name: str,
        description: str = "",
        category: str = "",
        sub_category: str = "",
        unit: str = "adet",
        buy_price: float = 0,
        sell_price_excl_vat: float = 0,
        sell_price_incl_vat: float = 0,
        vat_rate: float = 20,
        vat_mode: str = "INCL",
        stock: float = 0,
        critical_stock: float = 5,
        image_path: str = "",
        is_scale_product: bool = False,
        supplier_id: int | None = None,
        old_stock: float | None = None,
    ) -> bool:
        with self.conn() as conn:
            cur = conn.cursor()
            row = cur.execute("SELECT id, stock FROM products WHERE barcode=?", (barcode,)).fetchone()
            if row:
                cur.execute(
                    """
                    UPDATE products
                    SET name=?, description=?, category=?, sub_category=?, unit=?, buy_price=?,
                        sell_price_excl_vat=?, sell_price_incl_vat=?, vat_rate=?, vat_mode=?, stock=?,
                        critical_stock=?, image_path=?, is_scale_product=?, supplier_id=?
                    WHERE barcode=?
                    """,
                    (name, description, category, sub_category, unit, buy_price,
                     sell_price_excl_vat, sell_price_incl_vat, vat_rate, vat_mode,
                     stock, critical_stock, image_path, 1 if is_scale_product else 0,
                     supplier_id, barcode),
                )
                # Stok degistiyse hareket kaydet
                prev_stock = float(row[1] or 0)
                if abs(stock - prev_stock) > 0.001:
                    diff = stock - prev_stock
                    move_type = "IN" if diff > 0 else "OUT"
                    cur.execute(
                        "INSERT INTO stock_moves (move_time,product_id,product_name,move_type,qty,note) VALUES(?,?,?,?,?,?)",
                        (_now(), row[0], name, move_type, abs(diff), "Urun guncelleme"),
                    )
                conn.commit()
                return False
            cur.execute(
                """
                INSERT INTO products (
                    name, barcode, description, category, sub_category, unit, buy_price,
                    sell_price_excl_vat, sell_price_incl_vat, vat_rate, vat_mode,
                    stock, critical_stock, image_path, is_scale_product, supplier_id, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (name, barcode, description, category, sub_category, unit, buy_price,
                 sell_price_excl_vat, sell_price_incl_vat, vat_rate, vat_mode,
                 stock, critical_stock, image_path, 1 if is_scale_product else 0,
                 supplier_id, _now()),
            )
            new_id = cur.lastrowid
            if stock > 0:
                cur.execute(
                    "INSERT INTO stock_moves (move_time,product_id,product_name,move_type,qty,note) VALUES(?,?,?,?,?,?)",
                    (_now(), new_id, name, "IN", stock, "Ilk stok girisi"),
                )
            conn.commit()
            return True

    def get_product_full(self, product_id: int):
        with self.conn() as conn:
            return conn.execute(
                """
                SELECT id, name, barcode, description, category, sub_category, unit,
                       buy_price, sell_price_excl_vat, sell_price_incl_vat,
                       vat_rate, vat_mode, stock, critical_stock, image_path,
                       is_scale_product, supplier_id
                FROM products WHERE id=?
                """,
                (product_id,),
            ).fetchone()

    def delete_product(self, product_id: int) -> None:
        with self.conn() as conn:
            conn.execute("UPDATE products SET is_active=0 WHERE id=?", (product_id,))
            conn.commit()

    def list_products(self, include_inactive: bool = False):
        with self.conn() as conn:
            where = "" if include_inactive else "WHERE COALESCE(is_active,1)=1"
            return conn.execute(
                f"""
                SELECT id, name, barcode, unit, sell_price_incl_vat, vat_rate,
                       stock, image_path, is_scale_product, critical_stock, category
                FROM products {where}
                ORDER BY name
                """
            ).fetchall()

    def list_categories(self) -> list[str]:
        with self.conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT category FROM products WHERE COALESCE(is_active,1)=1 AND category IS NOT NULL AND category != '' ORDER BY category"
            ).fetchall()
            return [r[0] for r in rows]

    def get_product_by_barcode(self, barcode: str):
        with self.conn() as conn:
            return conn.execute(
                """
                SELECT id, name, barcode, unit, sell_price_incl_vat, vat_rate,
                       stock, image_path, is_scale_product, critical_stock
                FROM products
                WHERE barcode=? AND COALESCE(is_active,1)=1
                """,
                (barcode,),
            ).fetchone()

    # ── Müşteriler ────────────────────────────────────────────────────────────

    def list_customers(self):
        with self.conn() as conn:
            return conn.execute(
                "SELECT id, name, phone, address, balance FROM customers ORDER BY name"
            ).fetchall()

    def add_customer(self, name: str, phone: str = "", address: str = "", email: str = "") -> int:
        with self.conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO customers (name,phone,address,email,balance,created_at) VALUES(?,?,?,?,0,?)",
                (name, phone, address, email, _now()),
            )
            conn.commit()
            return cur.lastrowid

    def update_customer(self, customer_id: int, name: str, phone: str, address: str) -> None:
        with self.conn() as conn:
            conn.execute(
                "UPDATE customers SET name=?,phone=?,address=? WHERE id=?",
                (name, phone, address, customer_id),
            )
            conn.commit()

    def delete_customer(self, customer_id: int) -> None:
        with self.conn() as conn:
            conn.execute("DELETE FROM customers WHERE id=?", (customer_id,))
            conn.commit()

    def add_customer_payment(self, customer_id: int, amount: float) -> None:
        with self.conn() as conn:
            conn.execute("UPDATE customers SET balance=balance-? WHERE id=?", (amount, customer_id))
            conn.commit()

    # ── Tedarikçiler ──────────────────────────────────────────────────────────

    def list_suppliers(self):
        with self.conn() as conn:
            return conn.execute("SELECT id, name, phone, debt FROM suppliers ORDER BY name").fetchall()

    def add_supplier(self, name: str, phone: str = "", address: str = "") -> None:
        with self.conn() as conn:
            conn.execute(
                "INSERT INTO suppliers (name,phone,address,debt,created_at) VALUES(?,?,?,0,?)",
                (name, phone, address, _now()),
            )
            conn.commit()

    def update_supplier(self, supplier_id: int, name: str, phone: str, address: str = "") -> None:
        with self.conn() as conn:
            conn.execute("UPDATE suppliers SET name=?,phone=?,address=? WHERE id=?", (name, phone, address, supplier_id))
            conn.commit()

    def delete_supplier(self, supplier_id: int) -> None:
        with self.conn() as conn:
            conn.execute("DELETE FROM suppliers WHERE id=?", (supplier_id,))
            conn.commit()

    def add_supplier_debt(self, supplier_id: int, amount: float) -> None:
        with self.conn() as conn:
            conn.execute("UPDATE suppliers SET debt=debt+? WHERE id=?", (amount, supplier_id))
            conn.commit()

    def add_supplier_payment(self, supplier_id: int, amount: float) -> None:
        with self.conn() as conn:
            conn.execute("UPDATE suppliers SET debt=debt-? WHERE id=?", (amount, supplier_id))
            conn.commit()

    # ── Stok Hareketleri ─────────────────────────────────────────────────────

    def add_stock_move(self, product_id: int, move_type: str, qty: float, note: str = "") -> None:
        sign = 1 if move_type.upper() == "IN" else -1
        with self.conn() as conn:
            if qty <= 0:
                raise ValueError("Miktar 0'dan buyuk olmalidir")
            row = conn.execute("SELECT name, stock FROM products WHERE id=?", (product_id,)).fetchone()
            if not row:
                raise ValueError("Urun bulunamadi")
            name, cur_stock = row[0], float(row[1] or 0)
            new_stock = cur_stock + (sign * qty)
            if new_stock < 0:
                raise ValueError(f"Yetersiz stok: {name}")
            conn.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, product_id))
            conn.execute(
                "INSERT INTO stock_moves (move_time,product_id,product_name,move_type,qty,note) VALUES(?,?,?,?,?,?)",
                (_now(), product_id, name, move_type.upper(), qty, note),
            )
            conn.commit()

    def list_stock_moves(self, limit: int = 500, date_from: str = "", date_to: str = ""):
        where_parts = ["1=1"]
        params: list = []
        if date_from:
            where_parts.append("date(sm.move_time) >= ?")
            params.append(date_from)
        if date_to:
            where_parts.append("date(sm.move_time) <= ?")
            params.append(date_to)
        params.append(limit)
        with self.conn() as conn:
            return conn.execute(
                f"""
                SELECT sm.move_time,
                       COALESCE(NULLIF(sm.product_name,''), p.name, '(silindi)') AS pname,
                       sm.move_type, sm.qty, sm.note
                FROM stock_moves sm
                LEFT JOIN products p ON p.id = sm.product_id
                WHERE {' AND '.join(where_parts)}
                ORDER BY sm.id DESC LIMIT ?
                """,
                params,
            ).fetchall()

    # ── Kasa Hareketleri ──────────────────────────────────────────────────────

    def add_cash_move(self, move_type: str, amount: float, note: str = "", sale_id: int | None = None) -> None:
        with self.conn() as conn:
            conn.execute(
                "INSERT INTO cash_moves (move_time,move_type,amount,sale_id,note) VALUES(?,?,?,?,?)",
                (_now(), move_type.upper(), amount, sale_id, note),
            )
            conn.commit()

    def get_cash_balance(self) -> float:
        with self.conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(CASE WHEN move_type='IN' THEN amount ELSE -amount END),0) FROM cash_moves"
            ).fetchone()
            return float(row[0] or 0)

    def list_cash_moves(self, limit: int = 500, date_from: str = "", date_to: str = ""):
        where_parts = ["1=1"]
        params: list = []
        if date_from:
            where_parts.append("date(move_time) >= ?")
            params.append(date_from)
        if date_to:
            where_parts.append("date(move_time) <= ?")
            params.append(date_to)
        params.append(limit)
        with self.conn() as conn:
            return conn.execute(
                f"SELECT move_time, move_type, amount, note FROM cash_moves "
                f"WHERE {' AND '.join(where_parts)} ORDER BY id DESC LIMIT ?",
                params,
            ).fetchall()

    # ── Kullanıcılar ──────────────────────────────────────────────────────────

    def list_users(self):
        with self.conn() as conn:
            return conn.execute(
                """
                SELECT id,username,role,can_discount,can_price_change,can_return,can_reports,
                       can_products,can_stock,can_customers,can_suppliers,can_cash,
                       can_users,can_backup,can_hardware,can_sales_history
                FROM app_users ORDER BY id
                """
            ).fetchall()

    def authenticate_user(self, username: str, password: str):
        with self.conn() as conn:
            row = conn.execute(
                """
                SELECT id,username,role,can_discount,can_price_change,can_return,can_reports,
                       can_products,can_stock,can_customers,can_suppliers,can_cash,
                       can_users,can_backup,can_hardware,can_sales_history,password
                FROM app_users WHERE username=?
                """,
                (username,),
            ).fetchone()
        if not row:
            return None
        if not _verify_password(password, row[16]):
            return None
        return {
            "id": row[0], "username": row[1], "role": row[2],
            "can_discount": bool(row[3]), "can_price_change": bool(row[4]),
            "can_return": bool(row[5]), "can_reports": bool(row[6]),
            "can_products": bool(row[7]), "can_stock": bool(row[8]), "can_customers": bool(row[9]),
            "can_suppliers": bool(row[10]), "can_cash": bool(row[11]), "can_users": bool(row[12]),
            "can_backup": bool(row[13]), "can_hardware": bool(row[14]), "can_sales_history": bool(row[15]),
        }

    def add_user(
        self,
        username: str,
        password: str,
        role: str,
        can_discount: bool,
        can_price_change: bool,
        can_return: bool,
        can_reports: bool,
        can_products: bool = False,
        can_stock: bool = False,
        can_customers: bool = False,
        can_suppliers: bool = False,
        can_cash: bool = False,
        can_users: bool = False,
        can_backup: bool = False,
        can_hardware: bool = False,
        can_sales_history: bool = False,
    ) -> None:
        with self.conn() as conn:
            conn.execute(
                """
                INSERT INTO app_users
                (username,password,role,can_discount,can_price_change,can_return,can_reports,
                 can_products,can_stock,can_customers,can_suppliers,can_cash,can_users,can_backup,can_hardware,can_sales_history)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    username, _hash_password(password), role,
                    int(can_discount), int(can_price_change), int(can_return), int(can_reports),
                    int(can_products), int(can_stock), int(can_customers), int(can_suppliers),
                    int(can_cash), int(can_users), int(can_backup), int(can_hardware), int(can_sales_history),
                ),
            )
            conn.commit()

    def update_user(
        self,
        user_id: int,
        password: str,
        role: str,
        can_discount: bool,
        can_price_change: bool,
        can_return: bool,
        can_reports: bool,
        can_products: bool = False,
        can_stock: bool = False,
        can_customers: bool = False,
        can_suppliers: bool = False,
        can_cash: bool = False,
        can_users: bool = False,
        can_backup: bool = False,
        can_hardware: bool = False,
        can_sales_history: bool = False,
    ) -> None:
        with self.conn() as conn:
            if password:
                conn.execute(
                    """
                    UPDATE app_users
                    SET password=?,role=?,can_discount=?,can_price_change=?,can_return=?,can_reports=?,
                        can_products=?,can_stock=?,can_customers=?,can_suppliers=?,can_cash=?,
                        can_users=?,can_backup=?,can_hardware=?,can_sales_history=?
                    WHERE id=?
                    """,
                    (
                        _hash_password(password), role, int(can_discount), int(can_price_change), int(can_return), int(can_reports),
                        int(can_products), int(can_stock), int(can_customers), int(can_suppliers), int(can_cash),
                        int(can_users), int(can_backup), int(can_hardware), int(can_sales_history), user_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE app_users
                    SET role=?,can_discount=?,can_price_change=?,can_return=?,can_reports=?,
                        can_products=?,can_stock=?,can_customers=?,can_suppliers=?,can_cash=?,
                        can_users=?,can_backup=?,can_hardware=?,can_sales_history=?
                    WHERE id=?
                    """,
                    (
                        role, int(can_discount), int(can_price_change), int(can_return), int(can_reports),
                        int(can_products), int(can_stock), int(can_customers), int(can_suppliers), int(can_cash),
                        int(can_users), int(can_backup), int(can_hardware), int(can_sales_history), user_id,
                    ),
                )
            conn.commit()

    def delete_user(self, user_id: int) -> None:
        with self.conn() as conn:
            admin_count = conn.execute("SELECT COUNT(*) FROM app_users WHERE role='ADMIN'").fetchone()[0]
            current_role = (conn.execute("SELECT role FROM app_users WHERE id=?", (user_id,)).fetchone() or ("",))[0]
            if current_role == "ADMIN" and admin_count <= 1:
                raise ValueError("Son admin kullanicisi silinemez")
            conn.execute("DELETE FROM app_users WHERE id=?", (user_id,))
            conn.commit()

    # ── Satış ─────────────────────────────────────────────────────────────────

    def create_sale(
        self,
        cart: list[dict],
        discount: float,
        payment_type: str,
        cash_amount: float,
        card_amount: float,
        transfer_amount: float,
        customer_id: int | None = None,
        is_return: bool = False,
        user_id: int | None = None,
    ) -> float:
        if discount < 0:
            discount = 0.0
        subtotal = sum(item["qty"] * item["price"] for item in cart)
        items_discount = sum(item.get("item_discount", 0.0) for item in cart)
        total = max(0.0, subtotal - items_discount - discount)
        now = _now()
        with self.conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO sales (sale_time,subtotal,discount,total,payment_type,
                    cash_amount,card_amount,transfer_amount,customer_id,is_return,user_id)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (now, subtotal, discount, total, payment_type,
                 cash_amount, card_amount, transfer_amount,
                 customer_id, 1 if is_return else 0, user_id),
            )
            sale_id = cur.lastrowid
            for item in cart:
                line_total = item["qty"] * item["price"] - item.get("item_discount", 0.0)
                cur.execute(
                    """
                    INSERT INTO sale_items
                        (sale_id,product_id,product_name,qty,unit_price,item_discount,vat_rate,line_total)
                    VALUES(?,?,?,?,?,?,?,?)
                    """,
                    (sale_id, item["product_id"], item.get("name", ""),
                     item["qty"], item["price"],
                     item.get("item_discount", 0.0), item.get("vat_rate", 0.0),
                     line_total),
                )
                stock_sign = 1 if is_return else -1
                # Stok kontrolü
                cur_stock = (cur.execute("SELECT stock FROM products WHERE id=?", (item["product_id"],)).fetchone() or (0,))[0]
                new_stock = float(cur_stock or 0) + stock_sign * item["qty"]
                if (not is_return) and new_stock < 0:
                    raise ValueError(f"Yetersiz stok: {item.get('name', 'Urun')}")
                cur.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, item["product_id"]))
                # Stok hareketi kaydet
                move_type = "IN" if is_return else "OUT"
                cur.execute(
                    "INSERT INTO stock_moves (move_time,product_id,product_name,move_type,qty,note) VALUES(?,?,?,?,?,?)",
                    (now, item["product_id"], item.get("name", ""), move_type, item["qty"],
                     "Iade" if is_return else "Satis"),
                )
            # Veresiye bakiye (kısmi ödeme destekli)
            if payment_type == "VERESIYE" and customer_id:
                outstanding = max(0.0, total - float(cash_amount or 0) - float(card_amount or 0) - float(transfer_amount or 0))
                bal_sign = -1 if is_return else 1
                cur.execute("UPDATE customers SET balance=balance+? WHERE id=?", (bal_sign * outstanding, customer_id))
            # Kasa hareketi kaydet (nakit)
            if cash_amount > 0:
                move_type = "OUT" if is_return else "IN"
                cur.execute(
                    "INSERT INTO cash_moves (move_time,move_type,amount,sale_id,note) VALUES(?,?,?,?,?)",
                    (now, move_type, cash_amount, sale_id, "Iade-nakit" if is_return else "Satis-nakit"),
                )
            conn.commit()
        return total

    # ── Satış Hareketleri ─────────────────────────────────────────────────────

    def list_sales_range(self, date_from: str, date_to: str, pay_filter: str = "TUMU", show_returns: bool = False):
        """Tarih aralıklı satış listesi. returns (id,time,pay_type,total,discount,cash,card,transfer,is_return)"""
        with self.conn() as conn:
            where = ["date(sale_time) >= date(?)", "date(sale_time) <= date(?)"]
            params: list = [date_from, date_to]
            if not show_returns:
                where.append("is_return = 0")
            if pay_filter and pay_filter != "TUMU":
                where.append("payment_type = ?")
                params.append(pay_filter)
            sql = f"""
                SELECT id, sale_time, payment_type, total, discount,
                       cash_amount, card_amount, transfer_amount, is_return
                FROM sales
                WHERE {' AND '.join(where)}
                ORDER BY id DESC
            """
            return conn.execute(sql, params).fetchall()

    def list_customer_sales(self, customer_id: int):
        """Bir müşterinin tüm veresiye işlemlerini döndür."""
        with self.conn() as conn:
            return conn.execute(
                """
                SELECT id, sale_time, payment_type, total, discount, is_return
                FROM sales
                WHERE customer_id = ?
                ORDER BY id DESC
                LIMIT 200
                """,
                (customer_id,),
            ).fetchall()

    def get_sale_items(self, sale_id: int):
        """Bir satışın kalemlerini döndür. (product_name,qty,unit_price,item_discount,vat_rate,line_total)"""
        with self.conn() as conn:
            return conn.execute(
                """
                SELECT COALESCE(NULLIF(si.product_name,''), p.name, '(silindi)'),
                       si.qty, si.unit_price, si.item_discount, si.vat_rate, si.line_total
                FROM sale_items si
                LEFT JOIN products p ON p.id = si.product_id
                WHERE si.sale_id = ?
                ORDER BY si.id
                """,
                (sale_id,),
            ).fetchall()

    # ── Kar Raporu ────────────────────────────────────────────────────────────

    def get_profit_report(self, date_from: str, date_to: str):
        """Ürün bazlı kar raporu. (name,qty,total_buy,total_sell,total_profit)"""
        with self.conn() as conn:
            return conn.execute(
                """
                SELECT
                    COALESCE(NULLIF(si.product_name,''), p.name, '(silindi)') pname,
                    COALESCE(SUM(si.qty), 0) qty,
                    COALESCE(SUM(si.qty * COALESCE(p.buy_price, 0)), 0) total_buy,
                    COALESCE(SUM(si.line_total), 0) total_sell,
                    COALESCE(SUM(si.line_total - si.qty * COALESCE(p.buy_price, 0)), 0) profit
                FROM sale_items si
                LEFT JOIN products p ON p.id = si.product_id
                JOIN sales s ON s.id = si.sale_id
                WHERE s.is_return = 0
                  AND date(s.sale_time) >= date(?)
                  AND date(s.sale_time) <= date(?)
                GROUP BY si.product_id, pname
                ORDER BY profit DESC
                """,
                (date_from, date_to),
            ).fetchall()

    # ── Raporlar ──────────────────────────────────────────────────────────────

    def get_report_summary(self, date_from: str = "", date_to: str = ""):
        """date_from / date_to: 'YYYY-MM-DD' formatında, boşsa tüm zamanlar."""
        with self.conn() as conn:
            # Sabit pencereler (bugün / hafta / ay)
            daily = conn.execute(
                """
                SELECT COALESCE(SUM(total),0), COALESCE(SUM(cash_amount),0),
                       COALESCE(SUM(card_amount),0), COALESCE(SUM(transfer_amount),0)
                FROM sales
                WHERE date(sale_time)=date('now','localtime') AND is_return=0
                """
            ).fetchone()
            weekly = conn.execute(
                "SELECT COALESCE(SUM(total),0) FROM sales WHERE sale_time>=datetime('now','localtime','-7 day') AND is_return=0"
            ).fetchone()[0]
            monthly = conn.execute(
                "SELECT COALESCE(SUM(total),0) FROM sales WHERE sale_time>=datetime('now','localtime','-30 day') AND is_return=0"
            ).fetchone()[0]
            return_total = conn.execute(
                "SELECT COALESCE(SUM(total),0) FROM sales WHERE date(sale_time)=date('now','localtime') AND is_return=1"
            ).fetchone()[0]

            # En çok satılan — tarih filtresi uygulanır
            where_parts = ["s.is_return=0"]
            params: list = []
            if date_from:
                where_parts.append("date(s.sale_time) >= ?")
                params.append(date_from)
            if date_to:
                where_parts.append("date(s.sale_time) <= ?")
                params.append(date_to)
            where_clause = " AND ".join(where_parts)

            tops = conn.execute(
                f"""
                SELECT COALESCE(NULLIF(si.product_name,''), p.name, '(silindi)') pname,
                       COALESCE(SUM(si.qty),0) qty
                FROM sale_items si
                LEFT JOIN products p ON p.id=si.product_id
                JOIN sales s ON s.id=si.sale_id
                WHERE {where_clause}
                GROUP BY si.product_id, pname
                ORDER BY qty DESC
                LIMIT 10
                """,
                params,
            ).fetchall()
        return {
            "daily_total": float(daily[0] or 0),
            "daily_cash": float(daily[1] or 0),
            "daily_card": float(daily[2] or 0),
            "daily_transfer": float(daily[3] or 0),
            "weekly_total": float(weekly or 0),
            "monthly_total": float(monthly or 0),
            "return_total": float(return_total or 0),
            "top_products": tops,
        }
