# -*- coding: utf-8 -*-
"""
光通信行业每日简报 - 云端版（GitHub Actions）
聚焦：光传输 / 光模块 / AI光互联 / 光器件芯片 / 卫星光通信 / 量子光通信。
流程：抓行业外媒 RSS -> DeepSeek 按细分归类+翻译成中文+解读 -> 生成HTML -> 邮件 + GitHub Pages。
"""
import os
import re
import json
import time
import smtplib
import datetime as dt
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr

import requests

BJ = dt.timezone(dt.timedelta(hours=8))

# 数据源（英文行业/科技 RSS，海外可达；内容来自 feed，截图为独立尽力而为）
FEEDS = [
    ("The Next Platform", "https://www.nextplatform.com/feed/"),
    ("Light Reading", "https://www.lightreading.com/rss.xml"),
    ("Fierce Network", "https://www.fierce-network.com/rss.xml"),
    ("DataCenterDynamics", "https://www.datacenterdynamics.com/en/rss/"),
]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# 中文光通信源（无 RSS，抓 HTML 列表页；覆盖光模块/卫星/量子/中国厂家/资本市场）
# 用户在国内可直接访问这些链接，故中文源条目不截图。
CN_FEEDS = [
    ("OFweek光通讯", "https://fiber.ofweek.com/", "https://fiber.ofweek.com"),
    ("讯石光通讯", "http://www.iccsz.com/", "http://www.iccsz.com"),
    ("C114通信网", "https://www.c114.com.cn/news/", "https://www.c114.com.cn"),
]
_CN_SKIP_KW = ["返回", "首页", "行业会议", "线上会议", "回放", "预约", "登录",
               "注册", "更多", "专题", "会展", "策划", "热点"]


def beijing_now():
    return dt.datetime.now(BJ)


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s or "").replace("&nbsp;", " ").strip()


# ----------------------------------------------------------------------------
# 1. 抓取 RSS 文章
# ----------------------------------------------------------------------------
def fetch_articles():
    items = []
    for name, url in FEEDS:
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=25)
            blocks = re.findall(r"<item\b.*?>(.*?)</item>", r.text, re.S | re.I)
            if not blocks:
                blocks = re.findall(r"<entry\b.*?>(.*?)</entry>", r.text, re.S | re.I)
            for b in blocks[:40]:
                def grab(tag):
                    m = re.search(rf"<{tag}\b[^>]*>(.*?)</{tag}>", b, re.S | re.I)
                    if not m:
                        return ""
                    v = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", m.group(1), flags=re.S)
                    return v.strip()
                title = strip_tags(grab("title"))
                link = strip_tags(grab("link")) or strip_tags(grab("guid"))
                summary = strip_tags(grab("description") or grab("summary"))
                if title and link:
                    items.append({"source": name, "title": title,
                                  "url": link, "summary": summary[:300]})
        except Exception as e:
            print(f"feed {name} failed:", e)
    print(f"fetched {len(items)} articles from {len(FEEDS)} feeds")
    return items


def fetch_cn_articles():
    """抓中文光通信站列表页的(标题,链接)。无 RSS，正则提取中文标题链接。"""
    out = []
    for name, url, base in CN_FEEDS:
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
            r.encoding = r.apparent_encoding or "utf-8"
            seen = set()
            for href, title in re.findall(
                    r'<a[^>]+href="([^"]+)"[^>]*>\s*([一-龥][^<]{7,40})\s*</a>', r.text):
                title = title.strip()
                if title in seen or any(k in title for k in _CN_SKIP_KW):
                    continue
                if href.startswith("//"):
                    link = "https:" + href
                elif href.startswith("/"):
                    link = base + href
                elif href.startswith("http"):
                    link = href
                else:
                    continue
                seen.add(title)
                out.append({"source": name, "title": title, "url": link,
                            "summary": "", "cn": True})
                if len(seen) >= 18:
                    break
        except Exception as e:
            print(f"cn feed {name} failed:", e)
    print(f"fetched {len(out)} CN articles from {len(CN_FEEDS)} sites")
    return out


