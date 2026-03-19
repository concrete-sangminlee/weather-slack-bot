import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

MAX_RETRIES = 3
RETRY_DELAY = 5

load_dotenv()

# ── 설정 로드 ──
_CONFIG_PATH = Path(__file__).parent / "config.yml"
with open(_CONFIG_PATH, encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "#weather")

CITY_NAME = CONFIG["city"]["name"]
CITY_LAT = CONFIG["city"]["latitude"]
CITY_LON = CONFIG["city"]["longitude"]
TIMEZONE = CONFIG["timezone"]
HOURLY_HOURS = CONFIG["forecast"]["hourly_hours"]
DAILY_DAYS = CONFIG["forecast"]["daily_days"]
PAST_DAYS = CONFIG["forecast"]["past_days"]
DISPLAY = CONFIG["display"]

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
    "Clear": ":sunny:",
    "Clouds": ":cloud:",
    "Rain": ":rain_cloud:",
    "Drizzle": ":partly_sunny_rain:",
    "Thunderstorm": ":thunder_cloud_and_rain:",
    "Snow": ":snowflake:",
    "Fog": ":fog:",
}

WIND_DIRECTIONS = [
    "북", "북북동", "북동", "동북동",
    "동", "동남동", "남동", "남남동",
    "남", "남남서", "남서", "서남서",
    "서", "서북서", "북서", "북북서",
]


def kmh_to_ms(kmh):
    return round(kmh / 3.6, 1)


def wind_direction_to_text(degrees):
    idx = round(degrees / 22.5) % 16
    return WIND_DIRECTIONS[idx]


def uv_index_level(uv):
    if uv <= 2:
        return "낮음 :blush:"
    if uv <= 5:
        return "보통 :slightly_smiling_face:"
    if uv <= 7:
        return "높음 :sunglasses:"
    if uv <= 10:
        return "매우 높음 :hot_face:"
    return "위험 :skull:"


def _request_with_retry(url, params):
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(RETRY_DELAY * (attempt + 1))


def fetch_weather():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": CITY_LAT,
        "longitude": CITY_LON,
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
            "visibility",
            "dew_point_2m",
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
        "hourly": ",".join([
            "temperature_2m",
            "weather_code",
            "precipitation_probability",
            "wind_speed_10m",
        ]),
        "timezone": TIMEZONE,
        "past_days": PAST_DAYS,
        "forecast_days": DAILY_DAYS,
    }
    return _request_with_retry(url, params)


def fetch_air_quality():
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": CITY_LAT,
        "longitude": CITY_LON,
        "current": "pm10,pm2_5,us_aqi,carbon_monoxide,nitrogen_dioxide,ozone",
        "timezone": TIMEZONE,
    }
    return _request_with_retry(url, params)


def aqi_level(aqi):
    if aqi <= 50:
        return "좋음 :large_green_circle:"
    if aqi <= 100:
        return "보통 :large_yellow_circle:"
    if aqi <= 150:
        return "민감군 나쁨 :large_orange_circle:"
    if aqi <= 200:
        return "나쁨 :red_circle:"
    if aqi <= 300:
        return "매우 나쁨 :purple_circle:"
    return "위험 :skull:"


def pm_level(pm25):
    if pm25 <= 15:
        return "좋음"
    if pm25 <= 35:
        return "보통"
    if pm25 <= 75:
        return "나쁨"
    return "매우 나쁨"


def format_visibility(meters):
    if meters >= 10000:
        return f"{meters / 1000:.0f} km (매우 좋음)"
    if meters >= 5000:
        return f"{meters / 1000:.1f} km (좋음)"
    if meters >= 1000:
        return f"{meters / 1000:.1f} km (보통)"
    return f"{meters:.0f} m (나쁨)"


