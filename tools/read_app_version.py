from pathlib import Path
import re


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    app_path = root / "flet_pos" / "app.py"
    text = app_path.read_text(encoding="utf-8")
    match = re.search(r'APP_VERSION\s*=\s*"V\s*([0-9.]+)"', text)
    if not match:
        return 1
    print(match.group(1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
