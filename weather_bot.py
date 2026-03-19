import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

__version__ = "2.1.0"

MAX_RETRIES = 3
RETRY_DELAY = 5

load_dotenv()

# ── 설정 로드 ──
_CONFIG_PATH = Path(__file__).parent / "config.yml"
with open(_CONFIG_PATH, encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

# ── 다국어 로드 ──
_LOCALE = CONFIG.get("locale", "ko")
_LOCALE_PATH = Path(__file__).parent / "locales" / f"{_LOCALE}.yml"
with open(_LOCALE_PATH, encoding="utf-8") as f:
    L = yaml.safe_load(f)

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "#weather")

CITY_NAME = CONFIG["city"]["name"]
CITY_LAT = CONFIG["city"]["latitude"]
CITY_LON = CONFIG["city"]["longitude"]
TIMEZONE = CONFIG["timezone"]
HOURLY_HOURS = CONFIG["forecast"]["hourly_hours"]
DAILY_DAYS = CONFIG["forecast"]["daily_days"]
PAST_DAYS = CONFIG["forecast"]["past_days"]
TREND_DAYS = CONFIG["forecast"].get("trend_days", 7)
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
            "relative_humidity_2m",
            "uv_index",
            "apparent_temperature",
        ]),
        "timezone": TIMEZONE,
        "past_days": PAST_DAYS,
        "forecast_days": max(DAILY_DAYS, TREND_DAYS),
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


def find_best_outdoor_time(data):
    """오늘 시간별 데이터에서 가장 외출하기 좋은 시간대 찾기"""
    hourly = data["hourly"]
    now = datetime.now()
    best_hour = None
    best_score = -1

    for i, time_str in enumerate(hourly["time"]):
        dt = datetime.fromisoformat(time_str)
        if dt.date() != now.date() or dt.hour <= now.hour or dt.hour < 7 or dt.hour > 20:
            continue

        t = hourly["temperature_2m"][i]
        code = hourly["weather_code"][i]
        prob = hourly["precipitation_probability"][i] or 0
        wind = kmh_to_ms(hourly["wind_speed_10m"][i])
        hum = hourly["relative_humidity_2m"][i]
        uv = hourly["uv_index"][i] or 0
        _, cat = WMO_DESCRIPTIONS.get(code, ("", "Clear"))

        # 비/눈/뇌우면 스킵
        if cat in ("Rain", "Drizzle", "Thunderstorm", "Snow"):
            continue
        if prob >= 60:
            continue

        score = 100

        # 기온 쾌적도
        if 18 <= t <= 24:
            pass
        elif 15 <= t <= 27:
            score -= 10
        elif 10 <= t <= 30:
            score -= 25
        else:
            score -= 40

        # 습도
        if 40 <= hum <= 60:
            pass
        elif 30 <= hum <= 70:
            score -= 5
        else:
            score -= 15

        # 바람
        score -= min(wind * 2, 20)

        # 자외선 (너무 높으면 감점)
        if uv >= 8:
            score -= 15
        elif uv >= 6:
            score -= 5

        # 강수 확률
        score -= prob * 0.3

        if score > best_score:
            best_score = score
            best_hour = dt.hour

    if best_hour is None:
        return None

    feels = None
    for i, time_str in enumerate(hourly["time"]):
        dt = datetime.fromisoformat(time_str)
        if dt.date() == now.date() and dt.hour == best_hour:
            feels = hourly["apparent_temperature"][i]
            break

    return {"hour": best_hour, "score": round(best_score), "feels": feels}


def build_weekly_trend(data):
    """7일 기온 트렌드 미니 차트"""
    daily = data["daily"]
    WEEKDAYS_KR = ["월", "화", "수", "목", "금", "토", "일"]

    start = PAST_DAYS
    entries = []
    for i in range(start, min(start + TREND_DAYS, len(daily["time"]))):
        dt = datetime.fromisoformat(daily["time"][i])
        t_max = daily["temperature_2m_max"][i]
        t_min = daily["temperature_2m_min"][i]
        entries.append((WEEKDAYS_KR[dt.weekday()], t_min, t_max))

    if not entries:
        return ""

    # 전체 범위 계산
    all_temps = [t for _, lo, hi in entries for t in (lo, hi)]
    t_floor = min(all_temps)
    t_ceil = max(all_temps)
    t_range = t_ceil - t_floor if t_ceil != t_floor else 1

    lines = []
    for day, lo, hi in entries:
        # 8칸 바로 표현
        bar_len = 8
        lo_pos = round((lo - t_floor) / t_range * bar_len)
        hi_pos = round((hi - t_floor) / t_range * bar_len)
        hi_pos = max(hi_pos, lo_pos + 1)  # 최소 1칸

        bar = ""
        for p in range(bar_len + 1):
            if lo_pos <= p <= hi_pos:
                bar += ":blue_square:" if p <= (lo_pos + hi_pos) // 2 else ":orange_square:"
            else:
                bar += "  "

        lines.append(f"`{day}` {lo:+.0f}° {bar} {hi:+.0f}°")

    return "\n".join(lines)


