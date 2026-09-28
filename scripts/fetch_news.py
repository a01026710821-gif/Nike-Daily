#!/usr/bin/env python3
import urllib.request, urllib.parse, xml.etree.ElementTree as ET, json, re, html, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/news.json"

# 1. 주가 데이터 수집 (Yahoo Finance API)
def fetch_nike_stock():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/NKE?interval=1d&range=5d"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        res = urllib.request.urlopen(req, timeout=10)
        data = json.loads(res.read().decode('utf-8'))
        
        meta = data['chart']['result'][0]['meta']
        price = meta.get('regularMarketPrice')
        prev_close = meta.get('chartPreviousClose')
        
        if price and prev_close:
            change = price - prev_close
            change_percent = (change / prev_close) * 100
            sign = "+" if change >= 0 else ""
            return {
                "symbol": "NKE (NYSE)",
                "price": f"${price:.2f}",
                "change": f"{sign}${change:.2f} ({sign}{change_percent:.2f}%)",
                "is_up": change >= 0
            }
    except Exception as e:
        print("주가 정보 수집 실패:", e)
    return {"symbol": "NKE (NYSE)", "price": "N/A", "change": "N/A", "is_up": True}

# 2. 최근 7일간의 주간 뉴스 수집
QUERIES = [
    '나이키',
    '나이키 주가',
    '나이키 운동화 OR 에어맥스 OR 조던',
    '나이키 실적 OR 매출',
    '나이키 코리아',
    '나이키 아디다스'
]

UA = "Mozilla/5.0 (NIKE-DAILY/1.0)"
items = []; seen = set()

def clean(s):
    s = re.sub(r'<[^>]+>', ' ', s or '')
    s = html.unescape(s)
    return re.sub(r'\s+', ' ', s).strip()

def extract_image(item_element):
    try:
        for child in item_element:
            if 'thumbnail' in child.tag or 'content' in child.tag:
                url = child.attrib.get('url')
                if url: return url
        desc = item_element.findtext("description") or ""
        match = re.search(r'src=["\'](https?://[^"\']+)["\']', desc)
        if match: return match.group(1)
    except Exception:
        pass
    return ""

for q in QUERIES:
    # 주간지를 위해 when:7d 로 변경
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q": q + " when:7d",
        "hl": "ko",
        "gl": "KR",
        "ceid": "KR:ko"
    })
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        data = urllib.request.urlopen(req, timeout=20).read()
        root = ET.fromstring(data)
        
        for x in root.findall(".//item"):
            title = clean(x.findtext("title"))
            link = x.findtext("link") or ""
            pub = x.findtext("pubDate") or ""
            source = x.findtext("source") or "Google News"
            desc = clean(x.findtext("description"))
            img_url = extract_image(x)
            
            key = re.sub(r'[^가-힣a-z0-9]', '', title.lower())
            if not title or key in seen:
                continue
            seen.add(key)
            
            low = title.lower() + " " + desc.lower()
            if not any(w in low for w in ["나이키", "nike", "조던", "jordan", "컨버스", "converse"]):
                continue
                
            cat = "BUSINESS"
            if any(w in low for w in ["신발", "운동화", "스니커즈", "에어맥스", "페가수스", "조던", "신제품", "출시", "컬렉션", "shoe", "sneaker"]):
                cat = "PRODUCT"
            elif any(w in low for w in ["광고", "캠페인", "브랜드", "마케팅", "컨버스", "brand", "marketing"]):
                cat = "BRAND"
            elif any(w in low for w in ["주가", "주식", "실적", "매출", "영업이익", "증시", "시장", "stock", "revenue", "earnings"]):
                cat = "MARKET"
            elif any(w in low for w in ["축구", "농구", "선수", "국대", "유니폼", "스포츠", "엠바페", "손흥민", "nba", "soccer"]):
                cat = "SPORTS"
                
            summary = desc[:300] if desc else title
            items.append({
                "cat": cat,
                "title": title,
                "summary": summary,
                "source": source,
                "date": pub[:16],
                "url": link,
                "image": img_url
            })
    except Exception as e:
        pass

items = items[:30]
today = datetime.date.today().isoformat()
stock_info = fetch_nike_stock()

if not items:
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"items": []}
    items = old.get("items", [])

data = {
    "date": today,
    "stock": stock_info,
    "insight": "한 주간 Google News에서 수집된 나이키 관련 주요 주간 브리핑입니다.",
    "items": items
}

OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("Updated", OUT, len(items), "items with stock info")
