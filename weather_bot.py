import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from config_loader import (
    CITY_LAT,
    CITY_LON,
    CITY_NAME,
    CONFIG,
    DAILY_DAYS,
    DISPLAY,
    PAST_DAYS,
    SLACK_BOT_TOKEN,
    SLACK_CHANNEL,
    TIMEZONE,
    TREND_DAYS,
    L,
)

__version__ = "4.1.0"

MAX_RETRIES = 3
RETRY_DELAY = 5

# 타임존 매핑 (주요 IANA → UTC offset)
_TZ_OFFSETS = {
    "Asia/Seoul": 9, "Asia/Tokyo": 9, "Asia/Shanghai": 8,
    "US/Eastern": -5, "US/Central": -6, "US/Pacific": -8,
    "Europe/London": 0, "Europe/Paris": 1, "Europe/Berlin": 1,
    "UTC": 0,
}


def now_local() -> datetime:
    """config의 타임존 기준 현재 시각 반환 (naive datetime)"""
    offset_hours = _TZ_OFFSETS.get(TIMEZONE, 9)
    tz = timezone(timedelta(hours=offset_hours))
    return datetime.now(tz).replace(tzinfo=None)

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


def kmh_to_ms(kmh: float) -> float:
    return round(kmh / 3.6, 1)


def wind_direction_to_text(degrees: float) -> str:
    idx = round(degrees / 22.5) % 16
    return WIND_DIRECTIONS[idx]


def uv_index_level(uv: float) -> str:
    if uv <= 2:
        return "낮음 😊"
    if uv <= 5:
        return "보통 🙂"
    if uv <= 7:
        return "높음 😎"
    if uv <= 10:
        return "매우 높음 🥵"
    return "위험 💀"


def _request_with_retry(url, params):
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(RETRY_DELAY * (attempt + 1))


def validate_weather_data(data: dict) -> bool:
    """API 응답 데이터 무결성 검증"""
    try:
        cur = data["current"]
        assert "temperature_2m" in cur
        assert "weather_code" in cur
        assert -80 <= cur["temperature_2m"] <= 60, f"비정상 기온: {cur['temperature_2m']}"
        assert 0 <= cur["relative_humidity_2m"] <= 100
        assert "daily" in data
        assert "hourly" in data
        return True
    except (KeyError, AssertionError) as e:
        print(f"⚠️ 데이터 검증 실패: {e}", file=sys.stderr)
        return False


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
        return "좋음 🟢"
    if aqi <= 100:
        return "보통 🟡"
    if aqi <= 150:
        return "민감군 나쁨 🟠"
    if aqi <= 200:
        return "나쁨 🔴"
    if aqi <= 300:
        return "매우 나쁨 ❗"
    return "위험 💀"


def pm_level(pm25):
    if pm25 <= 15:
        return "좋음"
    if pm25 <= 35:
        return "보통"
    if pm25 <= 75:
        return "나쁨"
    return "매우 나쁨"


def format_visibility(meters: float) -> str:
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


def weather_grade(score: int) -> tuple[str, str]:
    """생활지수를 A~F 등급으로 변환"""
    if score >= 90:
        return "A+", "#2ecc71"  # green
    if score >= 80:
        return "A", "#27ae60"
    if score >= 70:
        return "B+", "#3498db"  # blue
    if score >= 60:
        return "B", "#2980b9"
    if score >= 50:
        return "C+", "#f1c40f"  # yellow
    if score >= 40:
        return "C", "#e67e22"  # orange
    if score >= 30:
        return "D", "#e74c3c"  # red
    return "F", "#8e44ad"  # purple


def lifestyle_label(score):
    if score >= 90:
        return "최고 ⭐"
    if score >= 75:
        return "좋음 🟢"
    if score >= 60:
        return "보통 🟡"
    if score >= 40:
        return "나쁨 🟠"
    return "매우 나쁨 🔴"


def lifestyle_bar(score):
    filled = round(score / 10)
    return "🟩" * filled + "⬜" * (10 - filled)


def calc_wind_chill(temp: float, wind_ms: float) -> float:
    """윈드칠 공식 (JAG/TI, 10°C 이하 + 풍속 1.3m/s 이상)"""
    wind_kmh = wind_ms * 3.6
    if temp > 10 or wind_kmh < 4.8:
        return temp
    wc = 13.12 + 0.6215 * temp - 11.37 * (wind_kmh ** 0.16) + 0.3965 * temp * (wind_kmh ** 0.16)
    return round(wc, 1)


def calc_heat_index(temp: float, humidity: float) -> float:
    """열지수 (Rothfusz, 27°C 이상 + 습도 40% 이상)"""
    if temp < 27 or humidity < 40:
        return temp
    t = temp
    r = humidity
    hi = (-8.7847 + 1.6114 * t + 2.3385 * r - 0.1461 * t * r
          - 0.01231 * t**2 - 0.01642 * r**2
          + 0.002212 * t**2 * r + 0.0007255 * t * r**2
          - 0.000003582 * t**2 * r**2)
    return round(hi, 1)


