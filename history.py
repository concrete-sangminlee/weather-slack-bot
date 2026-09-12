"""날씨 히스토리 로깅 — 매일 데이터를 JSON에 저장하여 트렌드 추적"""
import json
from pathlib import Path

from config_loader import PAST_DAYS
from weather_bot import (
    CITY_NAME,
    extract_conditions,
    fetch_weather,
    now_local,
    try_fetch_air_quality,
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
    air_data = try_fetch_air_quality()
    cond = extract_conditions(fetch_weather(), air_data)

    record = {
        "date": now_local().strftime("%Y-%m-%d"),
        "time": cond.time,
        "city": CITY_NAME,
        "weather": cond.weather,
        "category": cond.category,
        "temp": cond.temp,
        "feels_like": cond.feels_like,
        "temp_max": cond.temp_max,
        "temp_min": cond.temp_min,
        "humidity": cond.humidity,
        "wind_speed": cond.wind_speed,
        "wind_gust": cond.wind_gust,
        "precip_prob": cond.precip_prob,
        "precip_sum": cond.precip_sum,
        "cloud_cover": cond.cloud_cover,
        "pressure": cond.pressure,
        "visibility": cond.visibility,
        "uv_max": cond.uv_max,
        "sunrise": cond.sunrise,
        "sunset": cond.sunset,
        "aqi": cond.aqi,
        "pm25": cond.pm25,
        "discomfort_index": cond.discomfort_index,
        "lifestyle_score": cond.lifestyle_score,
        "grade": cond.grade,
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


def check_forecast_accuracy():
    """어제 예보와 오늘 실제 날씨 비교"""
    history = load_history()
    if len(history) < 2:
        return None

    today = history[-1]

    # 어제 예보했던 오늘 최고/최저와 실제 비교
    # (history에는 당일 관측값만 있으므로, 오늘의 API에서 어제 예보를 역추적)
    data = fetch_weather()
    daily = data["daily"]

    # past_days=1이므로 index 0 = 어제 실제, index 1 = 오늘 실제
    idx = PAST_DAYS
    if idx >= len(daily["temperature_2m_max"]):
        return None
    actual_max = daily["temperature_2m_max"][idx]
    actual_min = daily["temperature_2m_min"][idx]

    # 히스토리에 저장된 오늘의 예보값 (아침에 기록된 값)
    forecast_max = today.get("temp_max")
    forecast_min = today.get("temp_min")

    if forecast_max is None or actual_max is None:
        return None

    max_error = abs(actual_max - forecast_max)
    min_error = abs(actual_min - forecast_min)
    avg_error = (max_error + min_error) / 2

    return {
        "date": today["date"],
        "forecast_max": forecast_max,
        "actual_max": actual_max,
        "max_error": round(max_error, 1),
        "forecast_min": forecast_min,
        "actual_min": actual_min,
        "min_error": round(min_error, 1),
        "avg_error": round(avg_error, 1),
        "grade": "A" if avg_error < 1 else "B" if avg_error < 2 else "C" if avg_error < 3 else "D",
    }


def get_trends(days: int = 7) -> dict:
    """기온 트렌드 분석"""
    history = load_history()
    recent = history[-days:]
    if len(recent) < 3:
        return {}

    temps = [r["temp"] for r in recent]

    # 기온 추세 (상승/하락/유지)
    first_half = sum(temps[:len(temps) // 2]) / max(len(temps) // 2, 1)
    second_half = sum(temps[len(temps) // 2:]) / max(len(temps) - len(temps) // 2, 1)
    diff = second_half - first_half

    if diff > 2:
        trend = "📈 상승세"
    elif diff < -2:
        trend = "📉 하락세"
    else:
        trend = "➡️ 유지"

    # 최고/최저 날
    best_day = max(recent, key=lambda r: r["lifestyle_score"])
    worst_day = min(recent, key=lambda r: r["lifestyle_score"])
    hottest = max(recent, key=lambda r: r["temp_max"])
    coldest = min(recent, key=lambda r: r["temp_min"])

    return {
        "trend": trend,
        "trend_diff": round(diff, 1),
        "best_day": f"{best_day['date']} (등급 {best_day['grade']}, {best_day['lifestyle_score']}점)",
        "worst_day": f"{worst_day['date']} (등급 {worst_day['grade']}, {worst_day['lifestyle_score']}점)",
        "hottest": f"{hottest['date']} ({hottest['temp_max']}°C)",
        "coldest": f"{coldest['date']} ({coldest['temp_min']}°C)",
    }


def main():
    record = log_today()
    print(f"📝 {record['date']} — {record['weather']} {record['temp']}°C (등급 {record['grade']})")

    stats = get_stats(7)
    if stats:
        print(f"📊 최근 {stats['days']}일: 평균 {stats['avg_temp']}°C, 최고 {stats['highest']}°C, 최저 {stats['lowest']}°C")

    trends = get_trends()
    if trends:
        print(f"📈 기온 추세: {trends['trend']} ({trends['trend_diff']:+.1f}°C)")
        print(f"   최고의 날: {trends['best_day']}")
        print(f"   최악의 날: {trends['worst_day']}")


if __name__ == "__main__":
    main()
