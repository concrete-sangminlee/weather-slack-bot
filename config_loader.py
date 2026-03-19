"""설정 로딩 모듈 — config.yml + locales + 환경변수"""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

_ROOT = Path(__file__).parent

# config.yml
_CONFIG_PATH = _ROOT / "config.yml"
with open(_CONFIG_PATH, encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

# locale
_LOCALE = CONFIG.get("locale", "ko")
_LOCALE_PATH = _ROOT / "locales" / f"{_LOCALE}.yml"
with open(_LOCALE_PATH, encoding="utf-8") as f:
    L = yaml.safe_load(f)

# Slack
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "#weather")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

# City
CITY_NAME = CONFIG["city"]["name"]
CITY_LAT = CONFIG["city"]["latitude"]
CITY_LON = CONFIG["city"]["longitude"]
TIMEZONE = CONFIG["timezone"]

# Forecast
HOURLY_HOURS = CONFIG["forecast"]["hourly_hours"]
DAILY_DAYS = CONFIG["forecast"]["daily_days"]
PAST_DAYS = CONFIG["forecast"]["past_days"]
TREND_DAYS = CONFIG["forecast"].get("trend_days", 7)

# Display
DISPLAY = CONFIG["display"]