def build_comfort_timeline(data):
    """시간별 쾌적도 타임라인 (07~21시)"""
    hourly = data["hourly"]
    now = now_local()

    hours = []
    for i, time_str in enumerate(hourly["time"]):
        dt = datetime.fromisoformat(time_str)
        if dt.date() != now.date():
            continue
        if dt.hour < 7 or dt.hour > 21:
            continue

        t = hourly["temperature_2m"][i]
        hum = hourly["relative_humidity_2m"][i]
        wind = kmh_to_ms(hourly["wind_speed_10m"][i])
        prob = hourly["precipitation_probability"][i] or 0
        code = hourly["weather_code"][i]
        _, cat = WMO_DESCRIPTIONS.get(code, ("", "Clear"))

        # 쾌적도 점수 (0~10)
        score = 10
        if 18 <= t <= 24:
            pass
        elif 15 <= t <= 27:
            score -= 1
        elif 10 <= t <= 30:
            score -= 3
        elif 5 <= t <= 33:
            score -= 5
        else:
            score -= 7

        if 40 <= hum <= 60:
            pass
        elif 30 <= hum <= 70:
            score -= 1
        else:
            score -= 2

        if wind >= 8:
            score -= 2
        elif wind >= 5:
            score -= 1

        if prob >= 60:
            score -= 3
        elif prob >= 30:
            score -= 1

        if cat in ("Rain", "Drizzle", "Thunderstorm", "Snow"):
            score -= 2

        score = max(0, min(10, score))

        # 블록 문자로 표현
        if score >= 8:
            block = "🟩"
        elif score >= 6:
            block = "🟨"
        elif score >= 4:
            block = "🟧"
        else:
            block = "🟥"

        hours.append((dt.hour, block, score))

    if not hours:
        return ""

    bar = "".join(b for _, b, _ in hours)
    return f"{bar}\n`07 · · 10 · · 13 · · 16 · · 19 · · 21`"


def find_best_outdoor_time(data):
    """오늘 시간별 데이터에서 가장 외출하기 좋은 시간대 찾기"""
    hourly = data["hourly"]
    now = now_local()
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
                bar += "🟦" if p <= (lo_pos + hi_pos) // 2 else "🟧"
            else:
                bar += "  "

        lines.append(f"`{day}` {lo:+.0f}° {bar} {hi:+.0f}°")

    return "\n".join(lines)


