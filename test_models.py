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

url = "https://kakaku.com/pc/videocard/itemlist.aspx?pdf_Spec103=500"
resp = requests.get(url, headers=headers, timeout=20)
soup = BeautifulSoup(resp.text, "html.parser")

all_links = soup.select("a[href*='/item/K']")
print(f"全 /item/K リンク数: {len(all_links)}")

# 各リンクのテキストと価格を詳しく確認
items = {}
for a in all_links:
    href = a.get("href", "")
    full_url = href if href.startswith("http") else f"https://kakaku.com{href}"
    text = a.get_text(strip=True)

    if full_url not in items:
        items[full_url] = {"texts": []}
    items[full_url]["texts"].append(text)

print(f"\nユニークなアイテムURL数: {len(items)}")
print("\n最初の3アイテムの全テキスト:")
for url_key, data in list(items.items())[:3]:
    print(f"\n  URL: {url_key[-30:]}")
    for t in data["texts"]:
        price = clean_price(t)
        print(f"    テキスト: {repr(t[:60])}  → 価格判定: {price}")
