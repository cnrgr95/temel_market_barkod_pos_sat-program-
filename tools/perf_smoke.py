import argparse
import sqlite3
import time


def _timeit(label, fn, repeat=5):
    times = []
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        times.append(time.perf_counter() - start)
    avg = sum(times) / len(times)
    print(f"{label}: {avg*1000:.2f} ms avg ({repeat} runs)")


def run(db_path: str):
    conn = sqlite3.connect(db_path, timeout=15)

    def list_products():
        conn.execute(
            """
            SELECT id, name, barcode, unit, sell_price_incl_vat, vat_rate,
                   stock, image_path, is_scale_product, critical_stock, category, sub_category
            FROM products
            WHERE COALESCE(is_active,1)=1
            ORDER BY name
            """
        ).fetchall()

    def list_customers():
        conn.execute("SELECT id, name, phone, address, balance FROM customers ORDER BY name").fetchall()

    def list_stock_moves():
        conn.execute(
            """
            SELECT move_time, product_id, move_type, qty, note
            FROM stock_moves
            ORDER BY id DESC
            LIMIT 500
            """
        ).fetchall()

    _timeit("list_products", list_products)
    _timeit("list_customers", list_customers)
    _timeit("list_stock_moves", list_stock_moves)

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="market.db")
    args = parser.parse_args()
    run(args.db)