def calc_daylight_progress(sunrise_str, sunset_str):
    """현재 시각이 일출~일몰 중 어디인지 프로그레스 바로 표현"""
    now = now_local()
    sunrise = datetime.fromisoformat(sunrise_str)
    sunset = datetime.fromisoformat(sunset_str)

    if now < sunrise:
        return "🌑 일출 전", 0
    if now > sunset:
        return "🌑 일몰 후", 100

    total = (sunset - sunrise).total_seconds()
    elapsed = (now - sunrise).total_seconds()
    pct = int(elapsed / total * 100)

    bar_len = 10
    filled = round(pct / 100 * bar_len)
    bar = "☀️" + "🟧" * filled + "⬛" * (bar_len - filled) + "🌙"

    remaining = sunset - now
    hours = int(remaining.total_seconds() // 3600)
    minutes = int((remaining.total_seconds() % 3600) // 60)

    return f"{bar} 일몰까지 {hours}시간 {minutes}분", pct


def get_moon_phase() -> str:
    """현재 달의 위상 계산 (Conway's method)"""
    now = now_local()
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
        return "🌑 삭(새달)"
    if phase_pct < 0.216:
        return "🌒 초승달"
    if phase_pct < 0.283:
        return "🌓 상현달"
    if phase_pct < 0.466:
        return "🌔 상현망간"
    if phase_pct < 0.534:
        return "🌕 보름달"
    if phase_pct < 0.716:
        return "🌖 하현망간"
    if phase_pct < 0.783:
        return "🌗 하현달"
    if phase_pct < 0.966:
        return "🌘 그믐달"
    return "🌑 삭(새달)"


def calc_golden_hour(sunrise_str, sunset_str):
    """사진 촬영 골든아워 계산 (일출/일몰 전후 30분)"""
    sunrise = datetime.fromisoformat(sunrise_str)
    sunset = datetime.fromisoformat(sunset_str)

    morning_start = sunrise.strftime("%H:%M")
    morning_end = (sunrise.replace(minute=sunrise.minute + 30) if sunrise.minute + 30 < 60
                   else sunrise.replace(hour=sunrise.hour + 1, minute=(sunrise.minute + 30) % 60)).strftime("%H:%M")

    evening_start = (sunset.replace(minute=sunset.minute - 30) if sunset.minute >= 30
                     else sunset.replace(hour=sunset.hour - 1, minute=sunset.minute + 30)).strftime("%H:%M")
    evening_end = sunset.strftime("%H:%M")

    return f"📷 {morning_start}~{morning_end} / {evening_start}~{evening_end}"


def get_tomorrow_alert(data):
    """내일 날씨가 오늘과 크게 다를 때 알림 생성"""
    daily = data["daily"]
    today_idx = PAST_DAYS
    tmr_idx = today_idx + 1
    if tmr_idx >= len(daily["time"]):
        return None

    t_max = daily["temperature_2m_max"][today_idx]
    tmr_max = daily["temperature_2m_max"][tmr_idx]
    tmr_code = daily["weather_code"][tmr_idx]
    tmr_prob = daily["precipitation_probability_max"][tmr_idx]
    tmr_desc, tmr_cat = WMO_DESCRIPTIONS.get(tmr_code, ("알 수 없음", "Clear"))
    today_code = daily["weather_code"][today_idx]
    _, today_cat = WMO_DESCRIPTIONS.get(today_code, ("알 수 없음", "Clear"))

    alerts = []

    # 기온 급변
    max_diff = tmr_max - t_max
    if max_diff >= 8:
        alerts.append(f"📈 내일 최고기온 {tmr_max}°C로 *{max_diff:+.0f}°C* 급상승!")
    elif max_diff <= -8:
        alerts.append(f"📉 내일 최고기온 {tmr_max}°C로 *{max_diff:+.0f}°C* 급하락!")
    elif abs(max_diff) >= 5:
        sign = "상승" if max_diff > 0 else "하락"
        alerts.append(f"🌡️ 내일 최고기온 {tmr_max}°C ({max_diff:+.0f}°C {sign})")

    # 날씨 급변 (맑음 → 비/눈 또는 반대)
    rain_cats = ("Rain", "Drizzle", "Thunderstorm", "Snow")
    if today_cat not in rain_cats and tmr_cat in rain_cats:
        emoji = WEATHER_EMOJIS.get(tmr_cat, "☁️")
        alerts.append(f"{emoji} 내일 {tmr_desc} 예보! 우산 미리 챙기세요.")
    elif today_cat in rain_cats and tmr_cat not in rain_cats:
        alerts.append(f"☀️ 내일은 날이 개요! ({tmr_desc})")

    # 강수 확률 급등
    today_prob = daily["precipitation_probability_max"][today_idx]
    if tmr_prob >= 60 and today_prob < 30:
        alerts.append(f"☂️ 내일 강수확률 {tmr_prob}%로 급등!")

    return alerts if alerts else None


def get_health_risks(temp, humidity, wind_ms, uv, pm25):
    """건강 위험 지수 생성"""
    risks = []

    # 감기/독감 위험 (저온 + 건조)
    if temp <= 5 and humidity <= 40:
        risks.append("🤧 *감기 주의* — 저온 건조. 손 씻기, 수분 섭취 철저히!")
    elif temp <= 10 and humidity <= 30:
        risks.append("🤒 *감기 유의* — 건조한 날씨. 환기와 수분 섭취 신경 쓰세요.")

    # 열사병/일사병 위험
    if temp >= 33 and humidity >= 60:
        risks.append("🤕 *열사병 위험* — 고온다습! 야외 활동 자제, 시원한 곳에서 쉬세요.")
    elif temp >= 30 and humidity >= 70:
        risks.append("🥵 *일사병 유의* — 무더위. 그늘에서 자주 쉬세요.")

    # 동상 위험
    if temp <= -15 or (temp <= -10 and wind_ms >= 5):
        risks.append("🥶 *동상 위험* — 노출 피부 10분 이내 동상 가능!")
    elif temp <= -5 and wind_ms >= 8:
        risks.append("🤒 *동상 유의* — 피부 노출을 최소화하세요.")

    # 호흡기 (대기질)
    if pm25 is not None and pm25 > 75:
        risks.append("😷 *호흡기 주의* — 초미세먼지 매우 나쁨. 외출 시 KF94 마스크 필수!")
    elif pm25 is not None and pm25 > 35:
        risks.append("😷 *호흡기 유의* — 미세먼지 나쁨. 호흡기 질환자 외출 자제.")

    # 자외선 피부 손상
    if uv is not None and uv >= 8:
        risks.append("⚠️ *피부 손상 주의* — 자외선 매우 강함. 10분 이상 노출 시 화상 위험!")

    return risks


def calc_discomfort_index(temp: float, humidity: float) -> float:
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
        return "매우 좋음 👔"
    if score >= 60:
        return "좋음 👕"
    if score >= 40:
        return "보통 😐"
    if score >= 20:
        return "나쁨 ☁️"
    return "매우 나쁨 ❌"


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
        return "세차 추천 ✨"
    if score >= 60:
        return "세차 괜찮음 👌"
    if score >= 40:
        return "보류 추천 🤔"
    return "세차 비추 🚫"


def calc_food_safety_index(temp, humidity):
    """식중독 지수 (기온 + 습도 기반)"""
    if temp >= 35 and humidity >= 80:
        return "위험 🚨"
    if temp >= 30 and humidity >= 70:
        return "경고 ⚠️"
    if temp >= 26 and humidity >= 60:
        return "주의 ⚠️"
    if temp >= 20:
        return "관심 👀"
    return "안전 ✅"


def get_activity_suggestions(temp, feels_like, main_weather, wind_ms, precip_prob, uv):
    """날씨에 맞는 활동 추천"""
    rain_cats = ("Rain", "Drizzle", "Thunderstorm", "Snow")

    if main_weather in rain_cats or (precip_prob and precip_prob >= 70):
        return "🏠 실내 카페 · 영화 · 독서 · 쇼핑몰"

    if temp <= 0:
        return "☕ 따뜻한 카페 · 실내 운동 · 온천/찜질방"

    if temp <= 10:
        return "👣 가벼운 산책 · 미술관/박물관 · 실내 운동"

    if temp >= 30:
        return "🏊 수영 · 워터파크 · 에어컨 있는 실내"

    if 18 <= feels_like <= 25 and wind_ms < 5:
        if uv and uv < 6:
            return "🚴 자전거 · 공원 산책 · 피크닉 · 야외 카페"
        return "🚶 산책 · 하이킹 · 야외 카페 (선크림 필수)"

    if 15 <= feels_like <= 27:
        return "🚶 산책 · 조깅 · 야외 카페"

    return "🚶 가벼운 외출 · 산책"


def get_seasonal_note():
    """한국 계절/절기 기반 메시지"""
    now = now_local()
    month = now.month
    day = now.day

    # 절기/계절 이벤트
    seasonal = {
        (1, 1): "🎍 새해 첫날! 올해도 건강하세요.",
        (2, 4): "🌱 입춘이에요. 봄이 시작됩니다!",
        (3, 1): "🇰🇷 삼일절. 역사를 기억하는 하루.",
        (3, 14): "🍫 화이트데이! 달콤한 하루 보내세요.",
        (5, 5): "👶 어린이날! 동심으로 돌아가는 하루.",
        (5, 8): "🤱 어버이날. 부모님께 감사를 전하세요.",
        (6, 6): "🇰🇷 현충일. 호국영령을 기립니다.",
        (8, 15): "🇰🇷 광복절. 독립의 기쁨을 기억합니다.",
        (9, 1): "📚 새 학기 시작! 힘찬 출발 응원합니다.",
        (10, 3): "🇰🇷 개천절. 하늘이 열린 날.",
        (10, 9): "🇰🇷 한글날. 세종대왕님 감사합니다.",
        (12, 25): "🎄 메리 크리스마스!",
        (12, 31): "🎊 한 해의 마지막 날! 수고 많으셨어요.",
    }

    # 정확한 날짜 매칭
    key = (month, day)
    if key in seasonal:
        return seasonal[key]

    # 계절별 기간 메시지
    if month == 3 and 20 <= day <= 31:
        return "🌸 벚꽃 개화 시즌이에요! 꽃놀이 계획 세워보세요."
    if month == 4 and 1 <= day <= 15:
        return "🌸 벚꽃이 만개하는 시기예요. 봄나들이 어떠세요?"
    if month == 4 and 15 < day <= 30:
        return "🌿 신록의 계절, 초록빛이 짙어지고 있어요."
    if month == 5 and 1 <= day <= 20:
        return "🌹 장미가 피기 시작하는 계절이에요."
    if month in (6, 7) and 15 <= day <= 31 and month == 6 or month == 7 and day <= 20:
        return "🌧️ 장마철이에요. 우산과 제습에 신경 쓰세요."
    if month == 7 and 20 < day <= 31:
        return "🏖️ 본격 여름 휴가철! 더위 조심하세요."
    if month == 8 and 1 <= day <= 20:
        return "🌻 한여름이에요. 수분 섭취와 자외선 차단 필수!"
    if month == 9 and 15 <= day <= 30:
        return "🍂 가을이 성큼 다가왔어요. 단풍 준비 되셨나요?"
    if month == 10 and 10 <= day <= 31:
        return "🍁 단풍이 물드는 시기예요. 산행 추천!"
    if month == 11 and 1 <= day <= 15:
        return "🍂 늦가을, 첫서리가 내릴 수 있어요."
    if month == 11 and 15 < day <= 30:
        return "🧣 초겨울 한파에 대비하세요."
    if month == 12 and 1 <= day <= 24:
        return "⛄ 겨울이에요. 따뜻한 옷차림 필수!"
    if month in (1, 2):
        return "❄️ 한겨울이에요. 건강 관리에 유의하세요."
    if month == 3 and day < 20:
        return "🌱 봄이 오고 있어요. 조금만 더 기다려주세요!"

    return None


def get_weather_mood(main_weather, temp, life_score):
    """날씨 상태에 따른 인격 한줄 메시지"""
    if life_score >= 85:
        moods = [
            "오늘 날씨 완전 최고예요! 기분 좋은 하루 될 거예요 ✨",
            "이런 날씨에 실내에만 있으면 아까워요! 밖으로 나가보세요 🌈",
            "날씨가 너무 좋아서 할 말을 잃었어요... 그냥 나가세요 😊",
        ]
    elif main_weather in ("Rain", "Drizzle"):
        moods = [
            "비 오는 날엔 따뜻한 음료 한 잔이 최고죠 ☕",
            "촉촉한 빗소리와 함께하는 하루, 나쁘지 않아요 🎵",
            "우산 챙기셨죠? 안 챙기셨으면 지금이라도! 🌂",
        ]
    elif main_weather == "Snow":
        moods = [
            "눈 오는 날이에요! 세상이 하얗게 변하는 중 ⛄",
            "눈길 조심하시고, 따뜻하게 입고 나가세요 ❄️",
        ]
    elif main_weather == "Thunderstorm":
        moods = [
            "천둥번개 치는 날이에요. 안전한 실내에 계세요! ⛈️",
            "밖에서 번쩍번쩍! 오늘은 집이 최고예요 🏠",
        ]
    elif temp >= 33:
        moods = [
            "찜통더위에요... 물 많이 드세요! 진심이에요 💦",
            "에어컨이 없으면 생존이 불가능한 날이에요 🥵",
        ]
    elif temp <= -5:
        moods = [
            "으으... 추워서 몸이 자동으로 웅크려져요 🥶",
            "오늘은 이불 밖이 위험합니다. 진짜로요 🛏️",
        ]
    elif main_weather == "Fog":
        moods = [
            "안개가 자욱해요. 운전 조심, 서행하세요 🌫️",
        ]
    elif life_score <= 35:
        moods = [
            "오늘 밖에 나가기 좀 그런 날이에요... 집콕 추천 🏠",
            "날씨가 좀 험하네요. 무리하지 마세요 💪",
        ]
    else:
        moods = [
            "무난한 하루가 될 것 같아요. 파이팅! 💪",
            "오늘도 좋은 하루 보내세요! 날씨 요정이 응원합니다 🧚",
            "특별한 건 없지만, 그게 또 좋은 거죠 🍃",
        ]

    # 날짜 기반으로 매일 다른 메시지 선택 (랜덤처럼 보이지만 결정적)
    day_seed = now_local().timetuple().tm_yday
    return moods[day_seed % len(moods)]


def get_greeting() -> str:
    """시간대별 인사말 (다국어)"""
    hour = now_local().hour
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
        outfit = "🥶 패딩·롱패딩, 목도리, 장갑, 귀마개, 기모 안감"
    elif t <= -5:
        outfit = "🧥 두꺼운 패딩, 목도리, 장갑, 기모 바지"
    elif t <= 0:
        outfit = "🧥 패딩·두꺼운 코트, 니트, 기모 바지"
    elif t <= 5:
        outfit = "🧥 코트·가죽자켓, 니트, 히트텍"
    elif t <= 10:
        outfit = "👔 자켓·트렌치코트, 니트·맨투맨"
    elif t <= 15:
        outfit = "👔 가디건·얇은 자켓, 맨투맨, 긴 바지"
    elif t <= 20:
        outfit = "👕 얇은 긴팔·셔츠, 면바지"
    elif t <= 25:
        outfit = "👕 반팔·얇은 셔츠, 면바지·린넨"
    elif t <= 30:
        outfit = "👕 반팔·민소매, 반바지·린넨 바지"
    else:
        outfit = "👕 민소매·나시, 반바지, 통풍 잘 되는 옷"

    extras = []
    if main_weather in ("Rain", "Drizzle", "Thunderstorm") or (precip_prob and precip_prob >= 50):
        extras.append("☂️ 우산")
    if main_weather == "Snow":
        extras.append("👟 방수 신발")

    if extras:
        outfit += " + " + " ".join(extras)

    return outfit


def generate_tips(main_weather, temp, feels_like, temp_max, temp_min,
                  humidity, uv, wind_ms, gust_ms, precip_prob,
                  precip_sum, cloud_cover, snow_sum, aqi=None, pm25=None):
    tips = []

    # ── 강수 관련 ──
    if main_weather == "Thunderstorm":
        tips.append("⛈️ 뇌우가 치고 있어요! 가급적 실내에 머무르세요.")
    elif main_weather in ("Rain", "Drizzle"):
        if precip_sum >= 30:
            tips.append("🌊 폭우 예상! 저지대 침수에 주의하고, 외출을 자제하세요.")
        elif precip_sum >= 10:
            tips.append("☔ 비가 많이 옵니다. 우산과 방수 신발을 챙기세요.")
        else:
            tips.append("☂️ 우산 꼭 챙기세요!")
    elif precip_prob is not None and precip_prob >= 70:
        tips.append(f"🌂 비 올 확률 {precip_prob}%! 우산 꼭 챙기세요.")
    elif precip_prob is not None and precip_prob >= 40:
        tips.append(f"🌂 비 올 확률 {precip_prob}%. 접이식 우산 하나 챙기면 좋겠어요.")

    # ── 눈 관련 ──
    if main_weather == "Snow":
        if snow_sum >= 5:
            tips.append("⛄ 폭설 주의! 대중교통 이용을 권장합니다.")
        else:
            tips.append("❄️ 눈이 내려요! 빙판길 조심하세요.")
    elif temp <= 0 and precip_prob is not None and precip_prob >= 30:
        tips.append("❄️ 영하에 강수 확률이 있어요. 도로 결빙에 주의하세요.")

    # ── 기온 관련 ──
    if temp <= -10:
        tips.append("🥶 강추위! 동파 주의, 노출 피부를 최소화하세요.")
    elif temp <= -5:
        tips.append("🥶 매서운 추위입니다. 내복과 두꺼운 외투 필수!")
    elif temp <= 0:
        tips.append("❄️ 영하입니다. 목도리, 장갑 챙기세요.")
    elif temp <= 5:
        tips.append("🧥 쌀쌀합니다. 따뜻한 외투를 입으세요.")
    elif temp <= 10:
        tips.append("🧤 약간 쌀쌀해요. 겉옷 하나 걸치세요.")

    if temp >= 35:
        tips.append("🔥 극심한 폭염! 야외 활동을 피하고 수분을 충분히 섭취하세요.")
    elif temp >= 33:
        tips.append("🥵 폭염 주의! 시원한 물 자주 마시고 그늘에서 쉬세요.")
    elif temp >= 30:
        tips.append("☀️ 무더운 날씨입니다. 통풍 잘 되는 옷을 입으세요.")
    elif temp >= 28:
        tips.append("😎 더운 날이에요. 시원하게 입으세요.")

    # ── 일교차 ──
    diff = temp_max - temp_min
    if diff >= 15:
        tips.append(f"🌡️ 일교차 {diff:.0f}°C! 겹쳐 입기 필수. 감기 조심하세요.")
    elif diff >= 10:
        tips.append(f"🌡️ 일교차가 {diff:.0f}°C로 큽니다. 얇은 겉옷을 챙기세요.")

    # ── 습도 관련 ──
    if humidity >= 90 and main_weather not in ("Rain", "Drizzle", "Thunderstorm", "Snow"):
        tips.append("💦 습도 매우 높음! 빨래는 실내 건조하세요.")
    elif humidity >= 80 and main_weather not in ("Rain", "Drizzle", "Thunderstorm", "Snow"):
        tips.append("💧 습도가 높아요. 불쾌지수가 높을 수 있습니다.")
    elif humidity <= 20:
        tips.append("🌵 공기가 매우 건조합니다. 보습제를 바르고 물을 자주 마시세요.")
    elif humidity <= 30:
        tips.append("💨 건조한 날씨예요. 수분 섭취와 피부 보습에 신경 쓰세요.")

    # ── 자외선 관련 ──
    if uv is not None:
        if uv >= 11:
            tips.append("💀 자외선 극도로 위험! 한낮 외출 자제, 선크림 SPF50+ 필수.")
        elif uv >= 8:
            tips.append("🧴 자외선 매우 강함! 선크림·선글라스·모자 3종 세트 챙기세요.")
        elif uv >= 6:
            tips.append("🧴 자외선 지수가 높아요. 선크림을 바르세요.")
        elif uv >= 3:
            tips.append("😎 자외선 보통. 장시간 야외 활동 시 선크림 추천.")

    # ── 바람 관련 ──
    if wind_ms >= 14:
        tips.append("🌪️ 강풍 경보급! 외출 자제, 간판·구조물 낙하 주의.")
    elif wind_ms >= 11:
        tips.append("🌬️ 강풍 주의! 우산이 뒤집힐 수 있어요. 외출 시 조심하세요.")
    elif wind_ms >= 8:
        tips.append("💨 바람이 꽤 셉니다. 체감 온도가 낮을 수 있어요.")
    elif wind_ms >= 5:
        tips.append("🍃 바람이 좀 불어요. 머리카락 날림 주의!")

    if gust_ms >= 20:
        tips.append(f"⚠️ 돌풍 {gust_ms} m/s 예상! 가벼운 물건이 날아갈 수 있어요.")

    # ── 안개 ──
    if main_weather == "Fog":
        tips.append("🌫️ 안개가 짙습니다. 운전 시 전조등 켜고 서행하세요.")

    # ── 대기질 관련 ──
    if pm25 is not None:
        if pm25 > 75:
            tips.append("🚫 초미세먼지 매우 나쁨! 외출 자제, KF94 마스크 필수.")
        elif pm25 > 35:
            tips.append("😷 초미세먼지 나쁨. 마스크를 착용하세요.")
    if aqi is not None and aqi > 150 and (pm25 is None or pm25 <= 35):
        tips.append("😷 대기질이 나쁩니다. 민감군은 외출을 줄이세요.")

    # ── 흐림/구름 ──
    if cloud_cover >= 90 and main_weather not in ("Rain", "Drizzle", "Thunderstorm", "Snow", "Fog"):
        tips.append("☁️ 하늘이 잔뜩 흐려요. 기분 전환에 따뜻한 음료 한 잔 어때요?")

    # ── 쾌적한 날씨 ──
    if not tips:
        if 18 <= temp <= 25 and 40 <= humidity <= 60 and wind_ms < 5:
            tips.append("🌈 완벽한 날씨! 산책하기 딱 좋은 날이에요.")
        elif 15 <= temp <= 27 and humidity < 70:
            tips.append("🍃 쾌적한 날씨입니다. 좋은 하루 보내세요!")
        elif 10 <= temp <= 15:
            tips.append("🌸 봄바람이 느껴지는 날이에요. 가벼운 산책 어떠세요?")
        else:
            tips.append("🍃 좋은 하루 보내세요!")

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
    emoji = WEATHER_EMOJIS.get(main_weather, "🌡️")

    temp = cur["temperature_2m"]
    feels_like = cur["apparent_temperature"]
    humidity = cur["relative_humidity_2m"]
    cloud_cover = cur["cloud_cover"]
    pressure = cur["pressure_msl"]
    wind_speed = kmh_to_ms(cur["wind_speed_10m"])
    wind_gust = kmh_to_ms(cur["wind_gusts_10m"])
    wind_dir = wind_direction_to_text(cur["wind_direction_10m"])
    visibility = cur.get("visibility", 0)

    today_idx = PAST_DAYS
    temp_max = daily["temperature_2m_max"][today_idx]
    temp_min = daily["temperature_2m_min"][today_idx]
    precip_sum = daily["precipitation_sum"][today_idx]
    precip_prob = daily["precipitation_probability_max"][today_idx]
    snow_sum = daily["snowfall_sum"][today_idx]
    sunrise_raw = daily["sunrise"][today_idx]
    sunset_raw = daily["sunset"][today_idx]
    sunrise = format_time(sunrise_raw)
    sunset = format_time(sunset_raw)
    sunshine = format_duration(daily["sunshine_duration"][today_idx])
    daylight = format_duration(daily["daylight_duration"][today_idx])
    daylight_bar, _ = calc_daylight_progress(sunrise_raw, sunset_raw)
    moon_phase = get_moon_phase()
    golden_hour = calc_golden_hour(sunrise_raw, sunset_raw) if DISPLAY.get("show_golden_hour", True) else ""
    gust_max = kmh_to_ms(daily["wind_gusts_10m_max"][today_idx])
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
    mood = get_weather_mood(main_weather, temp, life_score)
    comfort_tl = build_comfort_timeline(data)
    wc = calc_wind_chill(temp, wind_speed)
    hi = calc_heat_index(temp, humidity)
    grade, grade_color = weather_grade(life_score)
    seasonal = get_seasonal_note()

    # 한줄 요약
    summary = f"{emoji} {temp}°C (체감 {feels_like}°C) · {description} · 습도 {humidity}% · 바람 {wind_speed}m/s"
    if precip_prob and precip_prob > 0:
        summary += f" · 💧{precip_prob}%"

    WEEKDAYS_KR = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    now = now_local()
    today = now.strftime("%Y년 %m월 %d일") + " " + WEEKDAYS_KR[now.weekday()]

    blocks = [
        # ── 헤더 + 요약 ──
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{description} | {CITY_NAME} {get_greeting()}", "emoji": True},
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"📅 {today} · {summary}"}],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"_{mood}_"},
        },
        {"type": "divider"},

        # ── 기온 + 날씨 ──
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"{emoji} *현재* {temp}°C\n체감 {feels_like}°C"},
                {"type": "mrkdwn", "text": f"⬆️ *최고* {temp_max}°C\n⬇️ *최저* {temp_min}°C"},
                {"type": "mrkdwn", "text": f"💧 *습도* {humidity}%\n🔄 *기압* {pressure}hPa"},
                {"type": "mrkdwn", "text": f"☁️ *구름* {cloud_cover}%\n👁️ *가시거리* {format_visibility(visibility).split(' (')[0]}"},
            ],
        },
        *(
            [{
                "type": "context",
                "elements": [{"type": "mrkdwn", "text":
                    f"📈 {yesterday_cmp}"
                    + (f" · 🧊 풍속냉각 {wc}°C" if wc != temp else "")
                    + (f" · 🔥 열지수 {hi}°C" if hi != temp else "")
                }],
            }] if yesterday_cmp or wc != temp or hi != temp else []
        ),
        {"type": "divider"},

        # ── 강수 + 바람 (컴팩트) ──
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"☔ *강수* {precip_prob}%\n예상 {precip_sum}mm"},
                {"type": "mrkdwn", "text": f"🌬️ *바람* {wind_speed}m/s ({wind_dir})\n돌풍 {wind_gust}m/s"},
            ],
        },
        {"type": "divider"},

        # ── 일조 & UV (컴팩트) ──
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"🌅 *일출* {sunrise} / 🌇 *일몰* {sunset}\n{daylight} ({sunshine} 일조)"},
                {"type": "mrkdwn", "text": f"🏖️ *UV* {uv_max} ({uv_index_level(uv_max)})\n🔆 *일사량* {radiation} MJ/m²"},
            ],
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"{daylight_bar} · {moon_phase}" + (f" · {golden_hour}" if golden_hour else "")}],
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
                {"type": "section", "text": {"type": "mrkdwn", "text": "*🕐 시간별 예보*"}},
                *_build_hourly_blocks(data),
            ] if DISPLAY["show_hourly"] else []
        ),

        # ── 3일 예보 ──
        *(
            [
                {"type": "divider"},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*📅 {DAILY_DAYS}일 예보*"}},
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
                    "text": {"type": "mrkdwn", "text": f"*📈 {L['sections']['weekly_trend']}*\n{weekly_trend}"},
                },
            ] if weekly_trend else []
        ),

        {"type": "divider"},

        # ── 시간대별 쾌적도 타임라인 ──
        *(
            [{
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*🕐 쾌적도 타임라인*\n{comfort_tl}"},
            }] if comfort_tl else []
        ),

        # ── 생활지수 + 최적 외출 시간 ──
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*📊 {L['sections']['lifestyle_index']}*  등급 *{grade}*\n{lifestyle_bar(life_score)} *{life_score}점* ({lifestyle_label(life_score)})",
            },
        },
        *(
            _build_best_time_block(data)
            if DISPLAY.get("show_best_time", True) else []
        ),
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"🥵 *{L['sections']['discomfort']}*\n{di} ({discomfort_label(di)})"},
                {"type": "mrkdwn", "text": f"👔 *{L['sections']['laundry']}*\n{laundry} ({laundry_label(laundry)})"},
                {"type": "mrkdwn", "text": f"🚗 *{L['sections']['car_wash']}*\n{car_wash} ({car_wash_label(car_wash)})"},
                {"type": "mrkdwn", "text": f"🍱 *{L['sections']['food_safety']}*\n{food_safety}"},
            ],
        },

        # ── 옷차림 + 활동 추천 ──
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*👗 {L['sections']['outfit']}*\n{outfit}",
            },
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"✨ *추천 활동:* {activity}"},
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
                "text": f"*💡 {L['sections']['tips']}*\n" + "\n".join(f"• {t}" for t in tips),
            },
        },

        # ── 도시 비교 ──
        *_build_city_comparison_blocks(CONFIG.get("compare_cities", [])),

        # ── 계절 노트 ──
        *(
            [{
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": seasonal}],
            }] if seasonal else []
        ),

        # ── 명언 + 푸터 ──
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"_{get_weather_quote(main_weather)}_"},
            ],
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text":
                    f"v{__version__} · 📡 {cur['time']} 기준"
                    f" · <https://github.com/concrete-sangminlee/weather-slack-bot|GitHub>"
                },
            ],
        },
    ]

    return blocks, grade_color, main_weather


