# ☀️ Seoul Weather Slack Bot

매일 아침 7시, 서울의 날씨를 Slack으로 알려주는 봇입니다.

<img src="https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white" alt="Python"> <img src="https://img.shields.io/badge/Slack-Bot-4A154B?logo=slack&logoColor=white" alt="Slack"> <img src="https://img.shields.io/github/actions/workflow/status/concrete-sangminlee/weather-slack-bot/weather.yml?label=Daily%20Weather&logo=githubactions&logoColor=white" alt="Workflow Status">

## 📱 Slack 메시지 예시

```
☀️ 서울 오늘의 날씨
━━━━━━━━━━━━━━━
🌡️ 기온: 9.5°C (체감 6.3°C)
🌤️ 날씨: 맑음
💧 습도: 34%
━━━━━━━━━━━━━━━
💡 오늘의 팁: 🍃 좋은 하루 보내세요!
```

## ✨ 기능

- **실시간 날씨 정보** — 기온, 체감 기온, 날씨 상태, 습도
- **상황별 한줄 팁** — 비/눈/폭염/한파 등 날씨에 맞는 조언
- **매일 자동 실행** — GitHub Actions로 매일 아침 7시(KST) 전송
- **수동 실행 지원** — Actions 탭에서 언제든 수동 실행 가능

## 🛠️ 기술 스택

| 구분 | 기술 |
|------|------|
| 날씨 API | [Open-Meteo](https://open-meteo.com/) (무료, 키 불필요) |
| Slack 연동 | [slack-sdk](https://slack.dev/python-slack-sdk/) |
| 스케줄링 | GitHub Actions (cron) |
| 언어 | Python 3.12 |

## 🚀 설정 방법

### 1. Slack App 생성

1. [Slack API](https://api.slack.com/apps)에서 새 앱 생성
2. **OAuth & Permissions** → Bot Token Scopes에 `chat:write` 추가
3. 워크스페이스에 설치 후 `xoxb-` 토큰 복사
4. 메시지를 받을 채널에 봇 초대 (`/invite @봇이름`)

### 2. GitHub Secrets 등록

```bash
gh secret set SLACK_BOT_TOKEN    # Slack Bot 토큰 입력
gh secret set SLACK_CHANNEL      # 채널명 입력 (예: general)
```

### 3. 완료!

매일 아침 7시(KST)에 자동으로 날씨가 전송됩니다.

수동 실행: **Actions** 탭 → **Seoul Weather Bot** → **Run workflow**

## 📁 프로젝트 구조

```
├── weather_bot.py          # 메인 봇 스크립트
├── requirements.txt        # Python 의존성
├── .env.example            # 환경 변수 템플릿
└── .github/workflows/
    └── weather.yml         # GitHub Actions 워크플로우
```

## 📄 License

MIT