def calc_lifestyle_index(temp, humidity, wind_ms, uv, aqi, precip_prob):
    """종합 생활지수 (0~100, 높을수록 좋음)"""
    score = 100

    # 기온 쾌적도 (18~24가 최적)
    if 18 <= temp <= 24:
        pass
    elif 15 <= temp <= 27:
        score -= 5
    elif 10 <= temp <= 30:
        score -= 15
    elif 5 <= temp <= 33:
        score -= 25
    else:
        score -= 40

    # 습도 (40~60 최적)
    if 40 <= humidity <= 60:
        pass
    elif 30 <= humidity <= 70:
        score -= 5
    else:
        score -= 15

    # 바람
    if wind_ms >= 10:
        score -= 15
    elif wind_ms >= 5:
        score -= 5

    # 자외선
    if uv is not None:
        if uv >= 8:
            score -= 10
        elif uv >= 6:
            score -= 5

    # 대기질
    if aqi is not None:
        if aqi > 150:
            score -= 20
        elif aqi > 100:
            score -= 10
        elif aqi > 50:
            score -= 5

    # 강수 확률
    if precip_prob is not None:
        if precip_prob >= 70:
            score -= 15
        elif precip_prob >= 40:
            score -= 5

    return max(0, min(100, score))


def lifestyle_label(score):
    if score >= 90:
        return "최고 :star:"
    if score >= 75:
        return "좋음 :large_green_circle:"
    if score >= 60:
        return "보통 :large_yellow_circle:"
    if score >= 40:
        return "나쁨 :large_orange_circle:"
    return "매우 나쁨 :red_circle:"


def lifestyle_bar(score):
    filled = round(score / 10)
    return ":large_green_square:" * filled + ":white_large_square:" * (10 - filled)


def get_outfit_recommendation(temp, feels_like, main_weather, precip_prob):
    """체감 온도 기반 옷차림 추천"""
    t = feels_like

    if t <= -10:
        outfit = ":scarf: 패딩·롱패딩, 목도리, 장갑, 귀마개, 기모 안감"
    elif t <= -5:
        outfit = ":coat: 두꺼운 패딩, 목도리, 장갑, 기모 바지"
    elif t <= 0:
        outfit = ":coat: 패딩·두꺼운 코트, 니트, 기모 바지"
    elif t <= 5:
        outfit = ":coat: 코트·가죽자켓, 니트, 히트텍"
    elif t <= 10:
        outfit = ":necktie: 자켓·트렌치코트, 니트·맨투맨"
    elif t <= 15:
        outfit = ":shirt: 가디건·얇은 자켓, 맨투맨, 긴 바지"
    elif t <= 20:
        outfit = ":tshirt: 얇은 긴팔·셔츠, 면바지"
    elif t <= 25:
        outfit = ":tshirt: 반팔·얇은 셔츠, 면바지·린넨"
    elif t <= 30:
        outfit = ":shorts: 반팔·민소매, 반바지·린넨 바지"
    else:
        outfit = ":shorts: 민소매·나시, 반바지, 통풍 잘 되는 옷"

    extras = []
    if main_weather in ("Rain", "Drizzle", "Thunderstorm") or (precip_prob and precip_prob >= 50):
        extras.append(":umbrella: 우산")
    if main_weather == "Snow":
        extras.append(":boot: 방수 신발")

    if extras:
        outfit += " + " + " ".join(extras)

    return outfit