def _build_air_quality_blocks(aqi, pm25, pm10, co, no2, o3):
    if aqi is None:
        return []

    return [
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"💨 *대기질 (AQI)*\n{aqi} ({aqi_level(aqi)})"},
                {"type": "mrkdwn", "text": f"🔹 *초미세먼지 PM2.5*\n{pm25} µg/m³ ({pm_level(pm25)})"},
                {"type": "mrkdwn", "text": f"🔸 *미세먼지 PM10*\n{pm10} µg/m³"},
                {"type": "mrkdwn", "text": f"🧪 *오존*\n{o3} µg/m³"},
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
    now = now_local()
    current_hour = now.hour

    lines = []
    count = 0
    for i, time_str in enumerate(hourly["time"]):
        dt = datetime.fromisoformat(time_str)
        if dt.date() == now.date() and dt.hour > current_hour and count < 6:
            code = hourly["weather_code"][i]
            desc, cat = WMO_DESCRIPTIONS.get(code, ("알 수 없음", "Clear"))
            emoji = WEATHER_EMOJIS.get(cat, "🌡️")
            t = hourly["temperature_2m"][i]
            prob = hourly["precipitation_probability"][i]
            wind = kmh_to_ms(hourly["wind_speed_10m"][i])
            lines.append(f"`{dt.hour:02d}시` {emoji} *{t}°C*  💧{prob}%  💨{wind}m/s")
            count += 1

    # 오늘 남은 시간이 부족하면 내일 아침부터 채우기
    if count < 6:
        for i, time_str in enumerate(hourly["time"]):
            dt = datetime.fromisoformat(time_str)
            if dt.date() > now.date() and count < 6:
                code = hourly["weather_code"][i]
                desc, cat = WMO_DESCRIPTIONS.get(code, ("알 수 없음", "Clear"))
                emoji = WEATHER_EMOJIS.get(cat, "🌡️")
                t = hourly["temperature_2m"][i]
                prob = hourly["precipitation_probability"][i]
                wind = kmh_to_ms(hourly["wind_speed_10m"][i])
                day_label = "내일" if (dt.date() - now.date()).days == 1 else "모레"
                lines.append(f"`{day_label} {dt.hour:02d}시` {emoji} *{t}°C*  💧{prob}%  💨{wind}m/s")
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
        emoji = WEATHER_EMOJIS.get(cat, "🌡️")
        t_max = daily["temperature_2m_max"][i]
        t_min = daily["temperature_2m_min"][i]
        prob = daily["precipitation_probability_max"][i]

        date_str = f"{dt.month}/{dt.day}({day_name})"
        lines.append(f"`{date_str}` {emoji} {desc}  ⬇️*{t_min}°C* ⬆️*{t_max}°C*  💧{prob}%")

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
                    {"type": "mrkdwn", "text": "🏠 오늘은 실내 활동을 추천합니다."},
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
                {"type": "mrkdwn", "text": f"🏃 *최적 외출 시간:* {period} {display_hour}시경 (체감 {feels}°C)"},
            ],
        },
    ]


