import os
import sys

import requests
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "#weather")

SEOUL_LAT = 37.5665
SEOUL_LON = 126.9780

# Open-Meteo WMO Weather Code 매핑
WMO_DESCRIPTIONS = {
    0: ("맑음", "Clear"),
    1: ("대체로 맑음", "Clear"),
    2: ("구름 조금", "Clouds"),
    3: ("흐림", "Clouds"),
    45: ("안개", "Fog"),
    48: ("안개", "Fog"),
    51: ("이슬비 (약)", "Drizzle"),
    53: ("이슬비 (보통)", "Drizzle"),
    55: ("이슬비 (강)", "Drizzle"),
    61: ("비 (약)", "Rain"),
    63: ("비 (보통)", "Rain"),
    65: ("비 (강)", "Rain"),
    66: ("진눈깨비 (약)", "Rain"),
    67: ("진눈깨비 (강)", "Rain"),
    71: ("눈 (약)", "Snow"),
    73: ("눈 (보통)", "Snow"),
    75: ("눈 (강)", "Snow"),
    77: ("싸락눈", "Snow"),
    80: ("소나기 (약)", "Rain"),
    81: ("소나기 (보통)", "Rain"),
    82: ("소나기 (강)", "Rain"),
    85: ("눈소나기 (약)", "Snow"),
    86: ("눈소나기 (강)", "Snow"),
    95: ("뇌우", "Thunderstorm"),
    96: ("뇌우 (우박)", "Thunderstorm"),
    99: ("뇌우 (강한 우박)", "Thunderstorm"),
}

WEATHER_EMOJIS = {
    "Clear": "☀️",
    "Clouds": "☁️",
    "Rain": "🌧️",
    "Drizzle": "🌦️",
    "Thunderstorm": "⛈️",
    "Snow": "❄️",
    "Fog": "🌫️",
}


def fetch_weather():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": SEOUL_LAT,
        "longitude": SEOUL_LON,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code",
        "timezone": "Asia/Seoul",
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def generate_tip(main_weather, temp, humidity):
    tips = []
    if main_weather in ("Rain", "Drizzle", "Thunderstorm"):
        tips.append("☂️ 우산 꼭 챙기세요!")
    if main_weather == "Snow":
        tips.append("🧤 빙판길 조심하세요!")
    if temp <= 0:
        tips.append("🥶 영하입니다! 따뜻하게 입으세요.")
    elif temp <= 5:
        tips.append("🧥 많이 춥습니다. 외투 필수!")
    elif temp >= 33:
        tips.append("🥵 폭염 주의! 수분 섭취 잊지 마세요.")
    elif temp >= 28:
        tips.append("😎 더운 날씨입니다. 시원하게 입으세요.")
    if humidity >= 80 and main_weather not in ("Rain", "Drizzle", "Thunderstorm"):
        tips.append("💧 습도가 높아요. 비가 올 수 있으니 우산을 챙겨보세요.")
    if not tips:
        tips.append("🍃 좋은 하루 보내세요!")
    return " ".join(tips)


def format_message(data):
    current = data["current"]
    weather_code = current["weather_code"]
    temp = current["temperature_2m"]
    feels_like = current["apparent_temperature"]
    humidity = current["relative_humidity_2m"]

    description, main_weather = WMO_DESCRIPTIONS.get(weather_code, ("알 수 없음", "Clear"))
    emoji = WEATHER_EMOJIS.get(main_weather, "🌡️")
    tip = generate_tip(main_weather, temp, humidity)

    message = (
        f"{emoji} *서울 오늘의 날씨*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🌡️ 기온: *{temp}°C* (체감 {feels_like}°C)\n"
        f"🌤️ 날씨: {description}\n"
        f"💧 습도: {humidity}%\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💡 *오늘의 팁:* {tip}"
    )
    return message


def send_to_slack(message):
    client = WebClient(token=SLACK_BOT_TOKEN)
    client.chat_postMessage(channel=SLACK_CHANNEL, text=message)


def main():
    try:
        data = fetch_weather()
        message = format_message(data)
        send_to_slack(message)
        print("날씨 메시지 전송 완료!")
    except requests.RequestException as e:
        print(f"날씨 API 오류: {e}", file=sys.stderr)
        sys.exit(1)
    except SlackApiError as e:
        print(f"Slack 전송 오류: {e.response['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
