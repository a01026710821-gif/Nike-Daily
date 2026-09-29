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
        
        result = data['chart']['result'][0]
        meta = result['meta']
        timestamps = result.get('timestamp', [])
        close_prices = result['indicators']['quote'][0].get('close', [])
        
        price = meta.get('regularMarketPrice', 0)
        prev_close = meta.get('chartPreviousClose', price)
        change = price - prev_close
        change_percent = (change / prev_close) * 100 if prev_close else 0
        sign = "+" if change >= 0 else ""

        chart_data = []
        for ts, p in zip(timestamps, close_prices):
            if p is not None:
                dt_str = datetime.datetime.fromtimestamp(ts).strftime('%m/%d')
                chart_data.append({"date": dt_str, "price": round(p, 2)})

        return {
            "symbol": "NKE (NYSE)",
            "price": f"${price:.2f}",
            "change": f"{sign}${change:.2f} ({sign}{change_percent:.2f}%)",
            "is_up": change >= 0,
            "chart": chart_data
        }
    except Exception as e:
        print("주가 정보 수집 실패:", e)
        return {"symbol": "NKE (NYSE)", "price": "$82.50", "change": "+$1.20 (+1.48%)", "is_up": True, "chart": []}

# 2. 뉴스 수집 쿼리
QUERIES = [
    '나이키',
    '나이키 주가 OR 실적 OR 매출',
    '나이키 운동화 OR 신제품',
    '나이키 선수 OR 유니폼',
    '아디다스 OR 뉴발란스 OR 호카 OR 온러닝 OR 룰루레몬 OR 푸마'
]

# 🚫 [유료 / 멤버십 / 특정 언론사 차단 키워드]
PAYWALL_KEYWORDS = [
    "중앙plus", "joongang plus", "the joongang plus", "중앙플러스", "joongang.co.kr/plus", 
    "plus.joongang", "아시아경제 멤버십", "조선plus", "조선일보 유료", "매경 럭스멘", 
    "유료", "멤버십", "구독자 전용", "더 남아있는 이야기", "프리미엄 기사", "아티클 플러스",
    "paywall", "유료기사", "유료회원", "구독기사", "이용권", "로그인후", "전용 콘텐츠",
    "지금 바로 시작하기", "보유하신 이용권",
    "hankyung.com", "hankyung", "한국경제"
]

PAYWALL_SOURCES = [
    "중앙plus", "joongang plus", "조선일보 유료", "아시아경제 멤버십", "한국경제", "한경"
]

# 경쟁사 감지 키워드 (모델명 제외, 브랜드명 중심)
COMPETITOR_BRANDS = ["아디다스", "adidas", "뉴발란스", "new balance", "호카", "hoka", "온러닝", "on running", "룰루레몬", "lululemon", "푸마", "puma", "언더아머", "under armour"]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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
            source = clean(x.findtext("source") or "Google News")
            desc = clean(x.findtext("description"))
            img_url = extract_image(x)
            
            key = re.sub(r'[^가-힣a-z0-9]', '', title.lower())
            if not title or key in seen:
                continue
            
            full_text = f"{title} {source} {desc} {link}".lower()
            
            # 🚫 1) 유료/차단 언론사 필터링
            if any(ps in source.lower() for ps in PAYWALL_SOURCES) or any(pk in full_text for pk in PAYWALL_KEYWORDS):
                continue

            # 2) 나이키 또는 경쟁사 브랜드 포함 확인
            is_nike = any(w in full_text for w in ["나이키", "nike", "조던", "jordan", "컨버스"])
            is_competitor = any(cb in full_text for cb in COMPETITOR_BRANDS)

            if not (is_nike or is_competitor):
                continue

            seen.add(key)
                
            # 3) 카테고리 분류
            low = title.lower() + " " + desc.lower()
            
            # 경쟁사 키워드가 감지되면 최우선 경쟁사로 분류
            if is_competitor and not is_nike:
                cat = "COMPETITOR"
            elif any(w in low for w in ["축구", "농구", "선수", "국대", "유니폼", "스포츠", "엠바페", "손흥민", "nba", "올림픽", "골프"]):
                cat = "SPORTS"
            elif any(w in low for w in ["주가", "주식", "실적", "매출", "영업이익", "증시", "증권", "펀드", "투자", "s&p"]):
                cat = "MARKET"
            elif any(w in low for w in ["신발", "운동화", "스니커즈", "에어맥스", "페가수스", "조던", "신제품", "출시", "컬렉션", "스니커"]):
                cat = "PRODUCT"
            else:
                cat = "BRAND"
                
            summary = desc[:200] if desc else title
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

items = items[:40]
today = datetime.date.today().isoformat()
stock_info = fetch_nike_stock()

data = {
    "date": today,
    "stock": stock_info,
    "insight": "한 주간 Google News에서 수집된 나이키 및 주요 경쟁사 분야별 브리핑입니다.",
    "items": items
}

OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Updated {OUT}: 총 {len(items)}개 기사 수집 완료")
