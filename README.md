# NIKE DAILY — 무료 운영 버전

## 무엇이 들어 있나요?
- `index.html`: 직원이 보는 웹페이지
- `data/news.json`: 현재 뉴스 데이터
- `scripts/fetch_news.py`: Google News RSS에서 최근 7일 Nike 관련 기사 수집
- `.github/workflows/update.yml`: 매일 자동 갱신하는 GitHub Actions

## 비용
이 버전은 외부 유료 API를 사용하지 않습니다.
- GitHub Pages: 무료
- GitHub Actions: 공개 저장소에서 무료 범위 사용
- Google News RSS: 무료
- 별도 서버: 필요 없음

## 실제 배포 방법
1. GitHub 계정을 만듭니다.
2. 새 PUBLIC 저장소를 하나 만듭니다. 예: `nike-daily`
3. 이 폴더의 모든 파일을 저장소에 업로드합니다.
4. GitHub 저장소의 Settings → Pages에서 `Deploy from a branch`를 선택하고 `main / root`를 선택합니다.
5. 잠시 후 GitHub가 제공하는 `https://계정.github.io/nike-daily/` 주소가 웹페이지 주소가 됩니다.
6. Actions 탭에서 `Update NIKE DAILY`를 한 번 수동 실행하면 뉴스가 갱신됩니다.
7. 이후 매일 UTC 22:00(한국시간 오전 7시)에 자동 갱신됩니다.

## 중요한 운영 한계
이 무료 버전은 AI API를 호출하지 않고 RSS의 기사 제목/설명을 정리합니다. 따라서 'AI가 여러 기사를 읽고 고급 분석'하는 기능은 아직 유료 API 없이 구현한 것이 아닙니다.
또한 Google News RSS 결과는 검색엔진 결과이므로 원문 접근권한/저작권 조건을 존중해야 하며, 사이트에는 원문 링크와 출처만 표시하고 기사를 그대로 재배포하지 않습니다.

## 다음 확장
- 실제 AI 요약을 붙이려면 API 비용이 발생할 수 있습니다.
- 직원 이메일 구독은 별도 이메일 발송 서비스가 필요할 수 있습니다.
- 회사 전용 로그인/권한 기능은 별도 인증 서비스가 필요할 수 있습니다.

현재 버전은 '0원으로 실제 웹페이지를 운영하면서 먼저 수요를 검증'하는 목적입니다.