# ----------------------------------------------------------------------------
# 2. DeepSeek 筛选 + 归类 + 翻译 + 解读
# ----------------------------------------------------------------------------
def deepseek_brief(date_str, articles):
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key or not articles:
        return None
    lines = [f"[{i}] ({a['source']}) {a['title']} :: {a['summary'][:120]}"
             for i, a in enumerate(articles)]
    art_txt = "\n".join(lines)

    sys = (
        "你是资深光通信行业分析编辑。从给定的英文科技/电信/数据中心报道中，筛选与"
        "光通信产业相关的内容，按以下细分归类(sector 取这些值之一)：\n"
        "- 光传输：骨干/城域/数据中心互联传输设备，重点厂家 Ciena/Acacia/中兴ZTE/烽火Fiberhome/华为Huawei/长飞YOFC/领纤 等\n"
        "- 光模块：800G/1.6T 等光模块，重点厂家 旭创Innolight/新易盛Eoptolink/Coherent/Lumentum 等\n"
        "- AI光互联：AI 数据中心光互联/CPO/硅光/共封装/光背板，重点 英伟达NVIDIA/Meta/Google/Microsoft 等\n"
        "- 光器件芯片：激光器/探测器/光芯片/DSP，重点 Coherent/Lumentum/源杰/光迅Accelink 等\n"
        "- 卫星光通信：星间/星地激光通信、卫星互联网相关光通信\n"
        "- 量子光通信：量子密钥分发QKD/量子网络/量子通信商用\n"
        "- 资本市场：光通信/光互联相关公司的财报、业绩预告、股价大幅异动、融资、IPO/上市、"
        "并购、大额订单/中标、产能扩张等资本市场信息（A股如中际旭创/新易盛/光迅/天孚/太辰光，"
        "美股如 Coherent/Lumentum/Ciena，以及初创公司融资）\n"
        "注意均衡覆盖各细分，尤其留意光模块、卫星光通信、量子光通信、资本市场的条目，不要只选AI/传输。"
        "部分报道标题为中文(来自中文源)，照常处理。排除与光通信无关的纯软件/消费电子/无关社会新闻。"
        "把选中报道翻译/整理为中文并简明摘要。只依据给定报道，不编造。返回严格JSON。")
    user = (
        f"日期：{date_str}\n\n报道列表(带序号)：\n" + art_txt +
        "\n\n请输出JSON，全部中文：\n"
        "{\n"
        '  "brief": "今日光通信行业综述2-3句",\n'
        '  "items": [\n'
        '    {"idx": 序号整数, "title_zh": "中文标题", '
        '"sector": "光传输|光模块|AI光互联|光器件芯片|卫星光通信|量子光通信|资本市场|其他", '
        '"summary_zh": "2-3句中文摘要", "impact": "对产业/相关公司的影响，一句"}\n'
        "  ]\n"
        "}\n"
        "选择 8-14 条最相关的，尽量覆盖多个细分；idx 必须是列表中的序号。若无相关内容则 items 为空数组。"
    )
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": sys},
                      {"role": "user", "content": user}],
            response_format={"type": "json_object"}, temperature=0.4, timeout=120,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print("deepseek failed:", e)
        return None


def resolve_items(articles, brief):
    out, seen = [], set()
    for it in (brief or {}).get("items") or []:
        try:
            i = int(it.get("idx"))
        except (TypeError, ValueError):
            continue
        if 0 <= i < len(articles or []) and i not in seen:
            seen.add(i)
            a = articles[i]
            out.append({
                "title_zh": (it.get("title_zh") or a["title"]).strip(),
                "title_en": a["title"], "url": a["url"], "source": a["source"],
                "cn": a.get("cn", False),
                "sector": (it.get("sector") or "其他").strip(),
                "summary_zh": (it.get("summary_zh") or "").strip(),
                "impact": (it.get("impact") or "").strip(),
            })
    return out


