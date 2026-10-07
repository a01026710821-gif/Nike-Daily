"""Evidence-linked, rule-based weekly brief. No AI API or invented facts."""
from datetime import date, timedelta, datetime
from email.utils import parsedate_to_datetime
from html import escape
from urllib.parse import urlparse
import re

TOPICS = [
    ("실적·재무", ["실적", "매출", "영업이익", "수익", "earnings", "revenue", "profit", "sales", "주가", "stock"],
     "실적·수익성 관련 보도가 확인됨. 보도별 수치와 공식 발표의 일치 여부를 확인할 필요가 있음.",
     "Nike 실적 흐름이 생산·발주 계획에 영향을 미치는지 확인하고, 실제 주문 변동과 구분하여 점검"),
    ("조직·경영", ["조직", "구조조정", "경영", "ceo", "layoff", "restructur", "leadership", "인력", "전략", "strategy"],
     "조직·경영 전략 관련 보도가 확인됨. 구체적인 실행 범위는 공식 발표와 후속 보도로 검증해야 함.",
     "조직·운영 정책 변화가 구매 승인, 공급업체 평가, 납기 관리에 미치는지 모니터링"),
    ("시장·경쟁", ["중국", "미국", "점유율", "경쟁", "adidas", "아디다스", "hoka", "호카", "시장", "market", "competition"],
     "주요 시장 및 경쟁 구도에 관한 보도가 확인됨. 시장별 판매 추세와 브랜드 경쟁력 변화를 관찰할 필요가 있음.",
     "판매 시장 변화가 생산 물량 및 소재 수요에 반영되는지 점검"),
    ("제품·혁신", ["신제품", "출시", "러닝", "마라톤", "레이싱", "에이펙스", "running", "launch", "innovation", "shoe", "운동화"],
     "제품 출시·기술 경쟁 관련 보도가 확인됨. 제품 성과는 출시 보도와 실제 판매 지표를 구분해 판단해야 함.",
     "신제품 관련 자재 사양·납기·대체 소싱 대응 가능성을 사전 검토"),
    ("공급망·제조", ["공급망", "공급업체", "생산", "공장", "베트남", "인도네시아", "supply chain", "supplier", "manufactur", "factory", "sourcing"],
     "공급망·생산 관련 보도가 확인됨. 공개 보도만으로 협력업체에 대한 실제 정책 변경을 단정할 수 없음.",
     "관련 공장·협력사별 생산 일정, 핵심 자재 납기 및 공급 리스크를 점검"),
]

def _date(value):
    try:
        return parsedate_to_datetime(value).date()
    except (ValueError, TypeError, IndexError):
        for fmt in ("%a, %d %b %Y", "%d %b %Y"):
            try:
                return datetime.strptime(str(value), fmt).date()
            except (ValueError, TypeError):
                pass
        try:
            return date.fromisoformat(str(value)[:10])
        except (ValueError, TypeError):
            return None

def _valid_url(url):
    p = urlparse(str(url))
    return p.scheme in ('https', 'http') and bool(p.netloc)

def build_brief(news_data, run_date=None):
    today = run_date or date.today()
    end = today - timedelta(days=today.weekday() + 1)
    start = end - timedelta(days=6)
    articles = []
    seen = set()
    for item in news_data.get('items', []):
        published = _date(item.get('date'))
        title = re.sub(r'\s+-\s+[^-]{2,55}$', '', str(item.get('title', '')).strip())
        url = item.get('url', '')
        key = re.sub(r'\W+', '', title.lower())
        if not (published and start <= published <= end and title and _valid_url(url)) or key in seen:
            continue
        seen.add(key)
        articles.append({**item, 'clean_title': title, 'published': published})
    topics = []
    for label, keywords, meaning, action in TOPICS:
        matches = []
        for article in articles:
            haystack = (article['clean_title'] + ' ' + str(article.get('summary', ''))).lower()
            score = sum(1 for word in keywords if word.lower() in haystack)
            if score:
                matches.append((score, article))
        matches.sort(key=lambda pair: (-pair[0], -pair[1]['published'].toordinal()))
        if matches:
            topics.append({'label': label, 'count': len(matches), 'meaning': meaning, 'action': action, 'evidence': [a for _, a in matches[:2]]})
    topics.sort(key=lambda x: -x['count'])
    return {'start': start, 'end': end, 'articles': len(articles), 'topics': topics[:3]}