def calc_daylight_progress(sunrise_str, sunset_str):
    """현재 시각이 일출~일몰 중 어디인지 프로그레스 바로 표현"""
    now = datetime.now()
    sunrise = datetime.fromisoformat(sunrise_str)
    sunset = datetime.fromisoformat(sunset_str)

    if now < sunrise:
        return ":new_moon: 일출 전", 0
    if now > sunset:
        return ":new_moon: 일몰 후", 100

    total = (sunset - sunrise).total_seconds()
    elapsed = (now - sunrise).total_seconds()
    pct = int(elapsed / total * 100)

    bar_len = 10
    filled = round(pct / 100 * bar_len)
    bar = ":sunny:" + ":yellow_square:" * filled + ":black_large_square:" * (bar_len - filled) + ":crescent_moon:"

    remaining = sunset - now
    hours = int(remaining.total_seconds() // 3600)
    minutes = int((remaining.total_seconds() % 3600) // 60)

    return f"{bar} 일몰까지 {hours}시간 {minutes}분", pct


def get_moon_phase():
    """현재 달의 위상 계산 (Conway's method)"""
    now = datetime.now()
    year = now.year
    month = now.month
    day = now.day

    if month <= 2:
        year -= 1
        month += 12

    a = year // 100
    b = a // 4
    c = 2 - a + b
    e = int(365.25 * (year + 4716))
    f = int(30.6001 * (month + 1))
    jd = c + day + e + f - 1524.5

    days_since_new = (jd - 2451549.5) % 29.53058867
    phase_pct = days_since_new / 29.53058867

    if phase_pct < 0.0339:
        return ":new_moon: 삭(새달)"
    if phase_pct < 0.216:
        return ":waxing_crescent_moon: 초승달"
    if phase_pct < 0.283:
        return ":first_quarter_moon: 상현달"
    if phase_pct < 0.466:
        return ":waxing_gibbous_moon: 상현망간"
    if phase_pct < 0.534:
        return ":full_moon: 보름달"
    if phase_pct < 0.716:
        return ":waning_gibbous_moon: 하현망간"
    if phase_pct < 0.783:
        return ":last_quarter_moon: 하현달"
    if phase_pct < 0.966:
        return ":waning_crescent_moon: 그믐달"
    return ":new_moon: 삭(새달)"


def get_tomorrow_alert(data):
    """내일 날씨가 오늘과 크게 다를 때 알림 생성"""
    daily = data["daily"]
    today_idx = PAST_DAYS
    tmr_idx = today_idx + 1
    if tmr_idx >= len(daily["time"]):
        return None

    t_max = daily["temperature_2m_max"][today_idx]
    t_min = daily["temperature_2m_min"][today_idx]
    tmr_max = daily["temperature_2m_max"][tmr_idx]
    tmr_min = daily["temperature_2m_min"][tmr_idx]
    tmr_code = daily["weather_code"][tmr_idx]
    tmr_prob = daily["precipitation_probability_max"][tmr_idx]
    tmr_desc, tmr_cat = WMO_DESCRIPTIONS.get(tmr_code, ("알 수 없음", "Clear"))
    today_code = daily["weather_code"][today_idx]
    _, today_cat = WMO_DESCRIPTIONS.get(today_code, ("알 수 없음", "Clear"))

    alerts = []

    # 기온 급변
    max_diff = tmr_max - t_max
    min_diff = tmr_min - t_min
    if max_diff >= 8:
        alerts.append(f":chart_with_upwards_trend: 내일 최고기온 {tmr_max}°C로 *{max_diff:+.0f}°C* 급상승!")
    elif max_diff <= -8:
        alerts.append(f":chart_with_downwards_trend: 내일 최고기온 {tmr_max}°C로 *{max_diff:+.0f}°C* 급하락!")
    elif abs(max_diff) >= 5:
        sign = "상승" if max_diff > 0 else "하락"
        alerts.append(f":thermometer: 내일 최고기온 {tmr_max}°C ({max_diff:+.0f}°C {sign})")

    # 날씨 급변 (맑음 → 비/눈 또는 반대)
    rain_cats = ("Rain", "Drizzle", "Thunderstorm", "Snow")
    if today_cat not in rain_cats and tmr_cat in rain_cats:
        emoji = WEATHER_EMOJIS.get(tmr_cat, ":cloud:")
        alerts.append(f"{emoji} 내일 {tmr_desc} 예보! 우산 미리 챙기세요.")
    elif today_cat in rain_cats and tmr_cat not in rain_cats:
        alerts.append(f":sunny: 내일은 날이 개요! ({tmr_desc})")

    # 강수 확률 급등
    today_prob = daily["precipitation_probability_max"][today_idx]
    if tmr_prob >= 60 and today_prob < 30:
        alerts.append(f":umbrella: 내일 강수확률 {tmr_prob}%로 급등!")

    return alerts if alerts else None


def get_health_risks(temp, humidity, wind_ms, uv, pm25):
    """건강 위험 지수 생성"""
    risks = []

    # 감기/독감 위험 (저온 + 건조)
    if temp <= 5 and humidity <= 40:
        risks.append(":sneezing_face: *감기 주의* — 저온 건조. 손 씻기, 수분 섭취 철저히!")
    elif temp <= 10 and humidity <= 30:
        risks.append(":face_with_thermometer: *감기 유의* — 건조한 날씨. 환기와 수분 섭취 신경 쓰세요.")

    # 열사병/일사병 위험
    if temp >= 33 and humidity >= 60:
        risks.append(":face_with_head_bandage: *열사병 위험* — 고온다습! 야외 활동 자제, 시원한 곳에서 쉬세요.")
    elif temp >= 30 and humidity >= 70:
        risks.append(":hot_face: *일사병 유의* — 무더위. 그늘에서 자주 쉬세요.")

    # 동상 위험
    if temp <= -15 or (temp <= -10 and wind_ms >= 5):
        risks.append(":cold_face: *동상 위험* — 노출 피부 10분 이내 동상 가능!")
    elif temp <= -5 and wind_ms >= 8:
        risks.append(":face_with_thermometer: *동상 유의* — 피부 노출을 최소화하세요.")

    # 호흡기 (대기질)
    if pm25 is not None and pm25 > 75:
        risks.append(":lungs: *호흡기 주의* — 초미세먼지 매우 나쁨. 외출 시 KF94 마스크 필수!")
    elif pm25 is not None and pm25 > 35:
        risks.append(":mask: *호흡기 유의* — 미세먼지 나쁨. 호흡기 질환자 외출 자제.")

    # 자외선 피부 손상
    if uv is not None and uv >= 8:
        risks.append(":warning: *피부 손상 주의* — 자외선 매우 강함. 10분 이상 노출 시 화상 위험!")

    return risks


def calc_discomfort_index(temp, humidity):
    """불쾌지수 (Thom's Discomfort Index)"""
    di = 0.81 * temp + 0.01 * humidity * (0.99 * temp - 14.3) + 46.3
    return round(di, 1)


def discomfort_label(di):
    if di < 68:
        return "쾌적"
    if di < 75:
        return "보통"
    if di < 80:
        return "불쾌"
    return "매우 불쾌"


def calc_laundry_index(temp, humidity, wind_ms, precip_prob):
    """빨래 지수 (0~100, 높을수록 잘 마름)"""
    score = 50
    score += (temp - 15) * 2
    score -= (humidity - 50) * 0.5
    score += wind_ms * 3
    if precip_prob and precip_prob >= 50:
        score -= 30
    elif precip_prob and precip_prob >= 30:
        score -= 15
    return max(0, min(100, round(score)))


def laundry_label(score):
    if score >= 80:
        return "매우 좋음 :shirt:"
    if score >= 60:
        return "좋음 :tshirt:"
    if score >= 40:
        return "보통 :neutral_face:"
    if score >= 20:
        return "나쁨 :cloud:"
    return "매우 나쁨 :x:"


def calc_car_wash_index(precip_prob_today, precip_prob_tomorrow, pm25):
    """세차 지수 (0~100, 높을수록 세차 추천)"""
    score = 100
    if precip_prob_today and precip_prob_today >= 50:
        score -= 40
    elif precip_prob_today and precip_prob_today >= 30:
        score -= 20
    if precip_prob_tomorrow and precip_prob_tomorrow >= 50:
        score -= 30
    elif precip_prob_tomorrow and precip_prob_tomorrow >= 30:
        score -= 15
    if pm25 is not None:
        if pm25 > 75:
            score -= 30
        elif pm25 > 35:
            score -= 15
    return max(0, min(100, round(score)))


def car_wash_label(score):
    if score >= 80:
        return "세차 추천 :sparkles:"
    if score >= 60:
        return "세차 괜찮음 :ok_hand:"
    if score >= 40:
        return "보류 추천 :thinking_face:"
    return "세차 비추 :no_entry_sign:"


def calc_food_safety_index(temp, humidity):
    """식중독 지수 (기온 + 습도 기반)"""
    if temp >= 35 and humidity >= 80:
        return "위험 :rotating_light:"
    if temp >= 30 and humidity >= 70:
        return "경고 :warning:"
    if temp >= 26 and humidity >= 60:
        return "주의 :yellow_circle:"
    if temp >= 20:
        return "관심 :eyes:"
    return "안전 :white_check_mark:"


def get_activity_suggestions(temp, feels_like, main_weather, wind_ms, precip_prob, uv):
    """날씨에 맞는 활동 추천"""
    rain_cats = ("Rain", "Drizzle", "Thunderstorm", "Snow")

    if main_weather in rain_cats or (precip_prob and precip_prob >= 70):
        return ":house: 실내 카페 · 영화 · 독서 · 쇼핑몰"

    if temp <= 0:
        return ":cup_with_straw: 따뜻한 카페 · 실내 운동 · 온천/찜질방"

    if temp <= 10:
        return ":hiking_boot: 가벼운 산책 · 미술관/박물관 · 실내 운동"

    if temp >= 30:
        return ":swimmer: 수영 · 워터파크 · 에어컨 있는 실내"

    if 18 <= feels_like <= 25 and wind_ms < 5:
        if uv and uv < 6:
            return ":bicyclist: 자전거 · 공원 산책 · 피크닉 · 야외 카페"
        return ":person_walking: 산책 · 하이킹 · 야외 카페 (선크림 필수)"

    if 15 <= feels_like <= 27:
        return ":person_walking: 산책 · 조깅 · 야외 카페"

    return ":walking: 가벼운 외출 · 산책"


def get_greeting():
    """시간대별 인사말 (다국어)"""
    hour = datetime.now().hour
    g = L["greeting"]
    if hour < 6:
        return g["dawn"]
    if hour < 9:
        return g["morning"]
    if hour < 12:
        return g["am"]
    if hour < 18:
        return g["pm"]
    return g["evening"]


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
    sunrise_raw = daily["sunrise"][today_idx]
    sunset_raw = daily["sunset"][today_idx]
    sunrise = format_time(sunrise_raw)
    sunset = format_time(sunset_raw)
    sunshine = format_duration(daily["sunshine_duration"][today_idx])
    daylight = format_duration(daily["daylight_duration"][today_idx])
    daylight_bar, _ = calc_daylight_progress(sunrise_raw, sunset_raw)
    moon_phase = get_moon_phase()
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
    activity = get_activity_suggestions(temp, feels_like, main_weather, wind_speed, precip_prob, uv_max)
    health_risks = get_health_risks(temp, humidity, wind_speed, uv_max, pm25)
    tomorrow_alerts = get_tomorrow_alert(data)

    # 한국형 생활지수
    di = calc_discomfort_index(temp, humidity)
    laundry = calc_laundry_index(temp, humidity, wind_speed, precip_prob)
    tmr_prob = daily["precipitation_probability_max"][today_idx + 1] if today_idx + 1 < len(daily["time"]) else 0
    car_wash = calc_car_wash_index(precip_prob, tmr_prob, pm25)
    food_safety = calc_food_safety_index(temp, humidity)
    weekly_trend = build_weekly_trend(data) if DISPLAY.get("show_weekly_trend", True) else ""

    # 한줄 요약
    summary = f"{emoji} {temp}°C (체감 {feels_like}°C) · {description} · 습도 {humidity}% · 바람 {wind_speed}m/s"
    if precip_prob and precip_prob > 0:
        summary += f" · :droplet:{precip_prob}%"

    WEEKDAYS_KR = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    now = datetime.now()
    today = now.strftime("%Y년 %m월 %d일") + " " + WEEKDAYS_KR[now.weekday()]

    blocks = [
        # ── 헤더 ──
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{description} | {CITY_NAME} {get_greeting()}", "emoji": True},
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f":calendar: {today}"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": summary},
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
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"{daylight_bar} · {moon_phase}"},
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

        # ── 주간 기온 트렌드 ──
        *(
            [
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*:chart_with_upwards_trend: {L['sections']['weekly_trend']}*\n{weekly_trend}"},
                },
            ] if weekly_trend else []
        ),

        {"type": "divider"},

        # ── 생활지수 + 최적 외출 시간 ──
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*:bar_chart: {L['sections']['lifestyle_index']}*\n{lifestyle_bar(life_score)} *{life_score}* ({lifestyle_label(life_score)})",
            },
        },
        *(
            _build_best_time_block(data)
            if DISPLAY.get("show_best_time", True) else []
        ),
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f":hot_face: *{L['sections']['discomfort']}*\n{di} ({discomfort_label(di)})"},
                {"type": "mrkdwn", "text": f":shirt: *{L['sections']['laundry']}*\n{laundry} ({laundry_label(laundry)})"},
                {"type": "mrkdwn", "text": f":car: *{L['sections']['car_wash']}*\n{car_wash} ({car_wash_label(car_wash)})"},
                {"type": "mrkdwn", "text": f":bento: *{L['sections']['food_safety']}*\n{food_safety}"},
            ],
        },

        # ── 옷차림 + 활동 추천 ──
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*:womans_clothes: {L['sections']['outfit']}*\n{outfit}",
            },
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f":sparkles: *추천 활동:* {activity}"},
            ],
        },

        # ── 건강 위험 ──
        *(_build_health_block(health_risks)),

        # ── 내일 날씨 변화 알림 ──
        *(_build_tomorrow_alert_block(tomorrow_alerts)),

        # ── 오늘의 팁 ──
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*:bulb: {L['sections']['tips']}*\n" + "\n".join(f"• {t}" for t in tips),
            },
        },

        # ── 도시 비교 ──
        *_build_city_comparison_blocks(CONFIG.get("compare_cities", [])),

        # ── 푸터 ──
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"v{__version__} · Powered by Open-Meteo API | <https://github.com/concrete-sangminlee/weather-slack-bot|GitHub>"},
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