# ----------------------------------------------------------------------------
# 2.5 网页截图（自托管 Playwright）
# ----------------------------------------------------------------------------
COOKIE_BTNS = [
    "#onetrust-accept-btn-handler",
    "button:has-text('Accept All')", "button:has-text('Accept')",
    "button:has-text('I Agree')", "button:has-text('Agree')",
    "button:has-text('Got it')", "button:has-text('同意')",
]
CHALLENGE_MARKERS = [
    "verify you are human", "checking your browser", "just a moment",
    "attention required", "cf-challenge", "enable javascript and cookies",
]


def _is_challenge(page):
    try:
        blob = ((page.title() or "") + " " +
                (page.inner_text("body", timeout=2000) or "")[:1500]).lower()
    except Exception:
        return False
    return any(m in blob for m in CHALLENGE_MARKERS)


def capture_screenshots(items, date_str):
    """Playwright 截每条 {i}_thumb.jpg(首屏,滚到标题) + {i}_full.jpg(整页)。
    遇人机验证页则跳过(不展示验证页截图)。"""
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print("playwright import failed:", e)
        return
    outdir = f"docs/shots/{date_str}"
    os.makedirs(outdir, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage",
                                          "--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(viewport={"width": 900, "height": 640},
                                  user_agent=UA, locale="en-US")
        for i, it in enumerate(items):
            if it.get("cn"):          # 中文源用户可直接访问，不截图
                print(f"shot {i} skip (cn source)")
                continue
            page = ctx.new_page()
            try:
                page.goto(it["url"], wait_until="domcontentloaded", timeout=35000)
                page.wait_for_timeout(3000)
                if _is_challenge(page):
                    page.wait_for_timeout(5000)
                if _is_challenge(page):
                    print(f"shot {i} blocked (verification), skip")
                    page.close()
                    continue
                for sel in COOKIE_BTNS:
                    try:
                        page.click(sel, timeout=1000)
                        page.wait_for_timeout(400)
                        break
                    except Exception:
                        pass
                page.wait_for_timeout(600)
                page.screenshot(path=f"{outdir}/{i}_full.jpg", type="jpeg", quality=70,
                                full_page=True)
                try:
                    page.evaluate(
                        "() => { const h = document.querySelector('h1');"
                        " if (h) { window.scrollTo(0, h.getBoundingClientRect().top"
                        " + window.scrollY - 16); } }")
                    page.wait_for_timeout(500)
                except Exception:
                    pass
                page.screenshot(path=f"{outdir}/{i}_thumb.jpg", type="jpeg", quality=74)
                it["shot_thumb"] = f"shots/{date_str}/{i}_thumb.jpg"
                it["shot_full"] = f"shots/{date_str}/{i}_full.jpg"
                print(f"shot {i} ok")
            except Exception as e:
                print(f"shot {i} failed:", e)
            finally:
                if not page.is_closed():
                    page.close()
        browser.close()


def prune_shots(keep=14):
    root = "docs/shots"
    if not os.path.isdir(root):
        return
    dirs = sorted([d for d in os.listdir(root)
                   if re.match(r"\d{4}-\d{2}-\d{2}$", d)], reverse=True)
    import shutil
    for d in dirs[keep:]:
        shutil.rmtree(os.path.join(root, d), ignore_errors=True)


# ----------------------------------------------------------------------------
# 3. 生成 HTML
# ----------------------------------------------------------------------------
SECTOR_ORDER = ["光传输", "光模块", "AI光互联", "光器件芯片", "卫星光通信",
                "量子光通信", "资本市场", "其他"]
SECTOR_COLOR = {"光传输": "#1d4ed8", "光模块": "#047857", "AI光互联": "#be123c",
                "光器件芯片": "#b45309", "卫星光通信": "#7c3aed",
                "量子光通信": "#0891b2", "资本市场": "#ca8a04", "其他": "#6b7280"}


