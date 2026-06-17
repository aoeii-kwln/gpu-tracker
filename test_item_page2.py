"""
test_item_page2.py — p-priceList_item の正確な構造を解析
"""
import requests
from bs4 import BeautifulSoup
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def clean_price(text):
    nums = re.sub(r"[^\d]", "", text)
    return int(nums) if nums and 4 <= len(nums) <= 8 else None

url = "https://kakaku.com/item/K0001679747/"
resp = requests.get(url, headers=headers, timeout=20)
resp.encoding = resp.apparent_encoding  # fix encoding
soup = BeautifulSoup(resp.text, "html.parser")

items = soup.select("li.p-priceList_item")
print(f"p-priceList_item の数: {len(items)}")

for i, item in enumerate(items[:5]):
    print(f"\n--- ショップ {i+1} ---")

    shop_name_el = item.select_one(".p-priceList_shopName")
    shop_name = shop_name_el.get_text(strip=True) if shop_name_el else "?"
    print(f"  ショップ名: {shop_name}")

    # Price
    price_el = item.select_one("[class*='price'], [class*='Price']")
    all_classes_with_price = item.select("[class*='rice']")
    for el in all_classes_with_price[:3]:
        cls = ".".join(el.get("class", []))
        text = el.get_text(strip=True)
        print(f"  {el.name}.{cls}: {text[:60]}")

    # Full text dump for this item
    full_text = item.get_text(separator=" | ", strip=True)
    print(f"  全文: {full_text[:200]}")