def _build_best_time_block(data):
    result = find_best_outdoor_time(data)
    if result is None:
        return [
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": ":house: 오늘은 실내 활동을 추천합니다."},
                ],
            },
        ]

    hour = result["hour"]
    feels = result["feels"]
    period = "오전" if hour < 12 else "오후"
    display_hour = hour if hour <= 12 else hour - 12
    if display_hour == 0:
        display_hour = 12

    return [
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f":runner: *최적 외출 시간:* {period} {display_hour}시경 (체감 {feels}°C)"},
            ],
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


def _build_health_block(risks):
    if not risks:
        return []
    return [
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*:hospital: 건강 주의보*\n" + "\n".join(f"• {r}" for r in risks),
            },
        },
    ]


def _build_tomorrow_alert_block(alerts):
    if not alerts:
        return []
    return [
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*:crystal_ball: 내일 날씨 변화*\n" + "\n".join(f"• {a}" for a in alerts),
            },
        },
    ]


def fetch_city_weather(city):
    """비교 도시 날씨 간단 조회"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "current": "temperature_2m,weather_code,relative_humidity_2m,wind_speed_10m",
        "timezone": TIMEZONE,
    }
    return _request_with_retry(url, params)


def _build_city_comparison_blocks(compare_cities):
    """비교 도시 날씨 블록 생성"""
    if not compare_cities or not DISPLAY.get("show_city_comparison", True):
        return []

    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fetch_city_weather, c): c for c in compare_cities[:3]}
        for future in as_completed(futures):
            city = futures[future]
            try:
                data = future.result()
                cur = data["current"]
                code = cur["weather_code"]
                desc, cat = WMO_DESCRIPTIONS.get(code, ("알 수 없음", "Clear"))
                emoji = WEATHER_EMOJIS.get(cat, ":thermometer:")
                temp = cur["temperature_2m"]
                hum = cur["relative_humidity_2m"]
                wind = kmh_to_ms(cur["wind_speed_10m"])
                results.append(f"{emoji} *{city['name']}* {temp}°C · {desc} · 습도 {hum}% · 바람 {wind}m/s")
            except Exception:
                results.append(f":x: *{city['name']}* 데이터 조회 실패")

    if not results:
        return []

    return [
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*:earth_asia: 다른 도시 날씨*\n" + "\n".join(results),
            },
        },
    ]


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
        # API 병렬 호출
        with ThreadPoolExecutor(max_workers=2) as executor:
            weather_future = executor.submit(fetch_weather)
            air_future = executor.submit(fetch_air_quality)

            data = weather_future.result()
            try:
                air_data = air_future.result()
            except Exception:
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
