"""
test_5090_only.py — RTX 5090のみで正規代理店価格取得をテスト
"""
import requests
from bs4 import BeautifulSoup
import re
import time

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

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

def is_authorized_retailer(shop_name):
    return any(r in shop_name for r in AUTHORIZED_RETAILERS)

def clean_price(text):
    nums = re.sub(r"[^\d]", "", text)
    return int(nums) if nums and 4 <= len(nums) <= 8 else None

def get(url):
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp

def fetch_authorized_price(item_url):
    try:
        resp = get(item_url)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("li.p-priceList_item")
        best_price = None
        best_shop = None
        all_shops = []
        for item in items:
            shop_el = item.select_one(".p-priceList_shopName")
            if not shop_el:
                continue
            shop_name = shop_el.get_text(strip=True)
            price_el = item.select_one(".p-priceList_priceMain")
            price = clean_price(price_el.get_text()) if price_el else None
            all_shops.append((shop_name, price, is_authorized_retailer(shop_name)))
            if not is_authorized_retailer(shop_name) or not price or price < 10000:
                continue
            if best_price is None or price < best_price:
                best_price = price
                best_shop = shop_name
        return best_price, best_shop, all_shops
    except Exception as e:
        print(f"  ERROR: {e}")
        return None, None, []

# Step 1: get model list for RTX 5090
url = "https://kakaku.com/pc/videocard/itemlist.aspx?pdf_Spec103=500"
resp = get(url)
soup = BeautifulSoup(resp.text, "html.parser")

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

models = [v for v in items.values() if v["name"] and v["price"]]
models.sort(key=lambda x: x["price"])

print(f"RTX 5090 モデル数: {len(models)}\n")

# Step 2: for first 5 models, fetch authorized price
for i, model in enumerate(models[:5]):
    print(f"--- モデル {i+1}: {model['maker']} {model['name'][:50]} ---")
    print(f"  kakaku一覧価格: ¥{model['price']:,}")
    auth_price, auth_shop, all_shops = fetch_authorized_price(model["url"])
    print(f"  正規代理店最安: ¥{auth_price:,} ({auth_shop})" if auth_price else "  正規代理店: 見つかりませんでした")
    print(f"  全ショップ一覧:")
    for shop_name, price, is_auth in all_shops[:8]:
        mark = "✓" if is_auth else "✗"
        print(f"    {mark} {shop_name}: ¥{price:,}" if price else f"    {mark} {shop_name}: —")
    print()
    time.sleep(1.5)

print("=== テスト完了 ===")
