from bs4 import BeautifulSoup

with open("scratch/rs_online_dump.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

import sys
import os
# Ensure app module is in path
sys.path.insert(0, os.path.abspath('.'))

from app.core.httpx_scraper import _get_selectors, _extract_products

url = "https://uk.rs-online.com/web/c/site-safety/first-aid"
selectors = _get_selectors(url)
print("Detected Selectors:", selectors)

products = _extract_products(soup.prettify(), url, selectors)
print(f"Extracted {len(products)} products:")
for p in products[:5]:
    print(p)
