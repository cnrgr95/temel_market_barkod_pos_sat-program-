import argparse
import os
import random
import sqlite3
from datetime import datetime


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ean13_checksum(d12: str) -> str:
    digits = "".join(ch for ch in d12 if ch.isdigit())[:12]
    if len(digits) != 12:
        raise ValueError("EAN13 needs 12 digits")
    odd = sum(int(digits[i]) for i in range(0, 12, 2))
    even = sum(int(digits[i]) for i in range(1, 12, 2))
    return str((10 - ((odd + 3 * even) % 10)) % 10)


def _make_barcode(seed: int) -> str:
    base = f"869{seed:09d}"[:12]
    return f"{base}{_ean13_checksum(base)}"


def seed(db_path: str, products: int, customers: int) -> None:
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)

    conn = sqlite3.connect(db_path, timeout=15)
    cur = conn.cursor()

    existing_barcodes = {
        row[0] for row in cur.execute("SELECT barcode FROM products").fetchall() if row and row[0]
    }
    existing_customers = cur.execute("SELECT COUNT(*) FROM customers").fetchone()[0]

    categories = ["Gida", "Temizlik", "Icecek", "Atistirmalik", "Kozmetik"]
    subcats = {
        "Gida": ["Bakliyat", "Unlu", "Sut"],
        "Temizlik": ["Deterjan", "Kagit"],
        "Icecek": ["Meyve", "Gazli"],
        "Atistirmalik": ["Cikolata", "Kraker"],
        "Kozmetik": ["Krem", "Sampuan"],
    }

    added_products = 0
    seed_base = 100000000
    while added_products < products:
        barcode = _make_barcode(seed_base + added_products + 1)
        if barcode in existing_barcodes:
            added_products += 1
            continue
        name = f"Demo Urun {added_products + 1}"
        cat = random.choice(categories)
        sub = random.choice(subcats.get(cat, ["Genel"]))
        buy = round(random.uniform(5, 100), 2)
        sell = round(buy * random.uniform(1.15, 1.6), 2)
        vat = 20.0
        sell_excl = sell / (1 + vat / 100.0)
        stock = round(random.uniform(0, 200), 2)
        critical = round(random.uniform(3, 15), 2)

        cur.execute(
            """
            INSERT INTO products (
                name, barcode, description, category, sub_category, unit, buy_price,
                sell_price_excl_vat, sell_price_incl_vat, vat_rate, vat_mode,
                stock, critical_stock, image_path, is_scale_product, supplier_id, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                name,
                barcode,
                "",
                cat,
                sub,
                "adet",
                buy,
                sell_excl,
                sell,
                vat,
                "INCL",
                stock,
                critical,
                "",
                0,
                None,
                _now(),
            ),
        )
        product_id = cur.lastrowid
        if stock > 0:
            cur.execute(
                "INSERT INTO stock_moves (move_time,product_id,product_name,move_type,qty,note) VALUES(?,?,?,?,?,?)",
                (_now(), product_id, name, "IN", stock, "Demo stok"),
            )
        existing_barcodes.add(barcode)
        added_products += 1

    added_customers = 0
    start_idx = existing_customers + 1
    for i in range(customers):
        idx = start_idx + i
        name = f"Demo Musteri {idx}"
        phone = f"05{random.randint(10, 99)}{random.randint(1000000, 9999999)}"
        address = f"Demo Adres {idx}"
        email = f"demo{idx}@example.com"
        cur.execute(
            "INSERT INTO customers (name,phone,address,email,balance,notes,created_at) VALUES(?,?,?,?,0,?,?)",
            (name, phone, address, email, "", _now()),
        )
        added_customers += 1

    conn.commit()
    conn.close()

    print(f"Added products: {added_products}")
    print(f"Added customers: {added_customers}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="market.db")
    parser.add_argument("--products", type=int, default=500)
    parser.add_argument("--customers", type=int, default=100)
    args = parser.parse_args()
    seed(args.db, args.products, args.customers)
