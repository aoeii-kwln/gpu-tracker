"""
GPU Price Tracker - Multi-source scraper
Sources: kakaku.com, ドスパラ, ツクモ, ユニットコム, Joshin Web, Amazon.co.jp, ソフマップ
"""

import json
import os
import re
import time
import logging
import smtplib
import traceback
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests
from bs4 import BeautifulSoup



# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
DATA_FILE  = BASE_DIR / "data" / "prices.json"
LOG_FILE   = BASE_DIR / "logs" / "scraper.log"

EMAIL_TO   = "weilahm@gmail.com"
EMAIL_FROM = "weilahm@gmail.com"          # Gmail address used as sender
# ↓ Generate at https://myaccount.google.com/apppasswords  (2FA required)
EMAIL_APP_PASSWORD = "YOUR_GMAIL_APP_PASSWORD"

PRICE_CHANGE_THRESHOLD = 0.03   # 3% = trigger pick-up

# 正規代理店ホワイトリスト — 並行輸入/マーケットプレイス系を除外
AUTHORIZED_RETAILERS = [
    "TSUKUMO", "ツクモ",
    "パソコン工房", "PCワンズ",
    "ソフマップ", "ソフマップ.com",
    "Amazon.co.jp", "Amazon",
    "コジマネット", "コジマ",
    "ビックカメラ.com", "ビックカメラ",
    "ヨドバシ.com", "ヨドバシ",
    "ヤマダウェブコム", "ヤマダ電機",
    "ドスパラ", "Dospara",
    "Joshin", "ジョーシン",
    "ノジマ",
    "エディオン",
    "ケーズデンキ",
]

def is_authorized_retailer(shop_name: str) -> bool:
    """Check if shop name matches the authorized retailer whitelist."""
    return any(r in shop_name for r in AUTHORIZED_RETAILERS)

