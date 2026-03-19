"""날씨 히스토리 로깅 — 매일 데이터를 JSON에 저장하여 트렌드 추적"""
import json
from datetime import datetime
from pathlib import Path

from weather_bot import (
    CITY_NAME,
    PAST_DAYS,
    WMO_DESCRIPTIONS,
    calc_discomfort_index,
    calc_lifestyle_index,
    fetch_air_quality,
    fetch_weather,
    format_time,
    kmh_to_ms,
    weather_grade,
)

HISTORY_PATH = Path(__file__).parent / "weather_history.json"
MAX_DAYS = 90  # 최대 90일 보관


def load_history() -> list:
    if HISTORY_PATH.exists():
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    return []


def save_history(records: list):
    # 최대 기록 수 제한
    records = records[-MAX_DAYS:]
    HISTORY_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def log_today():
    """오늘의 날씨 데이터를 히스토리에 추가"""
    data = fetch_weather()
    cur = data["current"]
    daily = data["daily"]
    idx = PAST_DAYS

    code = cur["weather_code"]
    desc, cat = WMO_DESCRIPTIONS.get(code, ("?", "Clear"))

    aqi = pm25 = None
    try:
        air = fetch_air_quality()
        aqi = air["current"].get("us_aqi")
        pm25 = air["current"].get("pm2_5")
    except Exception:
        pass

    temp = cur["temperature_2m"]
    hum = cur["relative_humidity_2m"]
    wind = kmh_to_ms(cur["wind_speed_10m"])
    prob = daily["precipitation_probability_max"][idx]
    score = calc_lifestyle_index(temp, hum, wind, None, aqi, prob)
    grade, _ = weather_grade(score)

    record = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": cur["time"],
        "city": CITY_NAME,
        "weather": desc,
        "category": cat,
        "temp": temp,
        "feels_like": cur["apparent_temperature"],
        "temp_max": daily["temperature_2m_max"][idx],
        "temp_min": daily["temperature_2m_min"][idx],
        "humidity": hum,
        "wind_speed": wind,
        "wind_gust": kmh_to_ms(cur["wind_gusts_10m"]),
        "precip_prob": prob,
        "precip_sum": daily["precipitation_sum"][idx],
        "cloud_cover": cur["cloud_cover"],
        "pressure": cur["pressure_msl"],
        "visibility": cur.get("visibility", 0),
        "uv_max": daily["uv_index_max"][idx],
        "sunrise": format_time(daily["sunrise"][idx]),
        "sunset": format_time(daily["sunset"][idx]),
        "aqi": aqi,
        "pm25": pm25,
        "discomfort_index": calc_discomfort_index(temp, hum),
        "lifestyle_score": score,
        "grade": grade,
    }

    history = load_history()

    # 같은 날짜 이미 있으면 업데이트
    history = [r for r in history if r["date"] != record["date"]]
    history.append(record)
    history.sort(key=lambda r: r["date"])

    save_history(history)
    return record


def get_stats(days: int = 7) -> dict:
    """최근 N일 통계"""
    history = load_history()
    recent = history[-days:]
    if not recent:
        return {}

    temps = [r["temp"] for r in recent]
    maxs = [r["temp_max"] for r in recent]
    mins = [r["temp_min"] for r in recent]
    scores = [r["lifestyle_score"] for r in recent]

    return {
        "days": len(recent),
        "avg_temp": round(sum(temps) / len(temps), 1),
        "avg_max": round(sum(maxs) / len(maxs), 1),
        "avg_min": round(sum(mins) / len(mins), 1),
        "highest": max(maxs),
        "lowest": min(mins),
        "avg_score": round(sum(scores) / len(scores)),
        "rainy_days": sum(1 for r in recent if r["precip_sum"] > 0.5),
    }


def main():
    record = log_today()
    print(f"📝 {record['date']} — {record['weather']} {record['temp']}°C (등급 {record['grade']})")

    stats = get_stats(7)
    if stats:
        print(f"📊 최근 {stats['days']}일: 평균 {stats['avg_temp']}°C, 최고 {stats['highest']}°C, 최저 {stats['lowest']}°C")


if __name__ == "__main__":
    main()
