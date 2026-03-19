# ☀️ Seoul Weather Slack Bot

A comprehensive daily weather briefing delivered to Slack every morning — with 30+ data points, smart insights, lifestyle indices, and personality. Fully automated with GitHub Actions.

No API keys. No servers. Just fork, set two secrets, and go.

<img src="https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white" alt="Python"> <img src="https://img.shields.io/badge/Slack-Bot-4A154B?logo=slack&logoColor=white" alt="Slack"> <img src="https://img.shields.io/github/actions/workflow/status/concrete-sangminlee/weather-slack-bot/weather.yml?label=Daily%20Weather&logo=githubactions&logoColor=white" alt="Workflow Status"> <img src="https://img.shields.io/github/actions/workflow/status/concrete-sangminlee/weather-slack-bot/test.yml?label=Tests%20%2844%29&logo=pytest&logoColor=white" alt="Tests"> <img src="https://img.shields.io/badge/ruff-passing-brightgreen?logo=ruff&logoColor=white" alt="Ruff"> <img src="https://img.shields.io/badge/API-Open--Meteo-orange" alt="Open-Meteo"> <img src="https://img.shields.io/badge/i18n-ko%20%7C%20en%20%7C%20ja-blue" alt="i18n"> <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License"> <img src="https://img.shields.io/github/v/release/concrete-sangminlee/weather-slack-bot" alt="Release">

---

## 📱 Slack Message Preview

```
☀️ 서울 오늘의 날씨
━━━━━━━━━━━━━━━━━━━━

🌡️ 기온
  현재: 9.3°C (체감 5.8°C)
  최고: 9.9°C (체감 7.5°C)
  최저: -1.6°C (체감 -5.5°C)

🌤️ 날씨
  상태: 맑음
  구름량: 10%
  기압: 1018.4 hPa

💧 습도 & 강수
  습도: 35%
  현재 강수량: 0.0 mm
  오늘 예상 강수량: 0.0 mm (비 0.0 mm / 눈 0.0 cm)
  강수 확률: 0%
  강수 예상 시간: 0.0시간

💨 바람
  풍속: 2.5 m/s (돌풍 10.9 m/s)
  풍향: 서
  오늘 최대 풍속: 2.6 m/s (돌풍 11.4 m/s, 서풍)

☀️ 일조 & 자외선
  일출: 06:37 / 일몰: 18:42
  낮 길이: 12시간 4분
  일조 시간: 10시간 57분
  자외선 지수: 5.9 (높음 😎)
  일사량: 21.01 MJ/m²

🕐 시간별 예보
  16시 ☀️ 8.3°C  💧0%  💨2.3m/s
  17시 ☀️ 7.1°C  💧0%  💨2.6m/s
  18시 ☀️ 5.8°C  💧0%  💨2.4m/s
  ...

📅 3일 예보
  3/19(목) ☀️ 대체로 맑음  ⬇️-1.6°C ⬆️9.9°C  💧0%
  3/20(금) ☀️ 맑음        ⬇️0.4°C  ⬆️12.2°C 💧0%
  3/21(토) ☁️ 흐림        ⬇️-0.8°C ⬆️13.2°C 💧0%

━━━━━━━━━━━━━━━━━━━━
💡 오늘의 팁
  • 🧤 약간 쌀쌀해요. 겉옷 하나 걸치세요.
  • 🌡️ 일교차가 12°C로 큽니다. 얇은 겉옷을 챙기세요.
  • 😎 자외선 보통. 장시간 야외 활동 시 선크림 추천.
```

