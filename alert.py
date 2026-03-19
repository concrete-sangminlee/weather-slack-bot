"""긴급 날씨 알림 — 3시간마다 극단적 기상 조건 체크 (config.yml 임계값 사용)"""
import os
import sys
from datetime import datetime

import requests
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from weather_bot import (
    _request_with_retry, fetch_weather, fetch_air_quality, _get_channels,
    kmh_to_ms, WMO_DESCRIPTIONS, WEATHER_EMOJIS,
    CITY_LAT, CITY_LON, CITY_NAME, TIMEZONE, CONFIG,
    __version__,
)

load_dotenv()

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]

# config.yml 임계값 (기본값 포함)
THRESHOLDS = CONFIG.get("alerts", {})
T_HIGH = THRESHOLDS.get("temp_high", 35)
T_LOW = THRESHOLDS.get("temp_low", -15)
W_SPEED = THRESHOLDS.get("wind_speed", 14)
W_GUST = THRESHOLDS.get("wind_gust", 25)
P_HEAVY = THRESHOLDS.get("precip_heavy", 30)
P_MOD = THRESHOLDS.get("precip_moderate", 10)
AQI_DANGER = THRESHOLDS.get("aqi_danger", 200)
AQI_WARN = THRESHOLDS.get("aqi_warn", 150)


def check_alerts():
    """극단적 기상 조건 체크, 알림 리스트 반환"""
    data = fetch_weather()
    cur = data["current"]

    temp = cur["temperature_2m"]
    feels = cur["apparent_temperature"]
    wind = kmh_to_ms(cur["wind_speed_10m"])
    gust = kmh_to_ms(cur["wind_gusts_10m"])
    code = cur["weather_code"]
    precip = cur["precipitation"]
    _, cat = WMO_DESCRIPTIONS.get(code, ("", "Clear"))

    alerts = []

    if temp >= T_HIGH:
        alerts.append(("🔥", "폭염 경보", f"현재 기온 *{temp}°C* (체감 {feels}°C). 야외 활동을 즉시 중단하세요."))
    elif temp <= T_LOW:
        alerts.append(("🥶", "한파 경보", f"현재 기온 *{temp}°C* (체감 {feels}°C). 동파 방지, 외출 자제."))

    if wind >= W_SPEED or gust >= W_GUST:
        alerts.append(("🌪️", "강풍 경보", f"풍속 *{wind} m/s* (돌풍 {gust} m/s). 간판·구조물 낙하 위험!"))

    if precip >= P_HEAVY:
        alerts.append(("🌊", "폭우 경보", f"현재 강수량 *{precip} mm*. 저지대 침수 위험, 대피 준비."))
    elif precip >= P_MOD:
        alerts.append(("☔", "호우 주의", f"현재 강수량 *{precip} mm*. 우산 필수."))

    if cat == "Thunderstorm":
        alerts.append(("⛈️", "뇌우 경보", "낙뢰 위험! 즉시 실내로 대피하세요."))

    try:
        air = fetch_air_quality()
        aqi = air["current"].get("us_aqi")
        pm25 = air["current"].get("pm2_5")
        if aqi and aqi > AQI_DANGER:
            alerts.append(("🚨", "대기질 매우 나쁨", f"AQI *{aqi}*, PM2.5 *{pm25}* µg/m³. 외출 자제, KF94 마스크 필수!"))
        elif aqi and aqi > AQI_WARN:
            alerts.append(("😷", "대기질 나쁨", f"AQI *{aqi}*, PM2.5 *{pm25}* µg/m³. 민감군 외출 자제."))
    except Exception:
        pass

    return alerts


def send_alerts(alerts):
    if not alerts:
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🚨 {CITY_NAME} 긴급 날씨 알림", "emoji": True},
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"🕐 {now}"}],
        },
        {"type": "divider"},
    ]

    for emoji, title, desc in alerts:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"{emoji} *{title}*\n{desc}"},
        })

    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"v{__version__} · <https://github.com/concrete-sangminlee/weather-slack-bot|GitHub>"},
        ],
    })

    client = WebClient(token=SLACK_BOT_TOKEN)
    for channel in _get_channels():
        client.chat_postMessage(
            channel=channel,
            text=f"{CITY_NAME} 긴급 날씨 알림",
            blocks=blocks,
        )


def main():
    try:
        alerts = check_alerts()
        if alerts:
            send_alerts(alerts)
            print(f"긴급 알림 {len(alerts)}건 전송!")
        else:
            print("긴급 상황 없음.")
    except Exception as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