def generate_tips(main_weather, temp, feels_like, temp_max, temp_min,
                  humidity, uv, wind_ms, gust_ms, precip_prob,
                  precip_sum, cloud_cover, snow_sum, aqi=None, pm25=None):
    tips = []

    # ── 강수 관련 ──
    if main_weather == "Thunderstorm":
        tips.append(":thunder_cloud_and_rain: 뇌우가 치고 있어요! 가급적 실내에 머무르세요.")
    elif main_weather in ("Rain", "Drizzle"):
        if precip_sum >= 30:
            tips.append(":ocean: 폭우 예상! 저지대 침수에 주의하고, 외출을 자제하세요.")
        elif precip_sum >= 10:
            tips.append(":umbrella_with_rain_drops: 비가 많이 옵니다. 우산과 방수 신발을 챙기세요.")
        else:
            tips.append(":umbrella: 우산 꼭 챙기세요!")
    elif precip_prob is not None and precip_prob >= 70:
        tips.append(f":closed_umbrella: 비 올 확률 {precip_prob}%! 우산 꼭 챙기세요.")
    elif precip_prob is not None and precip_prob >= 40:
        tips.append(f":closed_umbrella: 비 올 확률 {precip_prob}%. 접이식 우산 하나 챙기면 좋겠어요.")

    # ── 눈 관련 ──
    if main_weather == "Snow":
        if snow_sum >= 5:
            tips.append(":snowman: 폭설 주의! 대중교통 이용을 권장합니다.")
        else:
            tips.append(":snowflake: 눈이 내려요! 빙판길 조심하세요.")
    elif temp <= 0 and precip_prob is not None and precip_prob >= 30:
        tips.append(":ice_cube: 영하에 강수 확률이 있어요. 도로 결빙에 주의하세요.")

    # ── 기온 관련 ──
    if temp <= -10:
        tips.append(":cold_face: 강추위! 동파 주의, 노출 피부를 최소화하세요.")
    elif temp <= -5:
        tips.append(":cold_face: 매서운 추위입니다. 내복과 두꺼운 외투 필수!")
    elif temp <= 0:
        tips.append(":ice_cube: 영하입니다. 목도리, 장갑 챙기세요.")
    elif temp <= 5:
        tips.append(":coat: 쌀쌀합니다. 따뜻한 외투를 입으세요.")
    elif temp <= 10:
        tips.append(":gloves: 약간 쌀쌀해요. 겉옷 하나 걸치세요.")

    if temp >= 35:
        tips.append(":fire: 극심한 폭염! 야외 활동을 피하고 수분을 충분히 섭취하세요.")
    elif temp >= 33:
        tips.append(":hot_face: 폭염 주의! 시원한 물 자주 마시고 그늘에서 쉬세요.")
    elif temp >= 30:
        tips.append(":sunny: 무더운 날씨입니다. 통풍 잘 되는 옷을 입으세요.")
    elif temp >= 28:
        tips.append(":sunglasses: 더운 날이에요. 시원하게 입으세요.")

    # ── 일교차 ──
    diff = temp_max - temp_min
    if diff >= 15:
        tips.append(f":thermometer: 일교차 {diff:.0f}°C! 겹쳐 입기 필수. 감기 조심하세요.")
    elif diff >= 10:
        tips.append(f":thermometer: 일교차가 {diff:.0f}°C로 큽니다. 얇은 겉옷을 챙기세요.")

    # ── 습도 관련 ──
    if humidity >= 90 and main_weather not in ("Rain", "Drizzle", "Thunderstorm", "Snow"):
        tips.append(":sweat_drops: 습도 매우 높음! 빨래는 실내 건조하세요.")
    elif humidity >= 80 and main_weather not in ("Rain", "Drizzle", "Thunderstorm", "Snow"):
        tips.append(":droplet: 습도가 높아요. 불쾌지수가 높을 수 있습니다.")
    elif humidity <= 20:
        tips.append(":desert: 공기가 매우 건조합니다. 보습제를 바르고 물을 자주 마시세요.")
    elif humidity <= 30:
        tips.append(":dash: 건조한 날씨예요. 수분 섭취와 피부 보습에 신경 쓰세요.")

    # ── 자외선 관련 ──
    if uv is not None:
        if uv >= 11:
            tips.append(":skull: 자외선 극도로 위험! 한낮 외출 자제, 선크림 SPF50+ 필수.")
        elif uv >= 8:
            tips.append(":lotion_bottle: 자외선 매우 강함! 선크림·선글라스·모자 3종 세트 챙기세요.")
        elif uv >= 6:
            tips.append(":lotion_bottle: 자외선 지수가 높아요. 선크림을 바르세요.")
        elif uv >= 3:
            tips.append(":sunglasses: 자외선 보통. 장시간 야외 활동 시 선크림 추천.")

    # ── 바람 관련 ──
    if wind_ms >= 14:
        tips.append(":tornado: 강풍 경보급! 외출 자제, 간판·구조물 낙하 주의.")
    elif wind_ms >= 11:
        tips.append(":wind_blowing_face: 강풍 주의! 우산이 뒤집힐 수 있어요. 외출 시 조심하세요.")
    elif wind_ms >= 8:
        tips.append(":dash: 바람이 꽤 셉니다. 체감 온도가 낮을 수 있어요.")
    elif wind_ms >= 5:
        tips.append(":leaves: 바람이 좀 불어요. 머리카락 날림 주의!")

    if gust_ms >= 20:
        tips.append(f":warning: 돌풍 {gust_ms} m/s 예상! 가벼운 물건이 날아갈 수 있어요.")

    # ── 안개 ──
    if main_weather == "Fog":
        tips.append(":fog: 안개가 짙습니다. 운전 시 전조등 켜고 서행하세요.")

    # ── 대기질 관련 ──
    if pm25 is not None:
        if pm25 > 75:
            tips.append(":no_entry_sign: 초미세먼지 매우 나쁨! 외출 자제, KF94 마스크 필수.")
        elif pm25 > 35:
            tips.append(":mask: 초미세먼지 나쁨. 마스크를 착용하세요.")
    if aqi is not None and aqi > 150 and (pm25 is None or pm25 <= 35):
        tips.append(":mask: 대기질이 나쁩니다. 민감군은 외출을 줄이세요.")

    # ── 흐림/구름 ──
    if cloud_cover >= 90 and main_weather not in ("Rain", "Drizzle", "Thunderstorm", "Snow", "Fog"):
        tips.append(":cloud: 하늘이 잔뜩 흐려요. 기분 전환에 따뜻한 음료 한 잔 어때요?")

    # ── 쾌적한 날씨 ──
    if not tips:
        if 18 <= temp <= 25 and 40 <= humidity <= 60 and wind_ms < 5:
            tips.append(":rainbow: 완벽한 날씨! 산책하기 딱 좋은 날이에요.")
        elif 15 <= temp <= 27 and humidity < 70:
            tips.append(":leaves: 쾌적한 날씨입니다. 좋은 하루 보내세요!")
        elif 10 <= temp <= 15:
            tips.append(":cherry_blossom: 봄바람이 느껴지는 날이에요. 가벼운 산책 어떠세요?")
        else:
            tips.append(":leaves: 좋은 하루 보내세요!")

    return tips


