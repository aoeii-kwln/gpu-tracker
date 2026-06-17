"""
test_item_page.py — kakaku個別商品ページの「すべてのショップで価格を比較」構造調査
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
print(f"Status: {resp.status_code}  Length: {len(resp.text)}")

soup = BeautifulSoup(resp.text, "html.parser")

# Search for shop names + prices
shop_keywords = ["TSUKUMO", "ツクモ", "パソコン工房", "ソフマップ", "Amazon",
                  "コジマ", "ビックカメラ", "ヤマダ", "ヨドバシ", "ドスパラ"]

print("\n=== ショップ名を含む要素 ===")
found_shops = set()
for tag in soup.find_all(True):
    text = tag.get_text(strip=True)
    for shop in shop_keywords:
        if shop in text and len(text) < 30:
            cls = ".".join(tag.get("class", []))
            print(f"  {tag.name}.{cls}: {text[:40]}")
            found_shops.add(shop)
            break

print(f"\n見つかったショップ: {found_shops}")

# Search for price table structure
print("\n=== 価格を含む行構造（最初の5件）===")
price_re = re.compile(r'\d{2,3},\d{3}')
count = 0
for tag in soup.find_all(["tr", "li", "div"]):
    text = tag.get_text(separator="|", strip=True)
    if price_re.search(text) and any(shop in text for shop in shop_keywords):
        cls = ".".join(tag.get("class", []))
        print(f"\n{tag.name}.{cls}:")
        print(f"  {text[:150]}")
        count += 1
        if count >= 5:
            break
