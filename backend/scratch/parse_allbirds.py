from bs4 import BeautifulSoup
import json

with open("scratch/allbirds_dump.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

elements = soup.select("div.grid div.bg-white.flex-col")
if elements:
    print(elements[0].prettify()[24000:27000])
