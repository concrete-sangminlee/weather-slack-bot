"""긴급 날씨 알림 — 3시간마다 극단적 기상 조건 체크"""
import os
import sys

import requests
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from weather_bot import (
    _request_with_retry, fetch_weather, fetch_air_quality,
    kmh_to_ms, WMO_DESCRIPTIONS, WEATHER_EMOJIS,
    CITY_LAT, CITY_LON, CITY_NAME, TIMEZONE, CONFIG,
    __version__,
)

load_dotenv()

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "#weather")


def check_alerts():
    """극단적 기상 조건 체크, 알림 리스트 반환"""
    data = fetch_weather()
    cur = data["current"]

    temp = cur["temperature_2m"]
    feels = cur["apparent_temperature"]
    humidity = cur["relative_humidity_2m"]
    wind = kmh_to_ms(cur["wind_speed_10m"])
    gust = kmh_to_ms(cur["wind_gusts_10m"])
    code = cur["weather_code"]
    precip = cur["precipitation"]
    _, cat = WMO_DESCRIPTIONS.get(code, ("", "Clear"))

    alerts = []

    # 극한 기온
    if temp >= 35:
        alerts.append((":fire:", "폭염 경보", f"현재 기온 *{temp}°C* (체감 {feels}°C). 야외 활동을 즉시 중단하세요."))
    elif temp <= -15:
        alerts.append((":cold_face:", "한파 경보", f"현재 기온 *{temp}°C* (체감 {feels}°C). 동파 방지, 외출 자제."))

    # 강풍
    if wind >= 14 or gust >= 25:
        alerts.append((":tornado:", "강풍 경보", f"풍속 *{wind} m/s* (돌풍 {gust} m/s). 간판·구조물 낙하 위험!"))

    # 폭우
    if precip >= 30:
        alerts.append((":ocean:", "폭우 경보", f"현재 강수량 *{precip} mm*. 저지대 침수 위험, 대피 준비."))
    elif precip >= 10:
        alerts.append((":umbrella_with_rain_drops:", "호우 주의", f"현재 강수량 *{precip} mm*. 우산 필수."))

    # 뇌우
    if cat == "Thunderstorm":
        alerts.append((":thunder_cloud_and_rain:", "뇌우 경보", "낙뢰 위험! 즉시 실내로 대피하세요."))

    # 대기질
    try:
        air = fetch_air_quality()
        aqi = air["current"].get("us_aqi")
        pm25 = air["current"].get("pm2_5")
        if aqi and aqi > 200:
            alerts.append((":rotating_light:", "대기질 매우 나쁨", f"AQI *{aqi}*, PM2.5 *{pm25}* µg/m³. 외출 자제, KF94 마스크 필수!"))
        elif aqi and aqi > 150:
            alerts.append((":mask:", "대기질 나쁨", f"AQI *{aqi}*, PM2.5 *{pm25}* µg/m³. 민감군 외출 자제."))
    except Exception:
        pass

    return alerts


def send_alerts(alerts):
    if not alerts:
        return

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f":rotating_light: {CITY_NAME} 긴급 날씨 알림", "emoji": True},
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
            {"type": "mrkdwn", "text": f"v{__version__} · 자동 모니터링 알림 | <https://github.com/concrete-sangminlee/weather-slack-bot|GitHub>"},
        ],
    })

    client = WebClient(token=SLACK_BOT_TOKEN)
    client.chat_postMessage(
        channel=SLACK_CHANNEL,
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
            print("긴급 상황 없음. 알림 전송 안 함.")
    except Exception as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
