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


def require_slack_token():
    """Bot Token 모드에 필요한 SLACK_BOT_TOKEN을 반환한다.

    import 시점이 아니라 실제 전송 직전에 호출해 누락 시 명확한 오류를 낸다.
    (직접 os.environ["SLACK_BOT_TOKEN"]로 읽으면 import 시 KeyError가 발생)"""
    if not SLACK_BOT_TOKEN:
        raise RuntimeError(
            "SLACK_BOT_TOKEN 환경변수가 설정되지 않았습니다. "
            ".env 또는 CI 시크릿에 xoxb- 토큰을 설정하세요."
        )
    return SLACK_BOT_TOKEN


def validate_config():
    """설정 파일 검증"""
    errors = []
    if not (-90 <= CITY_LAT <= 90):
        errors.append(f"위도 범위 오류: {CITY_LAT} (±90)")
    if not (-180 <= CITY_LON <= 180):
        errors.append(f"경도 범위 오류: {CITY_LON} (±180)")
    if not (1 <= DAILY_DAYS <= 16):
        errors.append(f"daily_days 범위 오류: {DAILY_DAYS} (1~16)")
    if not (0 <= PAST_DAYS <= 7):
        errors.append(f"past_days 범위 오류: {PAST_DAYS} (0~7)")
    if SLACK_BOT_TOKEN and not SLACK_BOT_TOKEN.startswith("xoxb-"):
        if SLACK_BOT_TOKEN != "test":
            errors.append("SLACK_BOT_TOKEN은 'xoxb-'로 시작해야 합니다")
    return errors


# 자동 검증 (import 시)
_errors = validate_config()
if _errors:
    import sys
    for e in _errors:
        print(f"⚠️ config 오류: {e}", file=sys.stderr)
