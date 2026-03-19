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


# ── 골든아워 ──

def test_golden_hour():
    from datetime import datetime
    result = wb.calc_golden_hour(
        datetime.now().replace(hour=6, minute=30).isoformat(),
        datetime.now().replace(hour=18, minute=42).isoformat(),
    )
    assert "📷" in result
    assert "06:30" in result
    assert "18:42" in result


# ── 멀티채널 ──

def test_get_channels_default():
    channels = wb._get_channels()
    assert isinstance(channels, list)
    assert len(channels) >= 1


# ── alert.py ──

def test_alert_check():
    import alert
    alerts = alert.check_alerts()
    assert isinstance(alerts, list)


# ── weekly_summary.py ──

def test_weekly_summary():
    import weekly_summary as ws
    blocks = ws.build_weekly_summary()
    assert isinstance(blocks, list)
    assert blocks[0]["type"] == "header"


# ── chart.py ──

def test_chart_generation():
    import chart
    path = chart.generate_chart()
    assert path.endswith(".png")
    import os
    assert os.path.exists(path)
    os.unlink(path)


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
    blocks, color, weather_cat = wb.build_blocks(data, air)
    assert isinstance(blocks, list)
    assert len(blocks) > 20
    assert blocks[0]["type"] == "header"
    assert color.startswith("#")
    assert weather_cat in wb.WEATHER_EMOJIS or weather_cat == "Clear"


def test_weather_grade():
    grade, color = wb.weather_grade(95)
    assert grade == "A+"
    assert color == "#2ecc71"
    grade, color = wb.weather_grade(35)
    assert grade == "D"


def test_seasonal_note():
    note = wb.get_seasonal_note()
    # 어떤 날이든 None이거나 문자열
    assert note is None or isinstance(note, str)


def test_wind_chill():
    assert wb.calc_wind_chill(5, 10) < 5  # 풍속냉각으로 체감 더 낮음
    assert wb.calc_wind_chill(20, 5) == 20  # 10°C 이상이면 적용 안 됨


def test_heat_index():
    assert wb.calc_heat_index(35, 70) > 35  # 열지수로 체감 더 높음
    assert wb.calc_heat_index(20, 50) == 20  # 27°C 미만이면 적용 안 됨


def test_comfort_timeline():
    data = wb.fetch_weather()
    tl = wb.build_comfort_timeline(data)
    assert isinstance(tl, str)


def test_cli_version():
    import cli
    cli.cmd_version()


def test_cli_stats():
    import cli
    cli.cmd_stats()


def test_config_validation():
    from config_loader import validate_config
    errors = validate_config()
    assert isinstance(errors, list)
    assert len(errors) == 0  # 기본 config는 오류 없어야 함


def test_forecast_accuracy():
    from history import check_forecast_accuracy
    result = check_forecast_accuracy()
    # 1일만 기록되어 있으면 None
    assert result is None or isinstance(result, dict)


def test_trends():
    from history import get_trends
    trends = get_trends()
    # 3일 미만이면 빈 dict
    assert isinstance(trends, dict)


def test_bot_identity():
    icon, name = wb.get_bot_identity("Clear")
    assert ":sunny:" in icon
    assert "날씨요정" in name


def test_weather_quote():
    quote = wb.get_weather_quote("Rain")
    assert isinstance(quote, str)
    assert len(quote) > 5


def test_history_log():
    import history
    record = history.log_today()
    assert record["city"] == wb.CITY_NAME
    assert "temp" in record
    assert "grade" in record

    stats = history.get_stats(1)
    assert stats["days"] == 1


# ── 극한 날씨 조건 테스트 ──

def test_tips_heatwave():
    tips = wb.generate_tips("Clear", 36, 38, 37, 30, 75, 10, 3, 5, 10, 0, 20, 0)
    tip_text = " ".join(tips)
    assert "폭염" in tip_text or "극심" in tip_text


def test_tips_snow():
    tips = wb.generate_tips("Snow", -2, -5, 0, -5, 60, 1, 3, 5, 80, 5, 90, 8)
    tip_text = " ".join(tips)
    assert "폭설" in tip_text or "눈" in tip_text