def format_time(iso_str):
    dt = datetime.fromisoformat(iso_str)
    return dt.strftime("%H:%M")


def format_duration(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}시간 {minutes}분"


def build_blocks(data, air_data=None):
    cur = data["current"]
    daily = data["daily"]

    weather_code = cur["weather_code"]
    description, main_weather = WMO_DESCRIPTIONS.get(weather_code, ("알 수 없음", "Clear"))
    emoji = WEATHER_EMOJIS.get(main_weather, ":thermometer:")

    temp = cur["temperature_2m"]
    feels_like = cur["apparent_temperature"]
    humidity = cur["relative_humidity_2m"]
    cloud_cover = cur["cloud_cover"]
    pressure = cur["pressure_msl"]
    wind_speed = kmh_to_ms(cur["wind_speed_10m"])
    wind_gust = kmh_to_ms(cur["wind_gusts_10m"])
    wind_dir = wind_direction_to_text(cur["wind_direction_10m"])
    precip = cur["precipitation"]
    visibility = cur.get("visibility", 0)
    dew_point = cur.get("dew_point_2m")

    # past_days=1이면 index 0=어제, 1=오늘; past_days=0이면 0=오늘
    today_idx = PAST_DAYS
    temp_max = daily["temperature_2m_max"][today_idx]
    temp_min = daily["temperature_2m_min"][today_idx]
    feels_max = daily["apparent_temperature_max"][today_idx]
    feels_min = daily["apparent_temperature_min"][today_idx]
    precip_sum = daily["precipitation_sum"][today_idx]
    precip_hours = daily["precipitation_hours"][today_idx]
    precip_prob = daily["precipitation_probability_max"][today_idx]
    rain_sum = daily["rain_sum"][today_idx]
    snow_sum = daily["snowfall_sum"][today_idx]
    sunrise = format_time(daily["sunrise"][today_idx])
    sunset = format_time(daily["sunset"][today_idx])
    sunshine = format_duration(daily["sunshine_duration"][today_idx])
    daylight = format_duration(daily["daylight_duration"][today_idx])
    wind_max = kmh_to_ms(daily["wind_speed_10m_max"][today_idx])
    gust_max = kmh_to_ms(daily["wind_gusts_10m_max"][today_idx])
    wind_dir_dominant = wind_direction_to_text(daily["wind_direction_10m_dominant"][today_idx])
    uv_max = daily["uv_index_max"][today_idx]
    radiation = daily["shortwave_radiation_sum"][today_idx]

    # 어제 대비 비교
    yesterday_cmp = ""
    if DISPLAY["show_yesterday_comparison"] and PAST_DAYS >= 1:
        y_max = daily["temperature_2m_max"][0]
        y_min = daily["temperature_2m_min"][0]
        diff_max = temp_max - y_max
        diff_min = temp_min - y_min
        sign_max = "+" if diff_max > 0 else ""
        sign_min = "+" if diff_min > 0 else ""
        yesterday_cmp = f"어제 대비 최고 {sign_max}{diff_max:.1f}°C / 최저 {sign_min}{diff_min:.1f}°C"

    # 대기질 데이터 추출
    aqi = pm25 = pm10 = co = no2 = o3 = None
    if air_data and "current" in air_data:
        aq = air_data["current"]
        aqi = aq.get("us_aqi")
        pm25 = aq.get("pm2_5")
        pm10 = aq.get("pm10")
        co = aq.get("carbon_monoxide")
        no2 = aq.get("nitrogen_dioxide")
        o3 = aq.get("ozone")

    tips = generate_tips(
        main_weather, temp, feels_like, temp_max, temp_min,
        humidity, uv_max, wind_speed, gust_max, precip_prob,
        precip_sum, cloud_cover, snow_sum, aqi, pm25,
    )

    outfit = get_outfit_recommendation(temp, feels_like, main_weather, precip_prob)
    life_score = calc_lifestyle_index(temp, humidity, wind_speed, uv_max, aqi, precip_prob)

    WEEKDAYS_KR = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    now = datetime.now()
    today = now.strftime("%Y년 %m월 %d일") + " " + WEEKDAYS_KR[now.weekday()]

    blocks = [
        # ── 헤더 ──
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{description} | {CITY_NAME} 오늘의 날씨", "emoji": True},
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f":calendar: {today}"},
            ],
        },
        {"type": "divider"},

        # ── 기온 ──
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} *현재 {temp}°C* (체감 {feels_like}°C)",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f":arrow_up: *최고* {temp_max}°C\n체감 {feels_max}°C"},
                {"type": "mrkdwn", "text": f":arrow_down: *최저* {temp_min}°C\n체감 {feels_min}°C"},
            ],
        },
        *(
            [{
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f":chart_with_upwards_trend: {yesterday_cmp}"}],
            }] if yesterday_cmp else []
        ),
        {"type": "divider"},

        # ── 날씨 상태 ──
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f":partly_sunny: *날씨*\n{description}"},
                {"type": "mrkdwn", "text": f":cloud: *구름량*\n{cloud_cover}%"},
                {"type": "mrkdwn", "text": f":compression: *기압*\n{pressure} hPa"},
                {"type": "mrkdwn", "text": f":droplet: *습도*\n{humidity}%"},
            ],
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f":eye: 가시거리 {format_visibility(visibility)} · :sweat_drops: 이슬점 {dew_point}°C"},
            ],
        },
        {"type": "divider"},

        # ── 강수 ──
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f":umbrella_with_rain_drops: *강수 확률*\n{precip_prob}%"},
                {"type": "mrkdwn", "text": f":rain_cloud: *현재 강수량*\n{precip} mm"},
                {"type": "mrkdwn", "text": f":sweat_drops: *예상 강수량*\n{precip_sum} mm"},
                {"type": "mrkdwn", "text": f":clock3: *강수 시간*\n{precip_hours}시간"},
            ],
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"비 {rain_sum} mm / 눈 {snow_sum} cm"},
            ],
        },
        {"type": "divider"},

        # ── 바람 ──
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f":wind_blowing_face: *풍속*\n{wind_speed} m/s"},
                {"type": "mrkdwn", "text": f":tornado: *돌풍*\n{wind_gust} m/s"},
                {"type": "mrkdwn", "text": f":compass: *풍향*\n{wind_dir}"},
                {"type": "mrkdwn", "text": f":chart_with_upwards_trend: *최대 풍속*\n{wind_max} m/s ({wind_dir_dominant}풍)"},
            ],
        },
        {"type": "divider"},

        # ── 일조 & 자외선 ──
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f":sunrise: *일출*\n{sunrise}"},
                {"type": "mrkdwn", "text": f":city_sunset: *일몰*\n{sunset}"},
                {"type": "mrkdwn", "text": f":sun_with_face: *낮 길이*\n{daylight}"},
                {"type": "mrkdwn", "text": f":sunny: *일조 시간*\n{sunshine}"},
            ],
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f":beach_with_umbrella: *자외선 지수*\n{uv_max} ({uv_index_level(uv_max)})"},
                {"type": "mrkdwn", "text": f":high_brightness: *일사량*\n{radiation} MJ/m²"},
            ],
        },
        {"type": "divider"},

        # ── 대기질 ──
        *(
            _build_air_quality_blocks(aqi, pm25, pm10, co, no2, o3)
            if DISPLAY["show_air_quality"] else []
        ),

        # ── 시간별 예보 ──
        *(
            [
                {"type": "divider"},
                {"type": "section", "text": {"type": "mrkdwn", "text": "*:clock1: 시간별 예보*"}},
                *_build_hourly_blocks(data),
            ] if DISPLAY["show_hourly"] else []
        ),

        # ── 3일 예보 ──
        *(
            [
                {"type": "divider"},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*:calendar: {DAILY_DAYS}일 예보*"}},
                *_build_daily_forecast_blocks(data),
            ] if DISPLAY["show_daily_forecast"] else []
        ),

        {"type": "divider"},

        # ── 생활지수 ──
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*:bar_chart: 오늘의 생활지수*\n{lifestyle_bar(life_score)} *{life_score}점* ({lifestyle_label(life_score)})",
            },
        },

        # ── 옷차림 추천 ──
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*:womans_clothes: 오늘의 옷차림*\n{outfit}",
            },
        },

        # ── 오늘의 팁 ──
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*:bulb: 오늘의 팁*\n" + "\n".join(f"• {t}" for t in tips),
            },
        },

        # ── 푸터 ──
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "Powered by Open-Meteo API | <https://github.com/concrete-sangminlee/weather-slack-bot|GitHub>"},
            ],
        },
    ]

    return blocks


