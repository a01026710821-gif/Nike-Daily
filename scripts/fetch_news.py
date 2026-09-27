#!/usr/bin/env python3
import urllib.request, urllib.parse, xml.etree.ElementTree as ET, json, re, html, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/news.json"

# 1. 한국어 검색 키워드 설정
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

for q in QUERIES:
    # 2. 최근 24시간(전일 기준: when:1d) + 한국어/한국지역 설정
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q": q + " when:1d",
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
            
            # 제목 중복 검사
            key = re.sub(r'[^가-힣a-z0-9]', '', title.lower())
            if not title or key in seen:
                continue
            seen.add(key)
            
            # 3. 키워드 필터링 (한글/영문 지원)
            low = title.lower() + " " + desc.lower()
            if not any(w in low for w in ["나이키", "nike", "조던", "jordan", "컨버스", "converse"]):
                continue
                
            # 4. 카테고리 자동 분류
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
                "url": link
            })
    except Exception as e:
        pass

# 상위 30개 기사 추출
items = items[:30]
today = datetime.date.today().isoformat()

# 만약 하루 동안 뉴스 수량이 적다면 이전 백업을 활용
if not items:
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"items": []}
    items = old.get("items", [])

data = {
    "date": today,
    "insight": "최근 24시간 동안 Google News에서 수집된 나이키 관련 주요 기사입니다.",
    "items": items
}

OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("Updated", OUT, len(items), "items")