def build_fallback_text(data):
    cur = data["current"]
    weather_code = cur["weather_code"]
    description, _ = WMO_DESCRIPTIONS.get(weather_code, ("알 수 없음", "Clear"))
    temp = cur["temperature_2m"]
    return f"{CITY_NAME} 오늘의 날씨: {description}, {temp}°C"


def _get_channels():
    """설정된 모든 채널 리스트 반환"""
    channels = CONFIG.get("slack_channels")
    if channels:
        return channels
    return [SLACK_CHANNEL]


SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

# 날씨별 봇 아이콘 + 이름
BOT_IDENTITIES = {
    "Clear": (":sunny:", "날씨요정 ☀️"),
    "Clouds": (":cloud:", "날씨요정 ☁️"),
    "Rain": (":rain_cloud:", "날씨요정 🌧️"),
    "Drizzle": (":partly_sunny_rain:", "날씨요정 🌦️"),
    "Thunderstorm": (":thunder_cloud_and_rain:", "날씨요정 ⛈️"),
    "Snow": (":snowflake:", "날씨요정 ❄️"),
    "Fog": (":fog:", "날씨요정 🌫️"),
}

WEATHER_QUOTES = {
    "Clear": [
        "☀️ 맑은 하늘 아래, 모든 것이 가능합니다.",
        "☀️ 햇살이 좋은 날, 기분도 화창하게!",
        "☀️ 오늘의 맑은 날씨처럼, 마음도 맑게.",
    ],
    "Clouds": [
        "☁️ 구름 뒤에는 항상 태양이 있습니다.",
        "☁️ 흐린 날도 나름의 아름다움이 있죠.",
    ],
    "Rain": [
        "🌧️ 비 온 뒤에 땅이 굳는다. — 한국 속담",
        "🌧️ 빗소리를 BGM 삼아 집중해보세요.",
        "🌧️ 비가 와야 무지개도 뜨는 법이죠.",
    ],
    "Snow": [
        "❄️ 첫눈처럼 설레는 하루가 되길.",
        "❄️ 눈이 오면 세상이 잠시 조용해지죠.",
    ],
    "Thunderstorm": [
        "⛈️ 폭풍우 속에서도 빛은 찾아옵니다.",
    ],
    "Fog": [
        "🌫️ 안개 속에서도 길은 있습니다.",
    ],
}