def _build_air_quality_blocks(aqi, pm25, pm10, co, no2, o3):
    if aqi is None:
        return []

    return [
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f":dash: *대기질 (AQI)*\n{aqi} ({aqi_level(aqi)})"},
                {"type": "mrkdwn", "text": f":small_blue_diamond: *초미세먼지 PM2.5*\n{pm25} µg/m³ ({pm_level(pm25)})"},
                {"type": "mrkdwn", "text": f":small_orange_diamond: *미세먼지 PM10*\n{pm10} µg/m³"},
                {"type": "mrkdwn", "text": f":test_tube: *오존*\n{o3} µg/m³"},
            ],
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"CO {co} µg/m³ · NO₂ {no2} µg/m³ · O₃ {o3} µg/m³"},
            ],
        },
        {"type": "divider"},
    ]


def _build_hourly_blocks(data):
    hourly = data["hourly"]
    now = datetime.now()
    current_hour = now.hour

    lines = []
    count = 0
    for i, time_str in enumerate(hourly["time"]):
        dt = datetime.fromisoformat(time_str)
        if dt.date() == now.date() and dt.hour > current_hour and count < 6:
            code = hourly["weather_code"][i]
            desc, cat = WMO_DESCRIPTIONS.get(code, ("알 수 없음", "Clear"))
            emoji = WEATHER_EMOJIS.get(cat, ":thermometer:")
            t = hourly["temperature_2m"][i]
            prob = hourly["precipitation_probability"][i]
            wind = kmh_to_ms(hourly["wind_speed_10m"][i])
            lines.append(f"`{dt.hour:02d}시` {emoji} *{t}°C*  :droplet:{prob}%  :dash:{wind}m/s")
            count += 1

    # 오늘 남은 시간이 부족하면 내일 아침부터 채우기
    if count < 6:
        for i, time_str in enumerate(hourly["time"]):
            dt = datetime.fromisoformat(time_str)
            if dt.date() > now.date() and count < 6:
                code = hourly["weather_code"][i]
                desc, cat = WMO_DESCRIPTIONS.get(code, ("알 수 없음", "Clear"))
                emoji = WEATHER_EMOJIS.get(cat, ":thermometer:")
                t = hourly["temperature_2m"][i]
                prob = hourly["precipitation_probability"][i]
                wind = kmh_to_ms(hourly["wind_speed_10m"][i])
                day_label = "내일" if (dt.date() - now.date()).days == 1 else "모레"
                lines.append(f"`{day_label} {dt.hour:02d}시` {emoji} *{t}°C*  :droplet:{prob}%  :dash:{wind}m/s")
                count += 1

    if not lines:
        lines.append("시간별 데이터 없음")

    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(lines)},
        },
    ]