def render_brief(news_data, run_date=None):
    brief = build_brief(news_data, run_date)
    h = lambda s: escape(str(s), quote=True)
    header = f'''<div style="margin:24px 0 16px;border-top:4px solid #111;padding-top:16px;font-family:Arial,sans-serif">
    <div style="font-size:11px;font-weight:bold;letter-spacing:1.5px;color:#bd5b18">NIKE WEEKLY / EXECUTIVE INTELLIGENCE</div>
    <h2 style="font-size:22px;line-height:1.3;color:#111;margin:7px 0">WEEKLY STRATEGIC BRIEF</h2>
    <div style="font-size:12px;color:#777">분석기간: {brief['start']:%Y.%m.%d} – {brief['end']:%Y.%m.%d} · 수집 기사 {brief['articles']}건 (발행일 기준)</div></div>'''
    if not brief['topics']:
        return header + '<div style="padding:18px;background:#f6f6f6;font-size:13px;color:#444">분석 기간 내 근거 기사가 부족하여 이번 주 전략 분석을 생략합니다. 기존 뉴스 목록을 참고해 주세요.</div>'
    topics = brief['topics']
    lead = ' · '.join(t['label'] for t in topics)
    parts = [header, f'<div style="padding:15px;background:#f6f6f6"><b style="font-size:12px;color:#ae5416">EXECUTIVE SUMMARY</b><p style="font-size:14px;line-height:1.7;margin:8px 0 0">이번 주 수집 기사에서 <b>{h(lead)}</b> 관련 보도가 상대적으로 두드러졌습니다. 아래는 기사 제목·RSS 요약을 근거로 정리한 검토 포인트이며, 공식 발표 확인 전 확정적인 경영 판단으로 해석해서는 안 됩니다.</p></div>', '<h3 style="font-size:14px;margin:22px 0 12px">01 / KEY STRATEGIC DEVELOPMENTS</h3>']
    for i, t in enumerate(topics, 1):
        links = ''.join(f'<div style="margin-top:5px"><a href="{h(a["url"])}" style="color:#444;font-size:12px;text-decoration:underline">[{h(a.get("source") or "원문")}] {h(a["clean_title"])}</a></div>' for a in t['evidence'])
        parts.append(f'<div style="border-bottom:1px solid #e5e5e5;padding:12px 0"><b style="font-size:14px">{i:02d} {h(t["label"])}</b><div style="font-size:12px;color:#888;margin:4px 0">관련 기사 {t["count"]}건</div><p style="font-size:13px;line-height:1.7;color:#333">{h(t["meaning"])}</p>{links}</div>')
    parts.append('<h3 style="font-size:14px;margin:22px 0 10px">02 / STRATEGIC OUTLOOK</h3><p style="font-size:13px;line-height:1.7;color:#333">이번 주 확인된 핵심 이슈의 후속 공식 발표, 실적 수치 및 실제 실행 여부를 우선 모니터링할 필요가 있습니다. 기사 빈도는 전략적 중요도 또는 실제 사업 영향을 의미하지 않습니다.</p>')
    actions = ''.join(f'<li style="margin:6px 0">{h(t["action"])}</li>' for t in topics[:2])
    parts.append(f'<div style="background:#f5f5f5;padding:16px;margin:20px 0"><b style="font-size:12px">03 / SHC BUSINESS IMPLICATIONS</b><p style="font-size:13px;line-height:1.7;color:#333">다음은 Nike의 확정 지시사항이 아닌 SHC 내부 검토 제안입니다.</p><ul style="padding-left:19px;font-size:13px;line-height:1.7">{actions}</ul></div>')
    parts.append('<div style="font-size:11px;color:#777;line-height:1.6;margin-bottom:24px">분석 방법: 전주 월~일 발행 기사 제목 및 RSS 요약의 주제별 분류. 기사 본문 전체·사실관계 자동 검증 및 AI 심층 분석은 수행하지 않음. 근거 기사 링크를 확인해 주세요.</div>')
    return '\n'.join(parts)