def get_bot_identity(main_weather: str) -> tuple[str, str]:
    """날씨에 따른 봇 아이콘 이모지와 이름"""
    return BOT_IDENTITIES.get(main_weather, (":partly_sunny:", "날씨요정"))


def get_weather_quote(main_weather: str) -> str:
    """날씨에 맞는 명언/한줄"""
    quotes = WEATHER_QUOTES.get(main_weather, WEATHER_QUOTES["Clear"])
    day_seed = now_local().timetuple().tm_yday
    return quotes[day_seed % len(quotes)]


def send_to_slack(blocks, fallback_text, chart_path=None, color=None, weather_cat=None):
    # Webhook 모드 (봇 토큰 불필요, 간단 설정)
    if SLACK_WEBHOOK_URL:
        payload = {"text": fallback_text}
        if color:
            payload["attachments"] = [{"color": color, "blocks": blocks}]
        else:
            payload["blocks"] = blocks
        requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        return

    # Bot Token 모드 (전체 기능)
    client = WebClient(token=SLACK_BOT_TOKEN)
    icon_emoji, bot_name = get_bot_identity(weather_cat) if weather_cat else (None, None)
    for channel in _get_channels():
        kwargs = {
            "channel": channel,
            "text": fallback_text,
        }
        if icon_emoji:
            kwargs["icon_emoji"] = icon_emoji
            kwargs["username"] = bot_name
        if color:
            kwargs["attachments"] = [{"color": color, "blocks": blocks}]
        else:
            kwargs["blocks"] = blocks

        resp = client.chat_postMessage(**kwargs)
        if chart_path:
            try:
                client.files_upload_v2(
                    channel=channel,
                    file=chart_path,
                    title=f"{CITY_NAME} {TREND_DAYS}-Day Trend",
                    initial_comment="📈 Temperature Trend",
                    thread_ts=resp["ts"],
                )
            except SlackApiError:
                pass


