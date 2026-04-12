import html
import random


_LEFT_PARITY = {
    "0": "LLLLLL",
    "1": "LLGLGG",
    "2": "LLGGLG",
    "3": "LLGGGL",
    "4": "LGLLGG",
    "5": "LGGLLG",
    "6": "LGGGLL",
    "7": "LGLGLG",
    "8": "LGLGGL",
    "9": "LGGLGL",
}

_L_CODES = {
    "0": "0001101",
    "1": "0011001",
    "2": "0010011",
    "3": "0111101",
    "4": "0100011",
    "5": "0110001",
    "6": "0101111",
    "7": "0111011",
    "8": "0110111",
    "9": "0001011",
}

_G_CODES = {
    "0": "0100111",
    "1": "0110011",
    "2": "0011011",
    "3": "0100001",
    "4": "0011101",
    "5": "0111001",
    "6": "0000101",
    "7": "0010001",
    "8": "0001001",
    "9": "0010111",
}

_R_CODES = {
    "0": "1110010",
    "1": "1100110",
    "2": "1101100",
    "3": "1000010",
    "4": "1011100",
    "5": "1001110",
    "6": "1010000",
    "7": "1000100",
    "8": "1001000",
    "9": "1110100",
}


def sanitize_digits(value: str | None) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def checksum(d12: str) -> int:
    d12 = sanitize_digits(d12)[:12]
    if len(d12) != 12:
        raise ValueError("EAN-13 checksum requires 12 digits")
    odd = sum(int(d12[i]) for i in range(0, 12, 2))
    even = sum(int(d12[i]) for i in range(1, 12, 2))
    return (10 - ((odd + 3 * even) % 10)) % 10


def is_valid_ean13(barcode: str | None) -> bool:
    digits = sanitize_digits(barcode)
    return len(digits) == 13 and digits[-1] == str(checksum(digits[:12]))


def complete_ean13(value: str | None, default_prefix: str = "869") -> str:
    digits = sanitize_digits(value)
    if len(digits) == 13:
        if not is_valid_ean13(digits):
            raise ValueError("Gecersiz EAN-13 barkodu")
        return digits
    if len(digits) == 12:
        return f"{digits}{checksum(digits)}"
    if len(digits) > 12:
        digits = digits[:12]
    if not digits:
        digits = sanitize_digits(default_prefix) or "869"
    if len(digits) > 12:
        digits = digits[:12]
    return generate_ean13(digits)


def generate_ean13(prefix: str = "869") -> str:
    prefix = sanitize_digits(prefix)
    if not prefix:
        prefix = "869"
    if len(prefix) > 12:
        prefix = prefix[:12]
    d12 = prefix + "".join(str(random.randint(0, 9)) for _ in range(12 - len(prefix)))
    return f"{d12}{checksum(d12)}"


def ean13_pattern(digits: str) -> str:
    first = digits[0]
    left_digits = digits[1:7]
    right_digits = digits[7:]
    parity = _LEFT_PARITY[first]

    bits = ["101"]
    for idx, digit in enumerate(left_digits):
        bits.append(_L_CODES[digit] if parity[idx] == "L" else _G_CODES[digit])
    bits.append("01010")
    for digit in right_digits:
        bits.append(_R_CODES[digit])
    bits.append("101")
    return "".join(bits)


def ean13_svg(
    barcode: str,
    module_width: int = 2,
    bar_height: int = 72,
    font_size: int = 15,
    fg_color: str = "#111827",
    bg_color: str = "#ffffff",
) -> str:
    digits = sanitize_digits(barcode)
    if len(digits) == 12:
        digits = f"{digits}{checksum(digits)}"
    elif len(digits) == 13:
        if not is_valid_ean13(digits):
            raise ValueError("Gecersiz EAN-13 barkodu")
    else:
        raise ValueError("EAN-13 icin 12 veya 13 haneli barkod gereklidir")

    bits = ean13_pattern(digits)
    width = len(bits) * module_width
    guard_height = bar_height + 8
    text_y = guard_height + font_size + 2
    svg_height = text_y + 6

    rects: list[str] = []
    x = 0
    for idx, bit in enumerate(bits):
        if bit == "1":
            in_start = idx < 3
            in_center = 45 <= idx < 50
            in_end = idx >= len(bits) - 3
            height = guard_height if (in_start or in_center or in_end) else bar_height
            rects.append(
                f'<rect x="{x}" y="0" width="{module_width}" height="{height}" fill="{fg_color}" />'
            )
        x += module_width

    safe_digits = html.escape(digits)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{svg_height}" '
        f'viewBox="0 0 {width} {svg_height}" role="img" aria-label="EAN13 {safe_digits}">'
        f'<rect width="{width}" height="{svg_height}" fill="{bg_color}" />'
        f'{"".join(rects)}'
        f'<text x="{width / 2:.1f}" y="{text_y}" font-family="Arial, sans-serif" font-size="{font_size}" '
        f'text-anchor="middle" fill="{fg_color}" letter-spacing="1">{safe_digits}</text>'
        f"</svg>"
    )
