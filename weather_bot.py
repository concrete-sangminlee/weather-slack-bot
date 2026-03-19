import os
import sys
from datetime import datetime

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

WIND_DIRECTIONS = [
    "북", "북북동", "북동", "동북동",
    "동", "동남동", "남동", "남남동",
    "남", "남남서", "남서", "서남서",
    "서", "서북서", "북서", "북북서",
]


def wind_direction_to_text(degrees):
    idx = round(degrees / 22.5) % 16
    return WIND_DIRECTIONS[idx]


def uv_index_level(uv):
    if uv <= 2:
        return "낮음 😊"
    if uv <= 5:
        return "보통 🙂"
    if uv <= 7:
        return "높음 😎"
    if uv <= 10:
        return "매우 높음 🥵"
    return "위험 ☠️"


def fetch_weather():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": SEOUL_LAT,
        "longitude": SEOUL_LON,
        "current": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "is_day",
            "precipitation",
            "rain",
            "snowfall",
            "weather_code",
            "cloud_cover",
            "pressure_msl",
            "surface_pressure",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
        ]),
        "daily": ",".join([
            "temperature_2m_max",
            "temperature_2m_min",
            "apparent_temperature_max",
            "apparent_temperature_min",
            "precipitation_sum",
            "precipitation_hours",
            "precipitation_probability_max",
            "rain_sum",
            "snowfall_sum",
            "weather_code",
            "sunrise",
            "sunset",
            "sunshine_duration",
            "daylight_duration",
            "wind_speed_10m_max",
            "wind_gusts_10m_max",
            "wind_direction_10m_dominant",
            "uv_index_max",
            "shortwave_radiation_sum",
        ]),
        "timezone": "Asia/Seoul",
        "forecast_days": 1,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def generate_tips(main_weather, temp, humidity, uv, wind_speed, precip_prob):
    tips = []
    if main_weather in ("Rain", "Drizzle", "Thunderstorm"):
        tips.append("☂️ 우산 꼭 챙기세요!")
    elif precip_prob and precip_prob >= 50:
        tips.append(f"🌂 비 올 확률 {precip_prob}%! 우산 챙기세요.")
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
        tips.append("💧 습도가 높아요. 불쾌지수 높을 수 있습니다.")
    if uv and uv >= 8:
        tips.append("🧴 자외선이 매우 강합니다! 선크림 필수!")
    elif uv and uv >= 6:
        tips.append("🧴 자외선 지수가 높아요. 선크림을 바르세요.")
    if wind_speed >= 40:
        tips.append("🌪️ 강풍 주의! 외출 시 조심하세요.")
    elif wind_speed >= 25:
        tips.append("💨 바람이 강합니다. 체감 온도가 낮을 수 있어요.")
    if not tips:
        tips.append("🍃 좋은 하루 보내세요!")
    return "\n".join(f"  • {t}" for t in tips)


def format_time(iso_str):
    dt = datetime.fromisoformat(iso_str)
    return dt.strftime("%H:%M")


def format_duration(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}시간 {minutes}분"


def format_message(data):
    cur = data["current"]
    daily = data["daily"]

    weather_code = cur["weather_code"]
    description, main_weather = WMO_DESCRIPTIONS.get(weather_code, ("알 수 없음", "Clear"))
    emoji = WEATHER_EMOJIS.get(main_weather, "🌡️")

    temp = cur["temperature_2m"]
    feels_like = cur["apparent_temperature"]
    humidity = cur["relative_humidity_2m"]
    cloud_cover = cur["cloud_cover"]
    pressure = cur["pressure_msl"]
    wind_speed = cur["wind_speed_10m"]
    wind_gust = cur["wind_gusts_10m"]
    wind_dir = wind_direction_to_text(cur["wind_direction_10m"])
    precip = cur["precipitation"]
    rain = cur["rain"]
    snow = cur["snowfall"]

    temp_max = daily["temperature_2m_max"][0]
    temp_min = daily["temperature_2m_min"][0]
    feels_max = daily["apparent_temperature_max"][0]
    feels_min = daily["apparent_temperature_min"][0]
    precip_sum = daily["precipitation_sum"][0]
    precip_hours = daily["precipitation_hours"][0]
    precip_prob = daily["precipitation_probability_max"][0]
    rain_sum = daily["rain_sum"][0]
    snow_sum = daily["snowfall_sum"][0]
    sunrise = format_time(daily["sunrise"][0])
    sunset = format_time(daily["sunset"][0])
    sunshine = format_duration(daily["sunshine_duration"][0])
    daylight = format_duration(daily["daylight_duration"][0])
    wind_max = daily["wind_speed_10m_max"][0]
    gust_max = daily["wind_gusts_10m_max"][0]
    wind_dir_dominant = wind_direction_to_text(daily["wind_direction_10m_dominant"][0])
    uv_max = daily["uv_index_max"][0]
    radiation = daily["shortwave_radiation_sum"][0]

    tips = generate_tips(main_weather, temp, humidity, uv_max, wind_speed, precip_prob)

    message = (
        f"{emoji} *서울 오늘의 날씨*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"*🌡️ 기온*\n"
        f"  현재: *{temp}°C* (체감 {feels_like}°C)\n"
        f"  최고: {temp_max}°C (체감 {feels_max}°C)\n"
        f"  최저: {temp_min}°C (체감 {feels_min}°C)\n"
        f"\n"
        f"*🌤️ 날씨*\n"
        f"  상태: {description}\n"
        f"  구름량: {cloud_cover}%\n"
        f"  기압: {pressure} hPa\n"
        f"\n"
        f"*💧 습도 & 강수*\n"
        f"  습도: {humidity}%\n"
        f"  현재 강수량: {precip} mm\n"
        f"  오늘 예상 강수량: {precip_sum} mm (비 {rain_sum} mm / 눈 {snow_sum} cm)\n"
        f"  강수 확률: {precip_prob}%\n"
        f"  강수 예상 시간: {precip_hours}시간\n"
        f"\n"
        f"*💨 바람*\n"
        f"  풍속: {wind_speed} km/h (돌풍 {wind_gust} km/h)\n"
        f"  풍향: {wind_dir}\n"
        f"  오늘 최대 풍속: {wind_max} km/h (돌풍 {gust_max} km/h, {wind_dir_dominant}풍)\n"
        f"\n"
        f"*☀️ 일조 & 자외선*\n"
        f"  일출: {sunrise} / 일몰: {sunset}\n"
        f"  낮 길이: {daylight}\n"
        f"  일조 시간: {sunshine}\n"
        f"  자외선 지수: {uv_max} ({uv_index_level(uv_max)})\n"
        f"  일사량: {radiation} MJ/m²\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*💡 오늘의 팁*\n"
        f"{tips}"
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
