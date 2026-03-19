# Weather Slack Bot

A daily weather briefing bot for Slack. Delivers 30+ weather data points, air quality, lifestyle indices, forecasts, outfit recommendations, and health alerts — fully automated through GitHub Actions. No API keys required, no servers to manage.

<img src="https://raw.githubusercontent.com/concrete-sangminlee/weather-slack-bot/main/docs/badge.svg" alt="Current Weather"> <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white" alt="Python"> <img src="https://img.shields.io/badge/Slack-Bot-4A154B?logo=slack&logoColor=white" alt="Slack"> <img src="https://img.shields.io/github/actions/workflow/status/concrete-sangminlee/weather-slack-bot/weather.yml?label=Daily&logo=githubactions&logoColor=white" alt="Daily"> <img src="https://img.shields.io/github/actions/workflow/status/concrete-sangminlee/weather-slack-bot/test.yml?label=Tests%20%2891%29&logo=pytest&logoColor=white" alt="Tests"> <img src="https://img.shields.io/badge/ruff-passing-brightgreen?logo=ruff&logoColor=white" alt="Ruff"> <img src="https://img.shields.io/badge/i18n-ko%20%7C%20en%20%7C%20ja-blue" alt="i18n"> <img src="https://img.shields.io/github/v/release/concrete-sangminlee/weather-slack-bot" alt="Release"> <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT">

---

## Overview

Every morning at 7 AM (KST), the bot sends a rich Slack message covering:

| Category | Details |
|----------|---------|
| **Temperature** | Current, feels-like, daily high/low, yesterday comparison, wind chill (JAG/TI), heat index (Rothfusz) |
| **Conditions** | Weather description, cloud cover, pressure, humidity, visibility, dew point |
| **Precipitation & Wind** | Rain probability, expected rainfall, wind speed, gusts, direction |
| **Sun & Moon** | Sunrise/sunset with daylight progress bar, sunshine hours, UV index, solar radiation, moon phase, golden hour |
| **Air Quality** | US AQI, PM2.5, PM10, ozone, CO, NO2 |
| **Forecasts** | 6-hour hourly, 3-day outlook, 7-day temperature trend with chart |
| **Comfort Timeline** | Hourly comfort score visualized from 07:00 to 21:00 |
| **Lifestyle Indices** | Composite score (A+ to F), discomfort index, laundry/car wash/food safety ratings |
| **Recommendations** | 11-tier outfit suggestion, activity ideas, 5 types of health risk warnings |
| **Alerts** | Tomorrow weather change prediction, extreme weather monitoring every 3 hours |
| **Personality** | Mood-aware daily messages, 25+ seasonal and holiday greetings, weather quotes |

At noon, a compact 3-line digest is sent as a quick update.

---

## Quick Start

### Option A: Bot Token (full features)

1. Fork this repository
2. Create a [Slack App](https://api.slack.com/apps) with `chat:write` and `files:write` scopes, install it, and copy the bot token
3. Invite the bot to your channel with `/invite @bot-name`
4. Add `SLACK_BOT_TOKEN` and `SLACK_CHANNEL` as GitHub Secrets

### Option B: Incoming Webhook (simpler setup)

1. Fork this repository
2. Create an [Incoming Webhook](https://api.slack.com/messaging/webhooks) and copy the URL
3. Add `SLACK_WEBHOOK_URL` as a GitHub Secret

Test immediately: **Actions > Seoul Weather Bot > Run workflow**

---

## CLI

```bash
weather-bot daily [--dry-run]     # Full daily briefing
weather-bot digest [--dry-run]    # Compact 3-line summary
weather-bot weekly                # Weekly summary (past + next 7 days)
weather-bot alert                 # Check for extreme weather conditions
weather-bot chart                 # Generate temperature trend chart
weather-bot export                # Output as Markdown
weather-bot json                  # Output as JSON
weather-bot history               # Log today's weather and show statistics
weather-bot analytics             # Full history analysis report
weather-bot compare               # Compare last two recorded days
weather-bot stats                 # Project and weather statistics
weather-bot setup                 # Interactive setup wizard
weather-bot version               # Show version
```

---

## Configuration

All settings are managed through `config.yml`:

```yaml
city:
  name: Seoul
  latitude: 37.5665
  longitude: 126.9780

locale: ko                       # ko, en, ja
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

alerts:
  temp_high: 35
  temp_low: -15
  wind_speed: 14
  aqi_danger: 200

compare_cities:
  # - name: Tokyo
  #   latitude: 35.6762
  #   longitude: 139.6503
```

---

## Automated Schedule

| Time (KST) | Workflow | Description |
|-------------|----------|-------------|
| 07:00 | `weather.yml` | Full weather briefing to Slack |
| 07:05 | `badge.yml` | Update dynamic weather badge |
| 07:10 | `history.yml` | Save daily weather snapshot |
| 12:00 | `digest.yml` | Compact noon digest |
| Every 3h | `alert.yml` | Extreme weather monitoring |
| Sun 21:00 | `weekly.yml` | Weekly summary |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Weather Data | [Open-Meteo](https://open-meteo.com/) (free, no API key) |
| Air Quality | [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api) |
| Slack Integration | [slack-sdk](https://slack.dev/python-slack-sdk/) and Incoming Webhooks |
| Charts | [matplotlib](https://matplotlib.org/) |
| Scheduling | GitHub Actions cron |
| Runtime | Python 3.10+ |

---

## Project Structure

```
cli.py                         Unified CLI with 13 commands
weather_bot.py                 Core daily weather briefing
weekly_summary.py              Weekly summary generator
alert.py                       Extreme weather alert checker
chart.py                       Temperature trend chart (matplotlib)
history.py                     Weather history logging (90-day JSON)
badge.py                       Dynamic SVG weather badge
config_loader.py               Configuration and locale loader
config.yml                     All user-configurable settings
locales/                       Language packs (ko, en, ja)
tests/                         91 automated tests (unit + E2E)
docs/                          GitHub Pages and badge assets
pyproject.toml                 Package metadata, ruff and pytest config
Dockerfile                     Container support
Makefile                       Development shortcuts
CHANGELOG.md                   Full version history
CONTRIBUTING.md                Contribution guide
CODE_OF_CONDUCT.md             Community standards
SECURITY.md                    Security policy
.github/workflows/             9 automated workflows
.github/ISSUE_TEMPLATE/        Bug report and feature request forms
.github/dependabot.yml         Dependency update automation
```

---

## Development

```bash
git clone https://github.com/concrete-sangminlee/weather-slack-bot.git
cd weather-slack-bot
make install                      # Install dependencies
make test                         # Run 91 tests
make lint                         # Run ruff linter
weather-bot daily --dry-run       # Preview without sending
weather-bot setup                 # Interactive configuration
```

---

## License

[MIT](LICENSE)