> Note: The actual Slack message uses [Block Kit](https://api.slack.com/block-kit) rich formatting with structured layouts, emoji icons, and clean section dividers.

---

## ✨ Features

### Weather Data

Every message includes **20+ data points** across 5 categories:

| Category | Data |
|----------|------|
| **Temperature** | Current, feels-like, daily high / low, feels-like high / low |
| **Sky** | Weather condition, cloud cover (%), pressure (hPa), visibility (km), dew point (°C) |
| **Humidity & Precipitation** | Humidity (%), current / total rainfall, snowfall, rain probability, precipitation hours |
| **Wind** | Speed (m/s), gusts, direction, daily max speed / gusts / dominant direction |
| **Sun & UV** | Sunrise, sunset, daylight duration, sunshine hours, UV index, solar radiation (MJ/m²) |
| **Air Quality** | US AQI, PM2.5 (fine dust), PM10, CO, NO₂, O₃ |

### Hourly & Multi-Day Forecast

| Forecast | Details |
|----------|---------|
| **Hourly** | Next 6 hours — temperature, precipitation probability, wind speed |
| **3-Day Outlook** | Daily summary — weather, high / low temp, precipitation probability |
| **Yesterday** | Temperature change vs. yesterday (high / low delta) |

### Smart Insights

| Feature | Description |
|---------|-------------|
| **Quick Summary** | One-line overview at the top for a quick glance |
| **Lifestyle Index** | 0–100 composite score with visual progress bar |
| **Best Outdoor Time** | Optimal hour to go outside based on hourly analysis |
| **Outfit Recommendation** | 11-tier clothing suggestion based on feels-like temp |
| **Activity Suggestions** | Weather-appropriate activities (indoor/outdoor) |
| **Health Risks** | Flu, heatstroke, frostbite, respiratory, UV burn warnings |
| **Tomorrow Alert** | Advance warning when tomorrow's weather changes significantly |
| **Weekly Trend** | 7-day temperature trend mini-chart with color bars |
| **Time-aware Greeting** | Header changes based on time of day |
| **Discomfort Index** | Thom's DI — real feel combining temp + humidity (Korean 불쾌지수) |
| **Laundry Index** | Will your laundry dry today? Based on temp, humidity, wind, rain |
| **Car Wash Index** | Should you wash your car? Based on rain forecast + dust levels |
| **Food Safety Index** | Food poisoning risk level based on temp + humidity |
| **Error Notifications** | Slack alert with error details when the bot fails |

### Smart Daily Tips

Over **30 context-aware tip presets** that adapt to weather conditions:

| Condition | Example Tip |
|-----------|-------------|
| Heavy rain (30mm+) | 🌊 Flood warning — stay indoors |
| Snow (5cm+) | ☃️ Heavy snow — use public transit |
| Freezing + rain chance | 🧊 Black ice warning |
| Extreme cold (-10°C↓) | 🥶 Pipe freezing risk, minimize exposed skin |
| Heatwave (35°C+) | 🔥 Avoid outdoor activities, stay hydrated |
| Temp swing (15°C+) | 🌡️ Layer up, cold risk |
| Dry air (≤20%) | 🏜️ Apply moisturizer, drink water |
| High humidity (≥90%) | 💦 Dry laundry indoors |
| UV extreme (11+) | ☠️ SPF50+ sunscreen mandatory |
| Strong wind (14+ m/s) | 🌪️ Watch for falling signs/structures |
| Gusts (20+ m/s) | ⚠️ Loose objects may blow away |
| Fog | 🌫️ Use headlights, drive slowly |
| Overcast (90%+) | ☁️ Grab a warm drink |
| PM2.5 bad (>35 µg/m³) | 😷 Wear a mask outdoors |
| PM2.5 very bad (>75) | 🚫 Stay indoors, KF94 mask required |
| AQI unhealthy (>150) | 😷 Sensitive groups reduce outdoor time |
| Perfect weather | 🌈 Perfect day for a walk! |

### Automation & Quality

- **Slack Block Kit** — rich card layout with structured sections, not plain text
- **Fully automated** — runs daily at 7:00 AM KST via GitHub Actions cron
- **Manual trigger** — run anytime from the Actions tab with one click
- **Zero infrastructure** — no server, no database, no API key, no cost
- **CI/CD** — automated test suite (26 tests) runs on every push
- **Retry logic** — up to 3 retries with backoff on API failures
- **Graceful degradation** — air quality API failure doesn't block weather delivery

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Weather API | [Open-Meteo](https://open-meteo.com/) — free, open-source, no API key |
| Slack | [slack-sdk](https://slack.dev/python-slack-sdk/) for Python |
| Scheduler | GitHub Actions cron |
| Language | Python 3.12 |

---

## 🚀 Quick Start

### 1. Fork this repo

Click the **Fork** button at the top right.

### 2. Create a Slack App

1. Go to [Slack API](https://api.slack.com/apps) → **Create New App** → From scratch
2. **OAuth & Permissions** → add `chat:write` and `files:write` (for chart uploads) to Bot Token Scopes
3. **Install to Workspace** → copy the `xoxb-` Bot Token
4. Invite the bot to your channel: `/invite @your-bot-name`

### 3. Set GitHub Secrets

Go to **Settings** → **Secrets and variables** → **Actions**, and add:

| Secret | Value |
|--------|-------|
| `SLACK_BOT_TOKEN` | Your `xoxb-...` bot token |
| `SLACK_CHANNEL` | Channel name without `#` (e.g. `general`) |

Or via CLI:

```bash
gh secret set SLACK_BOT_TOKEN
gh secret set SLACK_CHANNEL
```

### 4. You're all set!

The bot runs every day at **7:00 AM KST** automatically.

Test now: **Actions** → **Seoul Weather Bot** → **Run workflow**

---

## 🌍 Customization

All settings are in `config.yml` — no code changes needed:

```yaml
city:
  name: 서울                    # City display name
  latitude: 37.5665            # Find at maps.google.com → right-click → copy
  longitude: 126.9780

timezone: Asia/Seoul

forecast:
  hourly_hours: 6              # Hours in hourly forecast
  daily_days: 3                # Days in daily forecast (max 7)
  past_days: 1                 # For yesterday comparison (0 to disable)

display:
  show_air_quality: true       # AQI, PM2.5, PM10, pollutants
  show_hourly: true            # Hourly forecast section
  show_daily_forecast: true    # Multi-day forecast section
  show_yesterday_comparison: true  # Yesterday temp comparison
```

### Change Schedule

Edit the cron in `.github/workflows/weather.yml`:

```yaml
schedule:
  - cron: '0 22 * * *'  # UTC time → 22:00 UTC = 07:00 KST
```

> Use [crontab.guru](https://crontab.guru/) to build your cron expression.

### Change Language

The Slack messages are in Korean by default. Edit the strings in `weather_bot.py` (`WMO_DESCRIPTIONS`, `generate_tips`, `get_outfit_recommendation`) to localize.

---

## 📁 Project Structure

```
├── cli.py                      # Unified CLI (daily/weekly/alert/chart/version)
├── weather_bot.py              # Main bot — daily weather briefing
├── weekly_summary.py           # Weekly summary — past 7 days + next 7 days
├── alert.py                    # Extreme weather alert checker
├── chart.py                    # Temperature trend chart generator
├── SECURITY.md                 # Security policy
├── config.yml                  # All settings (city, locale, display, forecast)
├── CHANGELOG.md                # Version history
├── locales/                    # i18n language packs
│   ├── ko.yml                  # Korean (default)
│   ├── en.yml                  # English
│   └── ja.yml                  # Japanese
├── pyproject.toml              # Python package metadata
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container support
├── Makefile                    # Dev shortcuts
├── tests/
│   └── test_weather_bot.py     # 50 unit & integration tests
├── docs/
│   └── index.html              # GitHub Pages landing page
└── .github/
    ├── workflows/
    │   ├── weather.yml         # Daily weather (7 AM KST)
    │   ├── weekly.yml          # Weekly summary (Sun 9 PM KST)
    │   ├── alert.yml           # Extreme weather alerts (every 3h)
    │   ├── test.yml            # CI lint + tests (push & PR)
    │   └── pages.yml           # GitHub Pages deploy
    ├── ISSUE_TEMPLATE/         # Bug report & feature request
    └── dependabot.yml          # Auto dependency updates
```

### Docker

```bash
docker build -t weather-slack-bot .
docker run --env-file .env weather-slack-bot
```

### Makefile

```bash
make run          # Send daily weather
make weekly       # Send weekly summary
make alert        # Check extreme weather
make chart        # Generate trend chart
make version      # Show version
make test         # Run 50 tests
make lint         # Run ruff linter
make install      # Install dependencies
make docker-build # Build Docker image
make docker-run   # Run in Docker
```

---

## 🤝 Contributing

Contributions welcome! Ideas for improvement:

- Add more cities or multi-city support
- Add hourly forecast
- Localize tips to other languages
- Add Slack Block Kit rich formatting

---

## 📄 License

[MIT](LICENSE) — free to use, modify, and share.
