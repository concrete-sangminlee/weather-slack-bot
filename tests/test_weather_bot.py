"""weather_bot 핵심 로직 유닛 테스트"""
import os
import sys

# 테스트 시 환경 변수 설정
os.environ.setdefault("SLACK_BOT_TOKEN", "test")
os.environ.setdefault("SLACK_CHANNEL", "test")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import weather_bot as wb


# ── 유틸리티 함수 ──

def test_kmh_to_ms():
    assert wb.kmh_to_ms(36) == 10.0
    assert wb.kmh_to_ms(0) == 0.0
    assert wb.kmh_to_ms(3.6) == 1.0


def test_wind_direction_to_text():
    assert wb.wind_direction_to_text(0) == "북"
    assert wb.wind_direction_to_text(90) == "동"
    assert wb.wind_direction_to_text(180) == "남"
    assert wb.wind_direction_to_text(270) == "서"
    assert wb.wind_direction_to_text(360) == "북"


def test_uv_index_level():
    assert "낮음" in wb.uv_index_level(1)
    assert "보통" in wb.uv_index_level(4)
    assert "높음" in wb.uv_index_level(7)
    assert "매우 높음" in wb.uv_index_level(9)
    assert "위험" in wb.uv_index_level(12)


def test_format_visibility():
    assert "매우 좋음" in wb.format_visibility(20000)
    assert "좋음" in wb.format_visibility(7000)
    assert "보통" in wb.format_visibility(3000)
    assert "나쁨" in wb.format_visibility(500)


def test_format_duration():
    assert wb.format_duration(3600) == "1시간 0분"
    assert wb.format_duration(5400) == "1시간 30분"
    assert wb.format_duration(0) == "0시간 0분"


# ── AQI / PM ──

def test_aqi_level():
    assert "좋음" in wb.aqi_level(30)
    assert "보통" in wb.aqi_level(80)
    assert "나쁨" in wb.aqi_level(180)


def test_pm_level():
    assert wb.pm_level(10) == "좋음"
    assert wb.pm_level(25) == "보통"
    assert wb.pm_level(50) == "나쁨"
    assert wb.pm_level(100) == "매우 나쁨"


# ── 생활지수 ──

def test_lifestyle_index_perfect():
    score = wb.calc_lifestyle_index(20, 50, 2, 3, 30, 0)
    assert score >= 75


def test_lifestyle_index_bad():
    score = wb.calc_lifestyle_index(-5, 20, 15, 10, 200, 90)
    assert score <= 30


def test_lifestyle_label():
    assert "최고" in wb.lifestyle_label(95)
    assert "매우 나쁨" in wb.lifestyle_label(20)


# ── 옷차림 추천 ──

def test_outfit_cold():
    outfit = wb.get_outfit_recommendation(-15, -20, "Clear", 0)
    assert "패딩" in outfit


def test_outfit_hot():
    outfit = wb.get_outfit_recommendation(33, 35, "Clear", 0)
    assert "민소매" in outfit or "반바지" in outfit


def test_outfit_rain():
    outfit = wb.get_outfit_recommendation(20, 18, "Rain", 80)
    assert "우산" in outfit


# ── 팁 생성 ──

def test_tips_rain():
    tips = wb.generate_tips("Rain", 15, 14, 18, 12, 70, 3, 3, 5, 80, 15, 90, 0)
    tip_text = " ".join(tips)
    assert "우산" in tip_text


def test_tips_cold():
    tips = wb.generate_tips("Clear", -12, -18, -8, -15, 30, 1, 3, 5, 0, 0, 10, 0)
    tip_text = " ".join(tips)
    assert "추위" in tip_text or "동파" in tip_text


def test_tips_pleasant():
    tips = wb.generate_tips("Clear", 22, 21, 24, 18, 50, 2, 2, 3, 0, 0, 20, 0)
    tip_text = " ".join(tips)
    assert "좋은 하루" in tip_text or "산책" in tip_text or "완벽" in tip_text


# ── 건강 위험 ──

def test_health_flu_risk():
    risks = wb.get_health_risks(3, 25, 5, 2, 10)
    assert any("감기" in r for r in risks)


