"""End-to-end 파이프라인 테스트 — 전체 흐름 검증"""
import os

os.environ.setdefault("SLACK_BOT_TOKEN", "test")
os.environ.setdefault("SLACK_CHANNEL", "test")

from conftest import requires_api


@requires_api
def test_full_daily_pipeline():
    """일일 브리핑 전체 파이프라인 (Slack 전송 제외)"""
    from weather_bot import (
        build_blocks,
        build_fallback_text,
        fetch_air_quality,
        fetch_weather,
        validate_weather_data,
    )

    data = fetch_weather()
    assert validate_weather_data(data)

    try:
        air = fetch_air_quality()
    except Exception:
        air = None

    blocks, color, cat = build_blocks(data, air)

    assert len(blocks) >= 20
    assert len(blocks) <= 50  # Slack 블록 제한
    assert color.startswith("#")
    assert cat in ("Clear", "Clouds", "Rain", "Drizzle", "Thunderstorm", "Snow", "Fog")

    fallback = build_fallback_text(data)
    assert len(fallback) > 10
    assert "°C" in fallback

    # 블록 구조 검증
    block_types = [b["type"] for b in blocks]
    assert "header" in block_types
    assert "section" in block_types
    assert "divider" in block_types
    assert "context" in block_types


@requires_api
def test_full_digest_pipeline():
    """다이제스트 파이프라인"""
    from weather_bot import (
        PAST_DAYS,
        WMO_DESCRIPTIONS,
        calc_lifestyle_index,
        fetch_weather,
        get_outfit_recommendation,
        kmh_to_ms,
        weather_grade,
    )

    data = fetch_weather()
    cur = data["current"]
    daily = data["daily"]
    idx = PAST_DAYS

    temp = cur["temperature_2m"]
    feels = cur["apparent_temperature"]
    hum = cur["relative_humidity_2m"]
    wind = kmh_to_ms(cur["wind_speed_10m"])
    code = cur["weather_code"]
    desc, cat = WMO_DESCRIPTIONS.get(code, ("?", "Clear"))
    prob = daily["precipitation_probability_max"][idx]

    score = calc_lifestyle_index(temp, hum, wind, None, None, prob)
    grade, color = weather_grade(score)
    outfit = get_outfit_recommendation(temp, feels, cat, prob)

    assert isinstance(grade, str)
    assert len(grade) <= 2
    assert color.startswith("#")
    assert len(outfit) > 5


@requires_api
def test_weekly_summary_pipeline():
    """주간 요약 파이프라인"""
    from weekly_summary import build_weekly_summary

    blocks = build_weekly_summary()
    assert isinstance(blocks, list)
    assert len(blocks) >= 5
    assert blocks[0]["type"] == "header"


@requires_api
def test_alert_pipeline():
    """긴급 알림 파이프라인"""
    from alert import check_alerts

    alerts = check_alerts()
    assert isinstance(alerts, list)
    # 각 알림은 (emoji, title, desc) 튜플
    for a in alerts:
        assert len(a) == 3


@requires_api
def test_chart_pipeline():
    """차트 생성 파이프라인"""
    from chart import generate_chart

    path = generate_chart()
    assert path.endswith(".png")
    assert os.path.exists(path)
    assert os.path.getsize(path) > 1000  # 최소 1KB
    os.unlink(path)


@requires_api
def test_history_pipeline():
    """히스토리 파이프라인"""
    from history import get_stats, load_history, log_today

    record = log_today()
    assert len(record) >= 20  # 최소 20개 필드

    history = load_history()
    assert len(history) >= 1

    stats = get_stats(1)
    assert "avg_temp" in stats
    assert "rainy_days" in stats


@requires_api
def test_badge_pipeline():
    """배지 생성 파이프라인"""
    from badge import generate_badge

    path = generate_badge()
    assert path.endswith(".svg")
    assert os.path.exists(path)

    content = open(path, encoding="utf-8").read()
    assert "<svg" in content
    assert "°C" in content


def test_config_integrity():
    """설정 무결성 검증"""
    from config_loader import (
        CITY_LAT,
        CITY_LON,
        CITY_NAME,
        CONFIG,
        DAILY_DAYS,
        DISPLAY,
        PAST_DAYS,
        TIMEZONE,
        TREND_DAYS,
        L,
        validate_config,
    )

    errors = validate_config()
    assert len(errors) == 0

    assert isinstance(CITY_NAME, str) and len(CITY_NAME) > 0
    assert -90 <= CITY_LAT <= 90
    assert -180 <= CITY_LON <= 180
    assert isinstance(TIMEZONE, str)
    assert 1 <= DAILY_DAYS <= 16
    assert 0 <= PAST_DAYS <= 7
    assert 1 <= TREND_DAYS <= 16
    assert isinstance(DISPLAY, dict)
    assert isinstance(L, dict)
    assert "greeting" in L
    assert "sections" in L
    assert isinstance(CONFIG, dict)


def test_all_modules_importable():
    """모든 모듈이 import 가능한지 확인"""
    import alert
    import badge
    import chart
    import cli
    import config_loader
    import history
    import weather_bot
    import weekly_summary

    assert hasattr(weather_bot, "__version__")
    assert hasattr(cli, "main")
    assert hasattr(alert, "check_alerts")
    assert hasattr(chart, "generate_chart")
    assert hasattr(history, "log_today")
    assert hasattr(badge, "generate_badge")
    assert hasattr(weekly_summary, "build_weekly_summary")
    assert hasattr(config_loader, "validate_config")
