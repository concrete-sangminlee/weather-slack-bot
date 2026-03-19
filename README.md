# ☀️ Weather Slack Bot

The most comprehensive weather bot for Slack. 30+ data points, smart insights, lifestyle indices, personality — all fully automated.

**No API keys. No servers. Fork → 2 secrets → done.**

<img src="https://raw.githubusercontent.com/concrete-sangminlee/weather-slack-bot/main/docs/badge.svg" alt="Current Weather"> <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white" alt="Python"> <img src="https://img.shields.io/badge/Slack-Bot-4A154B?logo=slack&logoColor=white" alt="Slack"> <img src="https://img.shields.io/github/actions/workflow/status/concrete-sangminlee/weather-slack-bot/weather.yml?label=Daily&logo=githubactions&logoColor=white" alt="Daily"> <img src="https://img.shields.io/github/actions/workflow/status/concrete-sangminlee/weather-slack-bot/test.yml?label=Tests%20%2857%29&logo=pytest&logoColor=white" alt="Tests"> <img src="https://img.shields.io/badge/ruff-passing-brightgreen?logo=ruff&logoColor=white" alt="Ruff"> <img src="https://img.shields.io/badge/i18n-ko%20%7C%20en%20%7C%20ja-blue" alt="i18n"> <img src="https://img.shields.io/github/v/release/concrete-sangminlee/weather-slack-bot" alt="Release"> <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT">

---

## What You Get

Every morning at 7 AM, your Slack channel receives a rich, color-coded message with:

| Section | What's Included |
|---------|----------------|
| **Summary** | One-line overview + weather personality message |
| **Temperature** | Current, feels-like, high/low, yesterday comparison, wind chill / heat index |
| **Conditions** | Weather, cloud cover, pressure, humidity, visibility |
| **Precipitation** | Probability, expected amount, wind speed + gusts |
| **Sun & Moon** | Sunrise/sunset, daylight progress bar, sunshine hours, UV, moon phase, golden hour |
| **Air Quality** | AQI, PM2.5, PM10, O₃, CO, NO₂ |
| **Forecasts** | 6-hour hourly, 3-day outlook, 7-day trend chart |
| **Comfort Timeline** | Hourly comfort bar 07–21h (🟩🟨🟧🟥) |
| **Lifestyle** | Score (A+–F), discomfort index, laundry/car wash/food safety indices |
| **Recommendations** | 11-tier outfit, activity suggestions, health warnings |
| **Alerts** | Tomorrow weather change, extreme weather monitoring (every 3h) |
| **Personality** | Mood-aware messages, seasonal/holiday awareness (25+), daily quotes |

> **Dynamic bot identity** — bot icon and name change with weather (☀️ sunny, 🌧️ rain, ❄️ snow...)

---

## Quick Start (3 minutes)

### Option A: Slack Bot Token (recommended)

1. **Fork** this repo
2. Create a [Slack App](https://api.slack.com/apps) → add `chat:write` + `files:write` → Install → copy `xoxb-` token
3. Invite bot to channel: `/invite @bot-name`
4. Set **GitHub Secrets**: `SLACK_BOT_TOKEN` + `SLACK_CHANNEL`

### Option B: Webhook (simpler)

1. **Fork** this repo
2. Create an [Incoming Webhook](https://api.slack.com/messaging/webhooks) → copy URL
3. Set **GitHub Secret**: `SLACK_WEBHOOK_URL`

**Done!** Bot runs daily at 7 AM KST. Test now: **Actions → Seoul Weather Bot → Run workflow**

---

## CLI (9 commands)

```bash
weather-bot daily [--dry-run]    # Full briefing
weather-bot digest [--dry-run]   # 3-line compact summary
weather-bot weekly               # Past 7 days + next 7 days
weather-bot alert                # Extreme weather check
weather-bot chart                # Temperature trend chart (PNG)
weather-bot export               # Markdown report
weather-bot json                 # Structured JSON data
weather-bot history              # Log today + show stats
weather-bot version              # Version info
```

---

## Configuration

All settings in `config.yml` — no code changes needed:

```yaml
city:
  name: 서울
  latitude: 37.5665
  longitude: 126.9780

locale: ko                  # ko, en, ja
timezone: Asia/Seoul

forecast:
  hourly_hours: 6
  daily_days: 3
  trend_days: 7
  past_days: 1

display:
  show_air_quality: true
  show_hourly: true
  show_daily_forecast: true
  show_yesterday_comparison: true
  show_best_time: true
  show_weekly_trend: true
  show_golden_hour: true
  show_city_comparison: true

alerts:                     # Customizable thresholds
  temp_high: 35
  temp_low: -15
  wind_speed: 14
  aqi_danger: 200

compare_cities:             # Up to 3 cities
  # - name: Tokyo
  #   latitude: 35.6762
  #   longitude: 139.6503
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Weather | [Open-Meteo](https://open-meteo.com/) — free, no API key |
| Air Quality | [Open-Meteo Air Quality](https://open-meteo.com/en/docs/air-quality-api) |
| Slack | [slack-sdk](https://slack.dev/python-slack-sdk/) + Webhook support |
| Charts | [matplotlib](https://matplotlib.org/) |
| Scheduler | GitHub Actions (cron) |
| Language | Python 3.10+ |

---

## Project Structure

```
├── cli.py                      # Unified CLI (9 commands)
├── weather_bot.py              # Core — daily weather briefing
├── weekly_summary.py           # Weekly summary
├── alert.py                    # Extreme weather alerts
├── chart.py                    # Temperature trend chart
├── history.py                  # Weather history logging
├── config.yml                  # All settings
├── locales/                    # i18n (ko, en, ja)
├── pyproject.toml              # Package metadata + tool config
├── Dockerfile                  # Container support
├── Makefile                    # Dev shortcuts
├── tests/                      # 53 automated tests
├── docs/                       # GitHub Pages
├── CHANGELOG.md                # Full version history
├── CONTRIBUTING.md             # Contribution guide
├── CODE_OF_CONDUCT.md          # Community standards
├── SECURITY.md                 # Security policy
└── .github/
    ├── workflows/              # 6 workflows
    │   ├── weather.yml         # Daily (7 AM KST)
    │   ├── weekly.yml          # Weekly (Sun 9 PM KST)
    │   ├── alert.yml           # Alerts (every 3h)
    │   ├── test.yml            # CI (lint + test × 3 Python versions)
    │   ├── pages.yml           # GitHub Pages
    │   └── publish.yml         # PyPI publish on release
    ├── ISSUE_TEMPLATE/         # Bug report & feature request
    └── dependabot.yml          # Auto dependency updates
```

---

## Development

```bash
git clone https://github.com/concrete-sangminlee/weather-slack-bot.git
cd weather-slack-bot
make install                    # Install dependencies
make test                       # Run 53 tests
make lint                       # Run ruff linter
make run                        # Send daily weather
weather-bot daily --dry-run     # Preview without sending
```

---

## License

[MIT](LICENSE) — free to use, modify, and share.