def build_html(date_str, weekday_cn, items, brief_text):
    pages = os.environ.get("PAGES_BASE", "").rstrip("/")
    share = ""
    if pages:
        share = (f'<div style="background:#eff6ff;border:1px solid #bfdbfe;padding:10px 18px;'
                 f'font-size:13px;color:#1e40af;">🔗 在线版（可转发）：'
                 f'<a href="{pages}/{date_str}.html" style="color:#2563eb;">{pages}/{date_str}.html</a></div>')

    groups = {}
    for it in items:
        groups.setdefault(it["sector"] if it["sector"] in SECTOR_ORDER else "其他", []).append(it)

    body = ""
    for sec in SECTOR_ORDER:
        if sec not in groups:
            continue
        clr = SECTOR_COLOR.get(sec, "#6b7280")
        body += (f'<div style="margin:18px 0 8px;font-size:16px;font-weight:700;color:{clr};'
                 f'border-left:4px solid {clr};padding-left:10px;">{sec}</div>')
        for it in groups[sec]:
            impact = (f'<div style="color:#6b7280;font-size:13px;margin-top:4px;">💡 {it["impact"]}</div>'
                      if it["impact"] else "")
            shot_html, read_link = "", it["url"]
            if it.get("shot_thumb"):
                thumb = f'{pages}/{it["shot_thumb"]}' if pages else it["shot_thumb"]
                full = f'{pages}/{it["shot_full"]}' if pages else it["shot_full"]
                read_link = full
                shot_html = (
                    f'<a href="{full}" target="_blank" style="display:block;margin-top:8px;">'
                    f'<img src="{thumb}" alt="网页截图" style="width:100%;max-width:560px;'
                    f'border:1px solid #e5e7eb;border-radius:6px;display:block;"></a>')
            read_label = "阅读全文（整页截图）" if it.get("shot_full") else "阅读原文"
            body += (
                f'<div style="padding:14px 0;border-bottom:1px solid #f0f0f0;">'
                f'<a href="{read_link}" target="_blank" style="color:#1f2329;font-size:15px;'
                f'font-weight:600;text-decoration:none;">{it["title_zh"]}</a>'
                f'<div style="color:#374151;font-size:14px;line-height:1.7;margin-top:6px;">{it["summary_zh"]}</div>'
                f'{impact}{shot_html}'
                f'<div style="color:#9ca3af;font-size:12px;margin-top:7px;">来源：{it["source"]} · '
                f'<a href="{read_link}" target="_blank" style="color:#2563eb;">{read_label} ›</a> · '
                f'<a href="{it["url"]}" target="_blank" style="color:#9ca3af;">{"原文" if it.get("cn") else "英文原站"}</a></div>'
                f'</div>')

    if not items:
        body = '<p style="color:#9ca3af;">今日暂无筛选到相关光通信资讯。</p>'

    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>光通信每日简报 · {date_str}</title></head>
<body style="margin:0;padding:0;background:#f4f5f7;font-family:'Microsoft YaHei',-apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:#1f2329;">
<div style="max-width:680px;margin:0 auto;padding:20px;">
  <div style="background:#0c4a6e;border-radius:10px 10px 0 0;padding:22px 24px;">
    <div style="color:#fff;font-size:22px;font-weight:700;">📡 光通信每日简报 · {date_str}（{weekday_cn}）</div>
    <div style="color:#bae6fd;font-size:13px;margin-top:6px;">光传输 · 光模块 · AI光互联 · 光器件芯片 · 卫星/量子光通信 · 翻译解读由 DeepSeek 提供</div>
  </div>
  {share}
  <div style="background:#fff;padding:18px 24px;">
    <div style="background:#f8fafc;border-radius:8px;padding:12px 14px;font-size:14px;color:#334155;line-height:1.7;">
      <b>📋 今日综述：</b>{brief_text}
    </div>
    {body}
    <div style="margin-top:16px;padding:12px 14px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;font-size:12px;color:#6b7280;line-height:1.7;">
      信息来自公开外媒/行业报道（The Next Platform、Light Reading、DataCenterDynamics、OFweek光通讯、讯石、C114 等），由 DeepSeek 翻译归类与梳理，可能存在偏差或时效差，仅供参考，不构成投资建议。英文源页面截图托管于本站；中文源可直接点「原文」访问。
    </div>
  </div>
  <div style="text-align:center;color:#9ca3af;font-size:12px;padding:16px;">光通信每日简报 · 云端自动推送 · {date_str}</div>
