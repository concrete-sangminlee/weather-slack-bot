"""7일 기온 트렌드 차트 이미지 생성"""
import io
import tempfile
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from weather_bot import (
    _request_with_retry, CITY_LAT, CITY_LON, CITY_NAME,
    TIMEZONE, PAST_DAYS, TREND_DAYS,
)

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def fetch_chart_data():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": CITY_LAT,
        "longitude": CITY_LON,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
        "timezone": TIMEZONE,
        "past_days": PAST_DAYS,
        "forecast_days": TREND_DAYS,
    }
    return _request_with_retry(url, params)


def generate_chart():
    """7일 기온 차트 생성, 파일 경로 반환"""
    data = fetch_chart_data()
    daily = data["daily"]

    start = PAST_DAYS
    dates = []
    highs = []
    lows = []
    precip_probs = []
    labels = []

    for i in range(start, min(start + TREND_DAYS, len(daily["time"]))):
        dt = datetime.fromisoformat(daily["time"][i])
        dates.append(dt)
        highs.append(daily["temperature_2m_max"][i])
        lows.append(daily["temperature_2m_min"][i])
        precip_probs.append(daily["precipitation_probability_max"][i] or 0)
        labels.append(f"{dt.month}/{dt.day}\n({WEEKDAYS[dt.weekday()]})")

    # 스타일 설정
    plt.style.use("dark_background")
    fig, ax1 = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#0f172a")
    ax1.set_facecolor("#0f172a")

    x = range(len(dates))

    # 기온 범위 채우기
    ax1.fill_between(x, lows, highs, alpha=0.15, color="#3b82f6")

    # 최고/최저 기온 라인
    ax1.plot(x, highs, "o-", color="#f97316", linewidth=2.5, markersize=8, label="최고", zorder=5)
    ax1.plot(x, lows, "o-", color="#3b82f6", linewidth=2.5, markersize=8, label="최저", zorder=5)

    # 기온 값 라벨
    for i, (h, l) in enumerate(zip(highs, lows)):
        ax1.annotate(f"{h:.0f}°", (i, h), textcoords="offset points",
                     xytext=(0, 12), ha="center", fontsize=11, fontweight="bold", color="#f97316")
        ax1.annotate(f"{l:.0f}°", (i, l), textcoords="offset points",
                     xytext=(0, -16), ha="center", fontsize=11, fontweight="bold", color="#3b82f6")

    # 강수확률 바 (보조 축)
    ax2 = ax1.twinx()
    bars = ax2.bar(x, precip_probs, alpha=0.25, color="#06b6d4", width=0.4, label="강수확률")
    ax2.set_ylim(0, 120)
    ax2.set_ylabel("Precip %", color="#06b6d4", fontsize=11)
    ax2.tick_params(axis="y", labelcolor="#06b6d4")

    # 강수확률 라벨 (40% 이상만)
    for i, p in enumerate(precip_probs):
        if p >= 40:
            ax2.annotate(f"{p}%", (i, p), textcoords="offset points",
                         xytext=(0, 8), ha="center", fontsize=9, color="#06b6d4")

    # 축 설정
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=10)
    ax1.set_ylabel("Temp (°C)", fontsize=11)
    ax1.legend(["High", "Low"], loc="upper left", fontsize=10)
    ax1.grid(axis="y", alpha=0.15)
    ax1.set_title(f"{TREND_DAYS}-Day Temperature Trend", fontsize=16, fontweight="bold", pad=16)

    plt.tight_layout()

    # 임시 파일로 저장
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    fig.savefig(tmp.name, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return tmp.name


if __name__ == "__main__":
    path = generate_chart()
    print(f"Chart saved: {path}")
