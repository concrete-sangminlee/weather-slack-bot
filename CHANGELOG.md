# Changelog

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