def _build_daily_forecast_blocks(data):
    daily = data["daily"]
    WEEKDAYS_KR = ["월", "화", "수", "목", "금", "토", "일"]

    lines = []
    start = PAST_DAYS  # 어제 데이터 건너뛰기
    for i in range(start, min(start + DAILY_DAYS, len(daily["time"]))):
        dt = datetime.fromisoformat(daily["time"][i])
        day_name = WEEKDAYS_KR[dt.weekday()]
        code = daily["weather_code"][i]
        desc, cat = WMO_DESCRIPTIONS.get(code, ("알 수 없음", "Clear"))
        emoji = WEATHER_EMOJIS.get(cat, ":thermometer:")
        t_max = daily["temperature_2m_max"][i]
        t_min = daily["temperature_2m_min"][i]
        prob = daily["precipitation_probability_max"][i]

        date_str = f"{dt.month}/{dt.day}({day_name})"
        lines.append(f"`{date_str}` {emoji} {desc}  :arrow_down:*{t_min}°C* :arrow_up:*{t_max}°C*  :droplet:{prob}%")

    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(lines)},
        },
    ]


def build_fallback_text(data):
    cur = data["current"]
    weather_code = cur["weather_code"]
    description, _ = WMO_DESCRIPTIONS.get(weather_code, ("알 수 없음", "Clear"))
    temp = cur["temperature_2m"]
    return f"{CITY_NAME} 오늘의 날씨: {description}, {temp}°C"