# GPU models to track
GPU_MODELS = {
    # NVIDIA RTX 50 Series
    "RTX 5090":       {"kakaku_url": "https://kakaku.com/pc/videocard/itemlist.aspx?pdf_Spec103=500",                          "series": "RTX50", "vendor": "NVIDIA"},
    "RTX 5080":       {"kakaku_url": "https://kakaku.com/pc/videocard/itemlist.aspx?pdf_Spec103=499",                          "series": "RTX50", "vendor": "NVIDIA"},
    "RTX 5070 Ti":    {"kakaku_url": "https://kakaku.com/pc/videocard/itemlist.aspx?pdf_Spec103=501",                          "series": "RTX50", "vendor": "NVIDIA"},
    "RTX 5070":       {"kakaku_url": "https://kakaku.com/pc/videocard/itemlist.aspx?pdf_Spec103=502",                          "series": "RTX50", "vendor": "NVIDIA"},
    "RTX 5060 Ti 16G":{"kakaku_url": "https://kakaku.com/pc/videocard/itemlist.aspx?pdf_Spec103=503&pdf_Spec301=16384",        "series": "RTX50", "vendor": "NVIDIA"},
    "RTX 5060 Ti 8G": {"kakaku_url": "https://kakaku.com/pc/videocard/itemlist.aspx?pdf_Spec103=503&pdf_Spec301=8192",         "series": "RTX50", "vendor": "NVIDIA"},
    "RTX 5060":       {"kakaku_url": "https://kakaku.com/pc/videocard/itemlist.aspx?pdf_Spec103=504",                          "series": "RTX50", "vendor": "NVIDIA"},
    # AMD RX 9000 Series
    "RX 9070 XT":     {"kakaku_url": "https://kakaku.com/pc/videocard/itemlist.aspx?pdf_Spec112=106",                          "series": "RX9000", "vendor": "AMD"},
    "RX 9070":        {"kakaku_url": "https://kakaku.com/pc/videocard/itemlist.aspx?pdf_Spec112=107",                          "series": "RX9000", "vendor": "AMD"},
    "RX 9060 XT 16G": {"kakaku_url": "https://kakaku.com/pc/videocard/itemlist.aspx?pdf_Spec112=108&pdf_Spec301=16384",        "series": "RX9000", "vendor": "AMD"},
    "RX 9060 XT 8G":  {"kakaku_url": "https://kakaku.com/pc/videocard/itemlist.aspx?pdf_Spec112=108&pdf_Spec301=8192",         "series": "RX9000", "vendor": "AMD"},
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────
def get(url: str, **kwargs) -> requests.Response:
    resp = requests.get(url, headers=HEADERS, timeout=20, **kwargs)
    resp.raise_for_status()
    return resp


def clean_price(text: str) -> int | None:
    """Extract integer yen price from a string like '¥123,456' → 123456."""
    nums = re.sub(r"[^\d]", "", text)
    return int(nums) if nums else None


def load_data() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_data(data: dict):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Scrapers ──────────────────────────────────────────────────────────────────


def scrape_kakaku_models(gpu_name: str, url: str) -> list[dict]:
    """Kakaku.com — fetch all model listings with release date for new product detection."""
    results = []
    try:
        soup = BeautifulSoup(get(url).text, "html.parser")
        items = {}

        for a in soup.select("a[href*='/item/K']"):
            href = a.get("href", "")
            if not href:
                continue
            full_url = href if href.startswith("http") else f"https://kakaku.com{href}"
            text = a.get_text(strip=True)

            if full_url not in items:
                items[full_url] = {"name": "", "maker": "—", "price": None, "url": full_url}

            if text.startswith("¥") or text.startswith("￥"):
                price = clean_price(text)
                if price and price > 10000:
                    items[full_url]["price"] = price
            elif len(text) > 8:
                if not items[full_url]["name"]:
                    maker = "—"
                    model_name = text
                    for m in ["MSI", "ASUS", "ZOTAC", "GIGABYTE", "Palit Microsystems",
                              "Palit", "ASRock", "SAPPHIRE", "玄人志向", "GAINWARD",
                              "PNY", "INNO3D", "Colorful", "PowerColor", "XFX", "ELSA"]:
                        if text.startswith(m):
                            maker = m
                            model_name = text[len(m):].strip()
                            break
                    items[full_url]["maker"] = maker
                    items[full_url]["name"] = model_name[:80]

        # Extract release dates from swdate1 cells (登録日)
        # Each product row's date is in td.swdate1
        release_dates = {}
        for td in soup.select("td.swdate1"):
            date_text = td.get_text(strip=True)  # e.g. "2025/2/21"
            # Find the nearest item link in the same ancestor
            row = td.find_parent("tr")
            if row:
                a = row.find("a", href=re.compile(r"/item/K"))
                if a:
                    href = a.get("href", "")
                    full_url = href if href.startswith("http") else f"https://kakaku.com{href}"
                    try:
                        # normalize to YYYY-MM-DD
                        parts = date_text.replace("　","").split("/")
                        if len(parts) == 3:
                            release_dates[full_url] = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                    except Exception:
                        pass

        for item in items.values():
            if item["name"] and item["price"] and item["price"] > 10000:
                item_url = item["url"]
                results.append({
                    "maker":        item["maker"],
                    "name":         item["name"],
                    "price":        item["price"],
                    "url":          item_url,
                    "source":       "kakaku",
                    "release_date": release_dates.get(item_url, ""),
                })

        results.sort(key=lambda x: x["price"])
        log.info(f"  kakaku models [{gpu_name}]: {len(results)} models found")
    except Exception as e:
        log.warning(f"kakaku_models [{gpu_name}]: {e}")
    return results



def fetch_authorized_price(item_url: str) -> tuple[int | None, str | None]:
    """Fetch the lowest price among AUTHORIZED_RETAILERS only, from item detail page.
    Returns (price, shop_name) or (None, None) if no authorized shop found.
    """
    try:
        resp = get(item_url)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")

        items = soup.select("li.p-priceList_item")
        best_price = None
        best_shop = None

        for item in items:
            shop_el = item.select_one(".p-priceList_shopName")
            if not shop_el:
                continue
            shop_name = shop_el.get_text(strip=True)

            if not is_authorized_retailer(shop_name):
                continue

            price_el = item.select_one(".p-priceList_priceMain")
            if not price_el:
                continue
            price = clean_price(price_el.get_text())
            if not price or price < 10000:
                continue

            if best_price is None or price < best_price:
                best_price = price
                best_shop = shop_name

        return best_price, best_shop
    except Exception as e:
        log.warning(f"fetch_authorized_price [{item_url}]: {e}")
        return None, None



def scrape_all() -> dict[str, dict]:
    """Run all scrapers for each GPU model, fetching authorized-retailer prices."""
    results = {}
    for gpu_name, meta in GPU_MODELS.items():
        log.info(f"Scraping: {gpu_name}")
        kakaku_url = meta["kakaku_url"]

        models = scrape_kakaku_models(gpu_name, kakaku_url)
        time.sleep(1.0)

        # For each model, fetch the authorized-retailer-only price
        authorized_models = []
        for i, model in enumerate(models):
            auth_price, auth_shop = fetch_authorized_price(model["url"])
            time.sleep(1.0)
            if auth_price:
                model["price"] = auth_price
                model["source"] = auth_shop
                authorized_models.append(model)
            # else: skip — no authorized retailer carries this model
            if (i + 1) % 10 == 0:
                log.info(f"    ...{i+1}/{len(models)} 件処理済み")

        authorized_models.sort(key=lambda x: x["price"])
        log.info(f"  正規代理店モデル数 [{gpu_name}]: {len(authorized_models)}/{len(models)}")

        source_prices = {}
        if authorized_models:
            kakaku_price = authorized_models[0]["price"]
            source_prices["kakaku"] = kakaku_price
            log.info(f"  kakaku (正規代理店最安): ¥{kakaku_price:,}")

        results[gpu_name] = {"sources": source_prices, "models": authorized_models}
    return results



def compute_min_price(source_prices: dict) -> int | None:
    vals = [v for v in source_prices.values() if v]
    return min(vals) if vals else None


def detect_events(old_data: dict, new_entry: dict, gpu_name: str, today: str) -> list[dict]:
    """Return list of event dicts (price_change / new_model)."""
    events = []
    new_min = compute_min_price(new_entry.get("sources", {}))
    if new_min is None:
        return events

    gpu_history = old_data.get(gpu_name, {}).get("history", [])

    # New model — first time we see this GPU with a price
    if not gpu_history:
        events.append({
            "type":  "new_model",
            "date":  today,
            "price": new_min,
            "label": f"🆕 {gpu_name} が初めて検出されました (¥{new_min:,})",
        })
        return events

    # Price change
    last_prices = [
        e["min_price"] for e in gpu_history
        if e.get("min_price")
    ]
    if last_prices:
        prev = last_prices[-1]
        change = (new_min - prev) / prev
        if abs(change) >= PRICE_CHANGE_THRESHOLD:
            direction = "↗ 値上がり" if change > 0 else "↘ 値下がり"
            pct = f"{change:+.1%}"
            events.append({
                "type":    "price_change",
                "date":    today,
                "prev":    prev,
                "current": new_min,
                "change":  pct,
                "label":   f"{direction} {gpu_name}  {pct}  ¥{prev:,} → ¥{new_min:,}",
            })
    return events


def send_email(subject: str, body_html: str):
    if EMAIL_APP_PASSWORD == "YOUR_GMAIL_APP_PASSWORD":
        log.warning("Email not configured — skipping notification.")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = EMAIL_FROM
        msg["To"]      = EMAIL_TO
        msg.attach(MIMEText(body_html, "html", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_FROM, EMAIL_APP_PASSWORD)
            smtp.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        log.info(f"Email sent → {EMAIL_TO}")
    except Exception as e:
        log.error(f"Email failed: {e}")


def build_email_html(events: list[dict], today: str) -> str:
    rows = ""
    for ev in events:
        icon  = "🆕" if ev["type"] == "new_model" else ("📈" if "↗" in ev["label"] else "📉")
        rows += f"<tr><td>{icon}</td><td>{ev['label']}</td><td>{ev['date']}</td></tr>"
    return f"""
<html><body style="font-family:sans-serif;background:#0d1117;color:#e6edf3;padding:24px">
<h2 style="color:#58a6ff">GPU Price Tracker — {today} アップデート</h2>
<table border="0" cellpadding="8" style="border-collapse:collapse;width:100%">
  <thead>
    <tr style="background:#161b22;color:#8b949e;font-size:12px">
      <th></th><th align="left">内容</th><th align="left">日付</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
<p style="color:#8b949e;font-size:12px;margin-top:24px">
  GPU Price Tracker — 自動送信メール
</p>
</body></html>
"""


def run():
    today     = datetime.now().strftime("%Y-%m-%d")
    old_data  = load_data()
    new_scrape = scrape_all()

    all_events = []

    for gpu_name in new_scrape:
        source_prices = new_scrape[gpu_name].get("sources", {})
        models = new_scrape[gpu_name].get("models", [])
        min_price = compute_min_price(source_prices)

        new_entry = {
            "date":      today,
            "min_price": min_price,
            "sources":   source_prices,
            "models":    models,
        }

        # Detect events before updating
        events = detect_events(old_data, new_entry, gpu_name, today)
        all_events.extend(events)

        # Merge into data store
        if gpu_name not in old_data:
            old_data[gpu_name] = {
                "meta":    GPU_MODELS[gpu_name],
                "history": [],
                "events":  [],
            }

        # Avoid duplicate entries for the same date
        existing_dates = {e["date"] for e in old_data[gpu_name]["history"]}
        if today not in existing_dates:
            old_data[gpu_name]["history"].append(new_entry)

        old_data[gpu_name]["events"].extend(events)

    # Preserve ALL existing GPU data (including old key names)
    # Only update/add GPUs that were scraped today
    final_data = load_data()  # reload fresh to be safe
    for gpu_name, gpu_data in old_data.items():
        final_data[gpu_name] = gpu_data

    save_data(final_data)
    log.info(f"Data saved. {len(all_events)} event(s) detected.")

    # Inject data into dashboard.html
    try:
        from inject_data import inject
        inject()
    except Exception as e:
        log.warning(f"dashboard inject failed: {e}")

    # Email notification
    if all_events:
        subject = f"[GPU Tracker] {today} — {len(all_events)}件の変動を検出"
        html    = build_email_html(all_events, today)
        send_email(subject, html)
    else:
        log.info("No significant events — no email sent.")

    # Auto push to GitHub Pages
    try:
        import subprocess
        subprocess.run(["git", "add", "data/prices.json", "dashboard.html"], cwd=BASE_DIR, check=True)
        subprocess.run(["git", "commit", "-m", f"auto update {today}"], cwd=BASE_DIR, check=True)
        subprocess.run(["git", "push"], cwd=BASE_DIR, check=True)
        log.info("GitHub Pages updated successfully.")
    except Exception as e:
        log.warning(f"GitHub push failed: {e}")


if __name__ == "__main__":
    try:
        run()
    except Exception:
        log.error(traceback.format_exc())
