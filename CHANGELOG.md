# Changelog

## v4.1.0 (2026-09-11)

### Fixed
- `pyproject.toml` version now matches the code (`__version__`) — was out of sync
- `get_seasonal_note`: fixed operator-precedence bug so the 장마철(rainy season) message fires on the correct dates
- Timezone handling now uses the standard-library `zoneinfo` instead of a hand-maintained offset map — daylight saving time is respected and unknown zones warn + fall back to Asia/Seoul, with a crash-proof fixed-offset fallback when no tz database is present (`tzdata` added as a dependency for slim containers)
- `calc_golden_hour` uses `timedelta`, avoiding a possible `ValueError` at minute/hour boundaries
- CLI `daily` now passes the weather category to `send_to_slack`, so the per-weather bot icon/name is applied (matching the module entry point)

### Changed
- `SLACK_BOT_TOKEN` is now read once in `config_loader` and validated at send time via `require_slack_token()` — no more import-time `KeyError` in `alert.py` / `weekly_summary.py`
- Extracted a shared `extract_conditions()` / `CurrentConditions` builder in `weather_bot`, removing duplicated data-extraction logic from `cli.py`, `history.py`, and `badge.py`
- Replaced broad `except Exception: pass` blocks with targeted exception handling and stderr warnings
- `matplotlib` is now an optional extra (`pip install weather-slack-bot[chart]`); core install is lighter. Workflows/Dockerfile that render charts install it explicitly
- `requirements.txt` slimmed to core deps; `pyproject.toml` is the canonical dependency source
- CI test workflow runs pytest once (report + coverage threshold combined)

### Added
- Mocked unit tests for the Slack delivery layer, request retry/backoff, timezone/golden-hour/seasonal logic, and token validation

## v3.1.0 (2026-03-19)

### Added
- Slack Webhook support (`SLACK_WEBHOOK_URL` — no bot token needed)
- Weather history logging (`history.py` — saves daily snapshots to JSON, 90-day retention)
- JSON export (`weather-bot json` — structured JSON output)
- Markdown export (`weather-bot export` — MD table format)
- Digest mode in GitHub Actions workflow dropdown
- Multi-Python CI matrix (3.10, 3.11, 3.12)
- `--dry-run` flag for daily & digest commands
- CODE_OF_CONDUCT.md, SECURITY.md

### Changed
- Unified workflow uses `cli.py` as single entry point
- pyproject.toml: `weather-bot` CLI entry point, ruff/pytest config merged
- Type hints on 10+ core functions

## v3.0.0 (2026-03-19)

### Added
- pip-installable package with CLI entry point
- Comfort timeline (07-21h hourly bar)
- Wind chill (JAG/TI) & heat index (Rothfusz)
- Weather grade (A+ to F) with color-coded Slack sidebar
- Seasonal awareness (25+ Korean holidays & culture events)
- Weather personality (mood-aware daily messages)
- Golden hour calculator
- Temperature chart (matplotlib)
- Extreme weather alerts (3-hour monitoring)
- i18n (ko/en/ja)

### Changed
- ALL emoji: Slack shortcodes → Unicode (108 codes)
- Compact layout (40 → ~32 blocks)
- Parallel API calls (ThreadPoolExecutor)

## v2.3.0 (2026-03-19)

### Added
- Weather personality system — mood-aware messages that change tone based on conditions
- Seasonal awareness — Korean holidays (13), seasonal culture messages (cherry blossoms, monsoon, foliage)
- Golden hour calculator for photography
- Temperature trend chart image (matplotlib, uploaded to Slack thread)
- Extreme weather alert system — runs every 3 hours, monitors heatwave/cold/wind/rain/thunderstorm/AQI
- Weekly weather summary — past 7 days stats + next 7 days forecast
- Multi-channel support — send to multiple Slack channels
- Configurable alert thresholds in config.yml
- i18n support — Korean, English, Japanese locale files
- GitHub Pages landing page

### Changed
- ALL Slack emoji shortcodes converted to Unicode emoji (108 codes)
- Compact message layout (40 → 32 blocks)
- Parallel API calls with ThreadPoolExecutor

### Developer Experience
- ruff linting — 0 errors, CI integration
- 44 automated tests with coverage
- Dependabot for auto dependency updates
- GitHub Issue Templates (Bug Report / Feature Request)
- CONTRIBUTING.md guide
- Docker + Makefile support
- pyproject.toml for modern Python packaging

## v2.2.0 (2026-03-19)

### Added
- Compact message layout optimization (40 → 31 blocks)
- Chart image generation with matplotlib
- Extreme weather alert workflow (3-hour checks)
- Slack emoji compatibility fixes (12 non-standard → standard)

## v2.1.0 (2026-03-19)

### Added
- Multi-city weather comparison (parallel API calls)
- i18n framework with ko/en/ja locale files
- GitHub Pages landing page
- Weekly summary script
- GitHub Pages deployment workflow
- pyproject.toml

## v2.0.0 (2026-03-19)

### Added
- Parallel API calls (ThreadPoolExecutor)
- Sunrise/sunset daylight progress bar
- Moon phase display (8 phases, Conway's algorithm)
- Version management system
- GitHub Release

### Changed
- Slack Block Kit rich formatting
- 7-day forecast data

## v1.0.0 (2026-03-19)

### Initial Release
- Seoul weather briefing via Slack
- Open-Meteo API (no API key needed)
- Temperature, humidity, wind, precipitation, UV, air quality
- Hourly forecast (6 hours), 3-day outlook, 7-day trend
- Lifestyle index, outfit recommendation, activity suggestions
- Health risk warnings, tomorrow weather alerts
- Korean lifestyle indices (discomfort, laundry, car wash, food safety)
- 30+ context-aware tip presets
- GitHub Actions daily cron (7 AM KST)
- config.yml for full customization
