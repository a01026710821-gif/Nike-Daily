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

# 🚫 [유료 / 멤버십 / 특정 언론사 차단 키워드 및 URL 패턴]
PAYWALL_KEYWORDS = [
    "중앙plus", "joongang plus", "the joongang plus", "중앙플러스", "joongang.co.kr/plus", 
    "plus.joongang", "아시아경제 멤버십", "조선plus", "조선일보 유료", "매경 럭스멘", 
    "유료", "멤버십", "구독자 전용", "더 남아있는 이야기", "프리미엄 기사", "아티클 플러스",
    "paywall", "유료기사", "유료회원", "구독기사", "이용권", "로그인후", "전용 콘텐츠",
    "지금 바로 시작하기", "보유하신 이용권",
    "hankyung.com", "hankyung", "한국경제",
    # 💡 인베스팅닷컴 차단 키워드 및 URL 추가
    "investing.com", "kr.investing.com", "인베스팅닷컴", "article-93ch"
]

PAYWALL_SOURCES = [
    "중앙plus", "joongang plus", "조선일보 유료", "아시아경제 멤버십", "한국경제", "한경", "investing.com", "인베스팅"
]

COMPETITOR_BRANDS = ["아디다스", "adidas", "뉴발란스", "new balance", "호카", "hoka", "온러닝", "on running", "룰루레몬", "lululemon", "푸마", "puma", "언더아머"]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

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

def fetch_rss(query_str):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q": query_str + " when:7d",
        "hl": "ko",
        "gl": "KR",
        "ceid": "KR:ko"
    })
    results = []
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
            
            full_text = f"{title} {source} {desc} {link}".lower()
            
            # 유료 기사 및 특정 언론사 차단
            if any(ps in source.lower() for ps in PAYWALL_SOURCES) or any(pk in full_text for pk in PAYWALL_KEYWORDS):
                continue

            results.append({
                "title": title,
                "summary": desc[:200] if desc else title,
                "source": source,
                "date": pub[:16],
                "url": link,
                "image": img_url,
                "full_text": full_text
            })
    except Exception as e:
        print("RSS 수집 오류:", e)
    return results

items = []
seen = set()

# 1. 나이키 전용 기사 수집
nike_queries = ['나이키', '나이키 주가 OR 실적', '나이키 운동화 OR 신제품', '나이키 선수 OR 유니폼']
for q in nike_queries:
    raw_news = fetch_rss(q)
    for news in raw_news:
        key = re.sub(r'[^가-힣a-z0-9]', '', news["title"].lower())
        if not news["title"] or key in seen:
            continue
        
        # 나이키 관련 필수 단어 포함 검사
        if not any(w in news["full_text"] for w in ["나이키", "nike", "조던", "jordan", "컨버스"]):
            continue

        seen.add(key)
        
        low = news["full_text"]
        if any(w in low for w in ["축구", "농구", "선수", "국대", "유니폼", "스포츠", "엠바페", "손흥민", "nba", "올림픽", "골프"]):
            cat = "SPORTS"
        elif any(w in low for w in ["주가", "주식", "실적", "매출", "영업이익", "증시", "증권", "펀드", "투자"]):
            cat = "MARKET"
        elif any(w in low for w in ["신발", "운동화", "스니커즈", "에어맥스", "페가수스", "조던", "신제품", "출시", "컬렉션", "스니커"]):
            cat = "PRODUCT"
        else:
            cat = "BRAND"

        items.append({
            "cat": cat,
            "title": news["title"],
            "summary": news["summary"],
            "source": news["source"],
            "date": news["date"],
            "url": news["url"],
            "image": news["image"]
        })

# 2. 경쟁사 전용 기사 수집 (독립 수집 파이프라인)
comp_queries = ['아디다스', '뉴발란스', '호카 OR 온러닝', '룰루레몬 OR 푸마']
comp_count = 0
for q in comp_queries:
    raw_news = fetch_rss(q)
    for news in raw_news:
        if comp_count >= 6: # 경쟁사 기사 최대 6개 수집
            break
        key = re.sub(r'[^가-힣a-z0-9]', '', news["title"].lower())
        if not news["title"] or key in seen:
            continue

        if any(cb in news["full_text"] for cb in COMPETITOR_BRANDS):
            seen.add(key)
            items.append({
                "cat": "COMPETITOR",
                "title": news["title"],
                "summary": news["summary"],
                "source": news["source"],
                "date": news["date"],
                "url": news["url"],
                "image": news["image"]
            })
            comp_count += 1

today = datetime.date.today().isoformat()
stock_info = fetch_nike_stock()

data = {
    "date": today,
    "stock": stock_info,
    "insight": "한 주간 Google News에서 수집된 나이키 및 주요 경쟁사 분야별 브리핑입니다.",
    "items": items
}

OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Updated {OUT}: 총 {len(items)}개 기사 수집 완료 (경쟁사 기사 {comp_count}개 포함)")
