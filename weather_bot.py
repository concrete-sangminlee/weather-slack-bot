import os
import sys

import requests
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

OPENWEATHERMAP_API_KEY = os.environ["OPENWEATHERMAP_API_KEY"]
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "#weather")

SEOUL_LAT = 37.5665
SEOUL_LON = 126.9780

WEATHER_EMOJIS = {
    "Clear": "☀️",
    "Clouds": "☁️",
    "Rain": "🌧️",
    "Drizzle": "🌦️",
    "Thunderstorm": "⛈️",
    "Snow": "❄️",
    "Mist": "🌫️",
    "Fog": "🌫️",
    "Haze": "🌫️",
}


def fetch_weather():
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": SEOUL_LAT,
        "lon": SEOUL_LON,
        "appid": OPENWEATHERMAP_API_KEY,
        "units": "metric",
        "lang": "kr",
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
    main_weather = data["weather"][0]["main"]
    description = data["weather"][0]["description"]
    temp = data["main"]["temp"]
    feels_like = data["main"]["feels_like"]
    humidity = data["main"]["humidity"]
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
