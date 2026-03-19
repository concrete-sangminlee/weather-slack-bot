# ☀️ Seoul Weather Slack Bot

A Slack bot that delivers a comprehensive daily weather briefing for Seoul every morning — fully automated with GitHub Actions.

No API keys needed. No servers to maintain. Just fork, set two secrets, and go.

<img src="https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white" alt="Python"> <img src="https://img.shields.io/badge/Slack-Bot-4A154B?logo=slack&logoColor=white" alt="Slack"> <img src="https://img.shields.io/github/actions/workflow/status/concrete-sangminlee/weather-slack-bot/weather.yml?label=Daily%20Weather&logo=githubactions&logoColor=white" alt="Workflow Status"> <img src="https://img.shields.io/badge/API-Open--Meteo-orange" alt="Open-Meteo"> <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License">

## 📱 Slack Message Preview

```
☀️ 서울 오늘의 날씨
━━━━━━━━━━━━━━━━━━━━

🌡️ 기온
  현재: 9.5°C (체감 6.3°C)
  최고: 12.1°C / 최저: -1.6°C

🌤️ 날씨
  상태: 맑음 | 구름량: 10% | 기압: 1018.4 hPa

💧 습도 & 강수
  습도: 34% | 강수 확률: 0%

💨 바람
  풍속: 8.6 km/h (돌풍 38.2 km/h) | 풍향: 서

☀️ 일조 & 자외선
  일출: 06:37 / 일몰: 18:42
  자외선 지수: 5.9 (높음)

━━━━━━━━━━━━━━━━━━━━
💡 오늘의 팁
  • 🍃 좋은 하루 보내세요!
```

## ✨ Features

- **Comprehensive weather data** — temperature (current / high / low / feels-like), cloud cover, pressure, humidity, precipitation (amount / probability / duration), wind (speed / gusts / direction), sunrise & sunset, daylight & sunshine hours, UV index, solar radiation
- **Context-aware daily tips** — rain, snow, heatwave, cold snap, UV exposure, strong wind alerts
- **Fully automated** — runs every day at 7:00 AM KST via GitHub Actions cron
- **No API key required** — powered by [Open-Meteo](https://open-meteo.com/), a free and open-source weather API
- **Manual trigger** — run anytime from the Actions tab

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Weather API | [Open-Meteo](https://open-meteo.com/) — free, no API key needed |
| Slack SDK | [slack-sdk](https://slack.dev/python-slack-sdk/) for Python |
| Scheduler | GitHub Actions (cron schedule) |
| Language | Python 3.12 |

## 🚀 Quick Start

### 1. Fork this repo

Click the **Fork** button at the top right of this page.

### 2. Create a Slack App

1. Go to [Slack API](https://api.slack.com/apps) → **Create New App** → From scratch
2. Navigate to **OAuth & Permissions** → add `chat:write` to Bot Token Scopes
3. Click **Install to Workspace** and copy the `xoxb-` Bot Token
4. Invite the bot to your target channel: `/invite @your-bot-name`

### 3. Set GitHub Secrets

Go to your forked repo → **Settings** → **Secrets and variables** → **Actions**, and add:

| Secret | Value |
|--------|-------|
| `SLACK_BOT_TOKEN` | Your `xoxb-...` bot token |
| `SLACK_CHANNEL` | Channel name without `#` (e.g. `general`) |

Or use the CLI:

```bash
gh secret set SLACK_BOT_TOKEN
gh secret set SLACK_CHANNEL
```

### 4. Done!

The bot will automatically send a weather message every day at 7:00 AM KST.

To test immediately: **Actions** tab → **Seoul Weather Bot** → **Run workflow**

## 🌍 Customization

Want to change the city? Edit the coordinates in `weather_bot.py`:

```python
SEOUL_LAT = 37.5665  # Change to your city's latitude
SEOUL_LON = 126.9780  # Change to your city's longitude
```

Want to change the schedule? Edit the cron expression in `.github/workflows/weather.yml`:

```yaml
schedule:
  - cron: '0 22 * * *'  # UTC time (22:00 UTC = 07:00 KST)
```

## 📁 Project Structure

```
├── weather_bot.py              # Main bot script
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template (for local dev)
└── .github/workflows/
    └── weather.yml             # GitHub Actions workflow
```

## 📄 License

MIT — feel free to use, modify, and share.
