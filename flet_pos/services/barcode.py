import random


def _checksum(d12: str) -> int:
    odd = sum(int(d12[i]) for i in range(0, 12, 2))
    even = sum(int(d12[i]) for i in range(1, 12, 2))
    return (10 - ((odd + 3 * even) % 10)) % 10


def generate_ean13(prefix: str = "869") -> str:
    prefix = "".join(ch for ch in prefix if ch.isdigit())
    if not prefix:
        prefix = "869"
    if len(prefix) > 12:
        prefix = prefix[:12]
    d12 = prefix + "".join(str(random.randint(0, 9)) for _ in range(12 - len(prefix)))
    return f"{d12}{_checksum(d12)}"
