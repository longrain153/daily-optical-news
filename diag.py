# -*- coding: utf-8 -*-
"""诊断：中文站文章 URL 是否含日期（用于过滤旧闻）。"""
import re
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
H = {"User-Agent": UA}
SITES = {
    "OFweek": ("https://fiber.ofweek.com/", "https://fiber.ofweek.com"),
    "ICCSZ":  ("http://www.iccsz.com/", "http://www.iccsz.com"),
    "C114":   ("https://www.c114.com.cn/news/", "https://www.c114.com.cn"),
}
for name, (url, base) in SITES.items():
    try:
        r = requests.get(url, headers=H, timeout=20)
        r.encoding = r.apparent_encoding or "utf-8"
        print(f"=== {name} ===")
        seen = set()
        for href, title in re.findall(
                r'<a[^>]+href="([^"]+)"[^>]*>\s*([一-龥][^<]{7,40})\s*</a>', r.text):
            title = title.strip()
            if title in seen:
                continue
            seen.add(title)
            full = href if href.startswith("http") else (("https:" + href) if href.startswith("//") else base + href)
            # 找 URL 里的日期样式
            dm = re.search(r"(20\d{2})[-/_]?(\d{2})[-/_]?(\d{2})|/(20\d{2})[-/](\d{2})/", full)
            print(f"  {full[:85]}")
            if len(seen) >= 10:
                break
    except Exception as e:
        print(f"[{name}] ERROR {e}")