</div></body></html>"""


# ----------------------------------------------------------------------------
# 4. 发布到 GitHub Pages
# ----------------------------------------------------------------------------
def publish_pages(dash, html):
    os.makedirs("docs", exist_ok=True)
    with open(f"docs/{dash}.html", "w", encoding="utf-8") as f:
        f.write(html)
    nav = ('<div style="max-width:680px;margin:0 auto;padding:10px 20px;text-align:right;">'
           '<a href="archive.html" style="color:#2563eb;font-size:13px;text-decoration:none;">'
           '📅 查看历史简报 &rsaquo;</a></div>')
    anchor = '<div style="max-width:680px;margin:0 auto;padding:20px;">'
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html.replace(anchor, nav + anchor, 1))
    files = sorted([fn for fn in os.listdir("docs")
                    if re.match(r"\d{4}-\d{2}-\d{2}\.html$", fn)], reverse=True)
    items = "\n".join(f'<li><a href="{fn}">{fn[:-5]}</a></li>' for fn in files)
    archive = (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>光通信每日简报 · 历史</title></head>'
        '<body style="font-family:-apple-system,Microsoft YaHei,sans-serif;max-width:680px;'
        'margin:0 auto;padding:24px;color:#1f2329;">'
        '<p><a href="index.html" style="color:#2563eb;text-decoration:none;">&lsaquo; 返回最新一期</a></p>'
        '<h2>📡 光通信每日简报 · 历史</h2>'
        f'<ul style="line-height:2;">{items}</ul>'
        '<p style="color:#9ca3af;font-size:12px;">每天早上 7:30 自动更新 · 信息仅供参考</p></body></html>'
    )
    with open("docs/archive.html", "w", encoding="utf-8") as f:
        f.write(archive)
    print("pages published:", dash)


# ----------------------------------------------------------------------------
# 5. 发送邮件
# ----------------------------------------------------------------------------
def send_email(subject, html):
    user = os.environ["GMAIL_USER"]
    pwd = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "")
    to = os.environ.get("MAIL_TO", user)
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((str(Header("光通信简报", "utf-8")), user))
    msg["To"] = to
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as s:
        s.starttls()
        s.login(user, pwd)
        s.sendmail(user, [x.strip() for x in to.split(",")], msg.as_string())
    print("email sent to", to)


# ----------------------------------------------------------------------------
def main():
    now = beijing_now()
    dash = now.strftime("%Y-%m-%d")
    weekday_cn = "周" + "一二三四五六日"[now.weekday()]

    articles = fetch_articles() + fetch_cn_articles()
    if not articles:
        print("no articles; abort.")
        return

    brief = deepseek_brief(dash, articles)
    items = resolve_items(articles, brief)
    brief_text = (brief or {}).get("brief", "（综述未生成）")
    print(f"selected {len(items)} items")

    try:
        capture_screenshots(items, dash)
        prune_shots(14)
    except Exception as e:
        print("screenshots failed:", e)

    html = build_html(dash, weekday_cn, items, brief_text)

    try:
        publish_pages(dash, html)
    except Exception as e:
        print("publish_pages failed:", e)

    send_email(f"光通信简报 {dash}", html)


if __name__ == "__main__":
    main()
