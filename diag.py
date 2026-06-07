# -*- coding: utf-8 -*-
"""诊断2：看中文站文章链接(href+标题)结构，便于写抓取规则。"""
import re
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
H = {"User-Agent": UA}

SITES = {
    "OFweek": "https://fiber.ofweek.com/",
    "ICCSZ":  "http://www.iccsz.com/",
    "C114":   "https://www.c114.com.cn/news/",
}
for name, url in SITES.items():
    try:
        r = requests.get(url, headers=H, timeout=20)
        r.encoding = r.apparent_encoding or "utf-8"
        pairs = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>\s*([一-龥][^<]{7,40})\s*</a>', r.text)
        print(f"=== {name} ({len(pairs)} candidate links) ===")
        seen = set()
        for href, title in pairs:
            title = title.strip()
            if title in seen:
                continue
            seen.add(title)
            print(f"  {href[:70]}  ::  {title}")
            if len(seen) >= 6:
                break
    except Exception as e:
        print(f"[{name}] ERROR {e}")