def test_tips_thunderstorm():
    tips = wb.generate_tips("Thunderstorm", 20, 19, 22, 18, 80, 3, 3, 5, 90, 20, 95, 0)
    tip_text = " ".join(tips)
    assert "뇌우" in tip_text


def test_tips_fog():
    tips = wb.generate_tips("Fog", 10, 9, 12, 8, 95, 1, 2, 3, 0, 0, 100, 0)
    tip_text = " ".join(tips)
    assert "안개" in tip_text


def test_tips_dry():
    tips = wb.generate_tips("Clear", 15, 14, 18, 10, 15, 5, 3, 5, 0, 0, 20, 0)
    tip_text = " ".join(tips)
    assert "건조" in tip_text


def test_tips_high_humidity():
    tips = wb.generate_tips("Clouds", 25, 26, 28, 22, 92, 5, 3, 5, 0, 0, 80, 0)
    tip_text = " ".join(tips)
    assert "습도" in tip_text


def test_tips_strong_wind():
    tips = wb.generate_tips("Clear", 15, 10, 18, 12, 50, 5, 15, 22, 0, 0, 20, 0)
    tip_text = " ".join(tips)
    assert "강풍" in tip_text or "돌풍" in tip_text


def test_tips_uv_extreme():
    tips = wb.generate_tips("Clear", 30, 32, 33, 27, 40, 12, 3, 5, 0, 0, 10, 0, None, None)
    tip_text = " ".join(tips)
    assert "자외선" in tip_text


def test_tips_bad_air():
    tips = wb.generate_tips("Clear", 20, 19, 22, 18, 50, 5, 3, 5, 0, 0, 20, 0, 180, 80)
    tip_text = " ".join(tips)
    assert "미세먼지" in tip_text or "마스크" in tip_text


def test_outfit_mild():
    outfit = wb.get_outfit_recommendation(18, 17, "Clear", 0)
    assert "셔츠" in outfit or "긴팔" in outfit


def test_outfit_snow():
    outfit = wb.get_outfit_recommendation(-2, -5, "Snow", 70)
    assert "방수" in outfit or "우산" in outfit


def test_activity_cold():
    act = wb.get_activity_suggestions(-5, -10, "Clear", 5, 0, 1)
    assert "카페" in act or "실내" in act


def test_activity_hot():
    act = wb.get_activity_suggestions(33, 35, "Clear", 2, 0, 9)
    assert "수영" in act or "에어컨" in act


def test_health_no_risk_pleasant():
    risks = wb.get_health_risks(22, 50, 3, 4, 15)
    assert len(risks) == 0


def test_health_uv_burn():
    risks = wb.get_health_risks(28, 50, 3, 9, 10)
    assert any("피부" in r or "자외선" in r for r in risks)


def test_health_frostbite():
    risks = wb.get_health_risks(-12, 30, 8, 1, 10)
    assert any("동상" in r for r in risks)


def test_discomfort_hot_humid():
    di = wb.calc_discomfort_index(32, 85)
    assert "불쾌" in wb.discomfort_label(di)


def test_laundry_rainy():
    score = wb.calc_laundry_index(10, 85, 1, 90)
    assert score <= 25
    assert "나쁨" in wb.laundry_label(score) or "매우" in wb.laundry_label(score)


def test_food_safety_warning():
    result = wb.calc_food_safety_index(31, 72)
    assert "경고" in result


def test_seasonal_march():
    # 3월 19일이면 봄 메시지
    note = wb.get_seasonal_note()
    assert note is None or isinstance(note, str)


def test_weather_mood_rain():
    mood = wb.get_weather_mood("Rain", 15, 60)
    assert isinstance(mood, str)
    assert len(mood) > 5


def test_weather_mood_extreme_hot():
    mood = wb.get_weather_mood("Clear", 36, 20)
    assert isinstance(mood, str)


def test_weather_mood_extreme_cold():
    mood = wb.get_weather_mood("Clear", -8, 15)
    assert isinstance(mood, str)


def test_validate_weather_data():
    data = wb.fetch_weather()
    assert wb.validate_weather_data(data) is True


def test_validate_bad_data():
    assert wb.validate_weather_data({"current": {"temperature_2m": 999}}) is False


def test_build_fallback_text():
    data = wb.fetch_weather()
    text = wb.build_fallback_text(data)
    assert "°C" in text
    assert wb.CITY_NAME in text
