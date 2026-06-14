"""
inject_data.py — prices.json のデータを dashboard.html に埋め込む
scraper.py 実行後に自動で呼ばれます
"""
import json
from pathlib import Path

BASE_DIR   = Path(__file__).parent
DATA_FILE  = BASE_DIR / "data" / "prices.json"
TMPL_FILE  = BASE_DIR / "dashboard_template.html"
OUT_FILE   = BASE_DIR / "dashboard.html"

def inject():
    if not DATA_FILE.exists():
        print("[inject] prices.json が見つかりません")
        return
    if not TMPL_FILE.exists():
        print("[inject] dashboard_template.html が見つかりません")
        return

    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    with open(TMPL_FILE, encoding="utf-8") as f:
        html = f.read()

    json_str = json.dumps(data, ensure_ascii=False)
    html = html.replace("__PRICES_DATA__", json_str)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[inject] dashboard.html を更新しました ({len(data)} GPU)")

if __name__ == "__main__":
    inject()
