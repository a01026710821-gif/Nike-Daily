#!/usr/bin/env python3
import urllib.request, urllib.parse, xml.etree.ElementTree as ET, json, re, html, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data/news.json"
QUERIES=[
 'Nike',
 '"Nike Inc"',
 'Nike OR Jordan OR Converse',
 'Nike running',
 'Nike basketball',
 'Nike Korea',
 'Nike Adidas On Hoka'
]
UA="Mozilla/5.0 (NIKE-DAILY/1.0)"
items=[]; seen=set()

def clean(s):
    s=re.sub(r'<[^>]+>',' ',s or '')
    s=html.unescape(s)
    return re.sub(r'\s+',' ',s).strip()

for q in QUERIES:
    url="https://news.google.com/rss/search?"+urllib.parse.urlencode({"q":q+" when:7d","hl":"en-US","gl":"US","ceid":"US:en"})
    try:
        req=urllib.request.Request(url,headers={"User-Agent":UA})
        data=urllib.request.urlopen(req,timeout=20).read()
        root=ET.fromstring(data)
        for x in root.findall(".//item"):
            title=clean(x.findtext("title"))
            link=x.findtext("link") or ""
            pub=x.findtext("pubDate") or ""
            source=x.findtext("source") or "Google News"
            desc=clean(x.findtext("description"))
            key=re.sub(r'[^a-z0-9]','',title.lower())
            if not title or key in seen: continue
            seen.add(key)
            # Basic relevance filter
            low=title.lower()+" "+desc.lower()
            if "nike" not in low and "jordan" not in low and "converse" not in low: continue
            cat="BUSINESS"
            if any(w in low for w in ["shoe","sneaker","air max","pegasus","jordan","product","collection","release"]): cat="PRODUCT"
            elif any(w in low for w in ["advert","campaign","converse","brand","marketing"]): cat="BRAND"
            elif any(w in low for w in ["stock","shares","dow","revenue","earnings","sales","market"]): cat="MARKET"
            elif any(w in low for w in ["soccer","nba","nfl","athlete","mbappe"]): cat="SPORTS"
            summary=desc[:300] if desc else title
            items.append({"cat":cat,"title":title,"summary":summary,"source":source,"date":pub[:16],"url":link})
    except Exception as e:
        pass

# Preserve a useful fallback if Google RSS is temporarily unavailable.
items=items[:30]
today=datetime.date.today().isoformat()
if not items:
    old=json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"items":[]}
    items=old.get("items",[])
data={"date":today,"insight":"최근 7일간 Google News에서 수집된 Nike 관련 기사입니다. 자동 수집본은 원문을 확인하기 전 참고용으로 사용하세요.","items":items}
OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
print("Updated",OUT,len(items),"items")
