# -*- coding: utf-8 -*-
"""诊断：中文光通信源(讯石/C114/OFweek)从 GitHub 海外 runner 是否可达 + 有无 RSS/可抓。"""
import re
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
H = {"User-Agent": UA}

CANDS = {
    "C114-home":   "https://www.c114.com.cn/",
    "C114-rss":    "http://www.c114.com.cn/rss/",
    "OFweek-fiber":"https://fiber.ofweek.com/",
    "OFweek-rss":  "http://rss.ofweek.com/fiber.xml",
    "ICCSZ-home":  "http://www.iccsz.com/",
    "ICCSZ-rss":   "http://www.iccsz.com/rss.aspx",
    "C114-news":   "https://www.c114.com.cn/news/",
}

for tag, url in CANDS.items():
    try:
        r = requests.get(url, headers=H, timeout=20)
        r.encoding = r.apparent_encoding or "utf-8"
        t = r.text
        items = len(re.findall(r"<item\b", t, re.I))
        # 抓几个像标题的中文链接文本
        titles = re.findall(r'<a[^>]+href="[^"]*"[^>]*>([一-龥]{6,40})</a>', t)
        print(f"[{tag}] HTTP {r.status_code} len={len(t)} rssItems={items} 中文链接样例={titles[:3]}")
    except Exception as e:
        print(f"[{tag}] ERROR {type(e).__name__}: {str(e)[:80]}")
    print("-" * 55)
