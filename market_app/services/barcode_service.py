import random


def ean13_checksum(first_12_digits: str) -> int:
    if len(first_12_digits) != 12 or not first_12_digits.isdigit():
        raise ValueError("EAN-13 icin ilk 12 hane sayisal olmali.")

    odd_sum = sum(int(first_12_digits[i]) for i in range(0, 12, 2))
    even_sum = sum(int(first_12_digits[i]) for i in range(1, 12, 2))
    total = odd_sum + (even_sum * 3)
    return (10 - (total % 10)) % 10


def generate_ean13(prefix: str = "869") -> str:
    if not prefix.isdigit():
        raise ValueError("Prefix sayisal olmali.")
    if len(prefix) >= 12:
        first_12 = prefix[:12]
    else:
        remaining = 12 - len(prefix)
        first_12 = prefix + "".join(str(random.randint(0, 9)) for _ in range(remaining))
    check = ean13_checksum(first_12)
    return f"{first_12}{check}"
