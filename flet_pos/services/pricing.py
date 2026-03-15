def compute_prices(base_price: float, vat_rate: float, vat_mode: str) -> tuple[float, float]:
    ratio = 1 + (vat_rate / 100.0)
    if ratio <= 0:
        ratio = 1
    if vat_mode == "EXCL":
        excl = base_price
        incl = base_price * ratio
    else:
        incl = base_price
        excl = base_price / ratio
    return round(excl, 4), round(incl, 4)