def send_to_slack(blocks, fallback_text):
    client = WebClient(token=SLACK_BOT_TOKEN)
    client.chat_postMessage(
        channel=SLACK_CHANNEL,
        text=fallback_text,
        blocks=blocks,
    )


def send_error_to_slack(error_msg):
    """실패 시 에러 메시지를 Slack으로 전송"""
    try:
        client = WebClient(token=SLACK_BOT_TOKEN)
        client.chat_postMessage(
            channel=SLACK_CHANNEL,
            text=f":warning: 날씨 봇 오류: {error_msg}",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":rotating_light: *{CITY_NAME} 날씨 봇 오류*\n```{error_msg}```",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f":clock1: {datetime.now().strftime('%Y-%m-%d %H:%M')} | <https://github.com/concrete-sangminlee/weather-slack-bot/actions|GitHub Actions 확인>"},
                    ],
                },
            ],
        )
    except Exception:
        pass  # 에러 알림 자체가 실패하면 무시


def main():
    try:
        data = fetch_weather()
        try:
            air_data = fetch_air_quality()
        except requests.RequestException:
            air_data = None
        blocks = build_blocks(data, air_data)
        fallback_text = build_fallback_text(data)
        send_to_slack(blocks, fallback_text)
        print("날씨 메시지 전송 완료!")
    except requests.RequestException as e:
        error_msg = f"날씨 API 오류: {e}"
        print(error_msg, file=sys.stderr)
        send_error_to_slack(error_msg)
        sys.exit(1)
    except SlackApiError as e:
        error_msg = f"Slack 전송 오류: {e.response['error']}"
        print(error_msg, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        error_msg = f"예기치 않은 오류: {e}"
        print(error_msg, file=sys.stderr)
        send_error_to_slack(error_msg)
        sys.exit(1)


if __name__ == "__main__":
    main()
