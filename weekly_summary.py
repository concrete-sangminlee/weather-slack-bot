"""주간 날씨 요약 — 일요일 저녁에 한 주를 되돌아보고 다음 주를 전망"""
import os
import sys
from datetime import datetime

import requests
import yaml
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from pathlib import Path

from weather_bot import (
    _request_with_retry, kmh_to_ms, WMO_DESCRIPTIONS, WEATHER_EMOJIS,
    CITY_LAT, CITY_LON, CITY_NAME, TIMEZONE, CONFIG, DISPLAY,
    __version__, L,
)

load_dotenv()

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "#weather")


def fetch_weekly_data():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": CITY_LAT,
        "longitude": CITY_LON,
        "daily": ",".join([
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "weather_code",
            "wind_speed_10m_max",
            "uv_index_max",
        ]),
        "timezone": TIMEZONE,
        "past_days": 7,
        "forecast_days": 7,
    }
    return _request_with_retry(url, params)


def build_weekly_summary():
    data = fetch_weekly_data()
    daily = data["daily"]

    WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]

    # 지난주 데이터 (index 0~6)
    past_lines = []
    past_temps_max = []
    past_temps_min = []
    past_precip_total = 0
    past_rainy_days = 0

    for i in range(7):
        dt = datetime.fromisoformat(daily["time"][i])
        day = WEEKDAYS[dt.weekday()]
        code = daily["weather_code"][i]
        desc, cat = WMO_DESCRIPTIONS.get(code, ("?", "Clear"))
        emoji = WEATHER_EMOJIS.get(cat, ":thermometer:")
        t_max = daily["temperature_2m_max"][i]
        t_min = daily["temperature_2m_min"][i]
        precip = daily["precipitation_sum"][i]

        past_temps_max.append(t_max)
        past_temps_min.append(t_min)
        past_precip_total += precip
        if precip > 0.5:
            past_rainy_days += 1

        past_lines.append(f"`{dt.month}/{dt.day}({day})` {emoji} {t_min:+.0f}° ~ {t_max:+.0f}° {'| ' + str(round(precip, 1)) + 'mm' if precip > 0.5 else ''}")

    avg_max = sum(past_temps_max) / 7
    avg_min = sum(past_temps_min) / 7
    highest = max(past_temps_max)
    lowest = min(past_temps_min)

    # 다음주 전망 (index 7~13)
    next_lines = []
    for i in range(7, min(14, len(daily["time"]))):
        dt = datetime.fromisoformat(daily["time"][i])
        day = WEEKDAYS[dt.weekday()]
        code = daily["weather_code"][i]
        desc, cat = WMO_DESCRIPTIONS.get(code, ("?", "Clear"))
        emoji = WEATHER_EMOJIS.get(cat, ":thermometer:")
        t_max = daily["temperature_2m_max"][i]
        t_min = daily["temperature_2m_min"][i]
        next_lines.append(f"`{dt.month}/{dt.day}({day})` {emoji} {desc}  {t_min:+.0f}° ~ {t_max:+.0f}°")

    today = datetime.now().strftime("%Y년 %m월 %d일")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f":bar_chart: {CITY_NAME} 주간 날씨 요약", "emoji": True},
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f":calendar: {today}"}],
        },
        {"type": "divider"},

        # 지난주 통계
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*:rewind: 지난 7일 요약*"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f":thermometer: *평균 기온*\n{avg_min:.1f}° ~ {avg_max:.1f}°"},
                {"type": "mrkdwn", "text": f":chart_with_upwards_trend: *최고/최저*\n{highest}° / {lowest}°"},
                {"type": "mrkdwn", "text": f":rain_cloud: *강수*\n{past_precip_total:.1f}mm ({past_rainy_days}일)"},
                {"type": "mrkdwn", "text": f":sunny: *맑은 날*\n{7 - past_rainy_days}일"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(past_lines)},
        },
        {"type": "divider"},

        # 다음주 전망
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*:fast_forward: 다음 7일 전망*"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(next_lines) if next_lines else "데이터 없음"},
        },

        # 푸터
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"v{__version__} · Powered by Open-Meteo API | <https://github.com/concrete-sangminlee/weather-slack-bot|GitHub>"},
            ],
        },
    ]

    return blocks


def main():
    try:
        blocks = build_weekly_summary()
        client = WebClient(token=SLACK_BOT_TOKEN)
        client.chat_postMessage(
            channel=SLACK_CHANNEL,
            text=f"{CITY_NAME} 주간 날씨 요약",
            blocks=blocks,
        )
        print("주간 요약 전송 완료!")
    except Exception as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