def test_health_heat_risk():
    risks = wb.get_health_risks(35, 75, 2, 9, 10)
    assert any("열사병" in r for r in risks)


def test_health_no_risk():
    risks = wb.get_health_risks(20, 50, 3, 3, 10)
    assert len(risks) == 0


# ── 활동 추천 ──

def test_activity_rain():
    act = wb.get_activity_suggestions(20, 19, "Rain", 3, 80, 2)
    assert "실내" in act


def test_activity_perfect():
    act = wb.get_activity_suggestions(22, 21, "Clear", 3, 0, 4)
    assert "자전거" in act or "산책" in act or "피크닉" in act


# ── 한국형 생활지수 ──

def test_discomfort_index():
    di = wb.calc_discomfort_index(30, 80)
    assert di > 75
    assert "불쾌" in wb.discomfort_label(di)


def test_discomfort_comfortable():
    di = wb.calc_discomfort_index(20, 50)
    assert "쾌적" in wb.discomfort_label(di)


def test_laundry_index_good():
    score = wb.calc_laundry_index(25, 40, 5, 0)
    assert score >= 60


def test_laundry_index_bad():
    score = wb.calc_laundry_index(5, 90, 1, 80)
    assert score <= 30


def test_car_wash_good():
    score = wb.calc_car_wash_index(0, 0, 10)
    assert score >= 80


def test_car_wash_bad():
    score = wb.calc_car_wash_index(80, 70, 80)
    assert score <= 30


def test_food_safety_safe():
    result = wb.calc_food_safety_index(15, 50)
    assert "안전" in result


def test_food_safety_danger():
    result = wb.calc_food_safety_index(36, 85)
    assert "위험" in result


# ── 인사말 ──

def test_get_greeting():
    greeting = wb.get_greeting()
    assert isinstance(greeting, str)
    assert len(greeting) > 0


# ── 멀티시티 ──

def test_fetch_city_weather():
    city = {"name": "부산", "latitude": 35.1796, "longitude": 129.0756}
    data = wb.fetch_city_weather(city)
    assert "current" in data
    assert "temperature_2m" in data["current"]


def test_city_comparison_empty():
    blocks = wb._build_city_comparison_blocks([])
    assert blocks == []


def test_city_comparison_with_cities():
    cities = [{"name": "부산", "latitude": 35.1796, "longitude": 129.0756}]
    blocks = wb._build_city_comparison_blocks(cities)
    assert len(blocks) >= 1
    # 부산이 결과에 포함되어야 함
    found = False
    for b in blocks:
        text = b.get("text", {}).get("text", "")
        if "부산" in text:
            found = True
    assert found


# ── 일출/일몰/달 ──

def test_daylight_progress_daytime():
    # 오늘 일출 06:00, 일몰 19:00 가정
    from datetime import datetime
    bar, pct = wb.calc_daylight_progress(
        datetime.now().replace(hour=6, minute=0).isoformat(),
        datetime.now().replace(hour=19, minute=0).isoformat(),
    )
    assert isinstance(bar, str)
    assert 0 <= pct <= 100


def test_moon_phase():
    phase = wb.get_moon_phase()
    assert isinstance(phase, str)
    assert "달" in phase or "삭" in phase or "보름" in phase


# ── API 통합 테스트 ──

def test_fetch_weather():
    data = wb.fetch_weather()
    assert "current" in data
    assert "daily" in data
    assert "hourly" in data


def test_fetch_air_quality():
    data = wb.fetch_air_quality()
    assert "current" in data
    assert "pm2_5" in data["current"]


def test_build_blocks():
    data = wb.fetch_weather()
    air = wb.fetch_air_quality()
    blocks = wb.build_blocks(data, air)
    assert isinstance(blocks, list)
    assert len(blocks) > 20
    # 헤더가 있는지 확인
    assert blocks[0]["type"] == "header"


def test_build_fallback_text():
    data = wb.fetch_weather()
    text = wb.build_fallback_text(data)
    assert "°C" in text
    assert wb.CITY_NAME in text