def _build_health_block(risks):
    if not risks:
        return []
    return [
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*🏥 건강 주의보*\n" + "\n".join(f"• {r}" for r in risks),
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
                "text": "*🔮 내일 날씨 변화*\n" + "\n".join(f"• {a}" for a in alerts),
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
                emoji = WEATHER_EMOJIS.get(cat, "🌡️")
                temp = cur["temperature_2m"]
                hum = cur["relative_humidity_2m"]
                wind = kmh_to_ms(cur["wind_speed_10m"])
                results.append(f"{emoji} *{city['name']}* {temp}°C · {desc} · 습도 {hum}% · 바람 {wind}m/s")
            except Exception:
                results.append(f"❌ *{city['name']}* 데이터 조회 실패")

    if not results:
        return []

    return [
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*🌏 다른 도시 날씨*\n" + "\n".join(results),
            },
        },
    ]


def send_error_to_slack(error_msg):
    """실패 시 에러 메시지를 Slack으로 전송"""
    try:
        client = WebClient(token=SLACK_BOT_TOKEN)
        client.chat_postMessage(
            channel=SLACK_CHANNEL,
            text=f"⚠️ 날씨 봇 오류: {error_msg}",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🚨 *{CITY_NAME} 날씨 봇 오류*\n```{error_msg}```",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"🕐 {now_local().strftime('%Y-%m-%d %H:%M')} | <https://github.com/concrete-sangminlee/weather-slack-bot/actions|GitHub Actions 확인>"},
                    ],
                },
            ],
        )
    except Exception:
        pass  # 에러 알림 자체가 실패하면 무시


def main():
    start_time = time.time()
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

        if not validate_weather_data(data):
            raise ValueError("날씨 데이터 검증 실패")

        blocks, color, weather_cat = build_blocks(data, air_data)
        fallback_text = build_fallback_text(data)

        # 차트 생성 (실패해도 메시지는 전송)
        chart_path = None
        try:
            from chart import generate_chart
            chart_path = generate_chart()
        except Exception:
            pass

        send_to_slack(blocks, fallback_text, chart_path, color, weather_cat)

        # 임시 차트 파일 정리
        if chart_path:
            try:
                os.unlink(chart_path)
            except OSError:
                pass

        elapsed = round(time.time() - start_time, 2)
        print(f"날씨 메시지 전송 완료! ({elapsed}s)")
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
