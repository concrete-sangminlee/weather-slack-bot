"""Slack 전송 계층 · 네트워크 재시도 · 공용 추출 로직 유닛 테스트 (모두 mock 기반).

기존 test_weather_bot.py는 순수 함수 위주라 네트워크/Slack 경로가 비어 있었다.
여기서는 requests / slack_sdk를 모두 mock 하여 실제 네트워크 없이
전송 로직·재시도·타임존·골든아워·계절 메시지·토큰 검증을 검증한다.
"""
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("SLACK_BOT_TOKEN", "test")
os.environ.setdefault("SLACK_CHANNEL", "test")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config_loader  # noqa: E402
import weather_bot as wb  # noqa: E402

# ──────────────────────────────────────────────────────────────
# _request_with_retry — 재시도/백오프
# ──────────────────────────────────────────────────────────────

def test_request_with_retry_success_first_try():
    """첫 시도 성공 시 재시도 없이 JSON 반환."""
    resp = MagicMock()
    resp.json.return_value = {"ok": True}
    with patch.object(wb.requests, "get", return_value=resp) as mock_get, \
            patch.object(wb.time, "sleep") as mock_sleep:
        result = wb._request_with_retry("http://x", {})
    assert result == {"ok": True}
    assert mock_get.call_count == 1
    mock_sleep.assert_not_called()


def test_request_with_retry_retries_then_succeeds():
    """일시적 실패 후 재시도해서 성공하는 경로."""
    good = MagicMock()
    good.json.return_value = {"ok": True}
    err = wb.requests.RequestException("temporary")
    with patch.object(wb.requests, "get", side_effect=[err, good]) as mock_get, \
            patch.object(wb.time, "sleep") as mock_sleep:
        result = wb._request_with_retry("http://x", {})
    assert result == {"ok": True}
    assert mock_get.call_count == 2
    assert mock_sleep.call_count == 1  # 첫 실패 후 한 번 대기


def test_request_with_retry_exhausts_and_raises():
    """MAX_RETRIES 모두 실패하면 마지막 예외를 그대로 올린다."""
    err = wb.requests.RequestException("down")
    with patch.object(wb.requests, "get", side_effect=err) as mock_get, \
            patch.object(wb.time, "sleep"):
        with pytest.raises(wb.requests.RequestException):
            wb._request_with_retry("http://x", {})
    assert mock_get.call_count == wb.MAX_RETRIES


# ──────────────────────────────────────────────────────────────
# send_to_slack — Webhook 모드
# ──────────────────────────────────────────────────────────────

def test_send_to_slack_webhook_mode_with_color():
    blocks = [{"type": "section"}]
    with patch.object(wb, "SLACK_WEBHOOK_URL", "https://hooks.slack.test/x"), \
            patch.object(wb.requests, "post") as mock_post:
        wb.send_to_slack(blocks, "fallback", color="#fff")
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    payload = kwargs["json"]
    assert payload["text"] == "fallback"
    # color가 있으면 attachments로 감싼다
    assert payload["attachments"][0]["color"] == "#fff"
    assert payload["attachments"][0]["blocks"] == blocks


def test_send_to_slack_webhook_mode_without_color():
    blocks = [{"type": "section"}]
    with patch.object(wb, "SLACK_WEBHOOK_URL", "https://hooks.slack.test/x"), \
            patch.object(wb.requests, "post") as mock_post:
        wb.send_to_slack(blocks, "fallback")
    payload = mock_post.call_args.kwargs["json"]
    assert payload["blocks"] == blocks
    assert "attachments" not in payload


# ──────────────────────────────────────────────────────────────
# send_to_slack — Bot Token 모드
# ──────────────────────────────────────────────────────────────

def test_send_to_slack_bot_token_posts_to_all_channels():
    blocks = [{"type": "section"}]
    fake_client = MagicMock()
    fake_client.chat_postMessage.return_value = {"ts": "123.456"}
    with patch.object(wb, "SLACK_WEBHOOK_URL", None), \
            patch.object(wb, "WebClient", return_value=fake_client), \
            patch.object(wb, "_get_channels", return_value=["#a", "#b"]):
        wb.send_to_slack(blocks, "fallback", color="#000")
    assert fake_client.chat_postMessage.call_count == 2
    channels = {c.kwargs["channel"] for c in fake_client.chat_postMessage.call_args_list}
    assert channels == {"#a", "#b"}


def test_send_to_slack_bot_token_uploads_chart(tmp_path):
    chart = tmp_path / "chart.png"
    chart.write_bytes(b"fake-png")
    fake_client = MagicMock()
    fake_client.chat_postMessage.return_value = {"ts": "1.0"}
    with patch.object(wb, "SLACK_WEBHOOK_URL", None), \
            patch.object(wb, "WebClient", return_value=fake_client), \
            patch.object(wb, "_get_channels", return_value=["#a"]):
        wb.send_to_slack([{"type": "section"}], "fb", chart_path=str(chart))
    fake_client.files_upload_v2.assert_called_once()
    assert fake_client.files_upload_v2.call_args.kwargs["thread_ts"] == "1.0"


def test_send_to_slack_bot_token_applies_weather_identity():
    """weather_cat이 주어지면 icon_emoji/username을 채운다."""
    fake_client = MagicMock()
    fake_client.chat_postMessage.return_value = {"ts": "1.0"}
    with patch.object(wb, "SLACK_WEBHOOK_URL", None), \
            patch.object(wb, "WebClient", return_value=fake_client), \
            patch.object(wb, "_get_channels", return_value=["#a"]), \
            patch.object(wb, "get_bot_identity", return_value=(":sunny:", "맑음봇")):
        wb.send_to_slack([{"type": "section"}], "fb", weather_cat="Clear")
    kwargs = fake_client.chat_postMessage.call_args.kwargs
    assert kwargs["icon_emoji"] == ":sunny:"
    assert kwargs["username"] == "맑음봇"


def test_send_to_slack_chart_upload_failure_is_swallowed(tmp_path):
    """차트 업로드가 SlackApiError로 실패해도 메시지 전송은 성공으로 간주."""
    chart = tmp_path / "chart.png"
    chart.write_bytes(b"x")
    fake_client = MagicMock()
    fake_client.chat_postMessage.return_value = {"ts": "1.0"}
    fake_client.files_upload_v2.side_effect = wb.SlackApiError("nope", response={})
    with patch.object(wb, "SLACK_WEBHOOK_URL", None), \
            patch.object(wb, "WebClient", return_value=fake_client), \
            patch.object(wb, "_get_channels", return_value=["#a"]):
        wb.send_to_slack([{"type": "section"}], "fb", chart_path=str(chart))  # 예외 없이 통과


# ──────────────────────────────────────────────────────────────
# try_fetch_air_quality — 실패 시 None
# ──────────────────────────────────────────────────────────────

def test_try_fetch_air_quality_returns_data_on_success():
    with patch.object(wb, "fetch_air_quality", return_value={"current": {}}):
        assert wb.try_fetch_air_quality() == {"current": {}}


def test_try_fetch_air_quality_returns_none_on_error(capsys):
    with patch.object(wb, "fetch_air_quality",
                      side_effect=wb.requests.RequestException("boom")):
        assert wb.try_fetch_air_quality() is None
    assert "대기질" in capsys.readouterr().err


# ──────────────────────────────────────────────────────────────
# require_slack_token — 런타임 검증 (import 시점 아님)
# ──────────────────────────────────────────────────────────────

def test_require_slack_token_returns_when_set():
    with patch.object(config_loader, "SLACK_BOT_TOKEN", "xoxb-abc"):
        assert config_loader.require_slack_token() == "xoxb-abc"


def test_require_slack_token_raises_when_missing():
    with patch.object(config_loader, "SLACK_BOT_TOKEN", ""):
        with pytest.raises(RuntimeError):
            config_loader.require_slack_token()


# ──────────────────────────────────────────────────────────────
# now_local — zoneinfo 기반 (DST 반영), 알 수 없는 TZ 폴백
# ──────────────────────────────────────────────────────────────

def test_resolve_tz_known():
    tz = wb._resolve_tz("Asia/Seoul")
    assert tz.key == "Asia/Seoul"


def test_resolve_tz_unknown_falls_back_to_seoul(capsys):
    tz = wb._resolve_tz("Not/AReal_Zone")
    assert tz.key == "Asia/Seoul"
    assert "타임존" in capsys.readouterr().err


def test_now_local_returns_naive_datetime():
    dt = wb.now_local()
    assert isinstance(dt, datetime)
    assert dt.tzinfo is None


def test_resolve_tz_fixed_offset_fallback_when_no_tzdb(capsys):
    """tz 데이터베이스가 아예 없어도 예외 없이 고정 오프셋으로 폴백한다.

    ZoneInfo가 항상 ZoneInfoNotFoundError를 던지도록 mock 하여
    slim 컨테이너(tzdata 미설치) 상황을 재현한다."""
    with patch.object(wb, "ZoneInfo", side_effect=wb.ZoneInfoNotFoundError("no tzdb")):
        tz = wb._resolve_tz("Asia/Seoul")
    assert tz is wb._FIXED_FALLBACK_TZ
    # +9 고정 오프셋이어야 한다
    assert tz.utcoffset(None) == timedelta(hours=9)
    assert "tz 데이터베이스" in capsys.readouterr().err


# ──────────────────────────────────────────────────────────────
# extract_conditions — 공용 추출 로직 필드 매핑
# ──────────────────────────────────────────────────────────────

def _sample_weather():
    return {
        "current": {
            "time": "2026-06-01T12:00",
            "weather_code": 0,          # 맑음 / Clear
            "temperature_2m": 22.0,
            "apparent_temperature": 21.0,
            "relative_humidity_2m": 55,
            "wind_speed_10m": 18.0,     # kmh -> 5.0 m/s
            "wind_gusts_10m": 36.0,     # kmh -> 10.0 m/s
            "cloud_cover": 10,
            "pressure_msl": 1013,
            "visibility": 20000,
        },
        "daily": {
            "temperature_2m_max": [25.0],
            "temperature_2m_min": [15.0],
            "precipitation_probability_max": [10],
            "precipitation_sum": [0.0],
            "uv_index_max": [6.0],
            "sunrise": ["2026-06-01T05:20"],
            "sunset": ["2026-06-01T19:40"],
        },
    }


def test_extract_conditions_maps_core_fields():
    with patch.object(wb, "PAST_DAYS", 0):
        cond = wb.extract_conditions(_sample_weather())
    assert cond.time == "2026-06-01T12:00"
    assert cond.category == "Clear"
    assert cond.temp == 22.0
    assert cond.feels_like == 21.0
    assert cond.temp_max == 25.0
    assert cond.temp_min == 15.0
    assert cond.wind_speed == 5.0        # kmh_to_ms(18)
    assert cond.wind_gust == 10.0        # kmh_to_ms(36)
    assert cond.precip_prob == 10
    assert cond.sunrise == "05:20"
    assert cond.sunset == "19:40"
    # air_data 미전달 시 aqi/pm25는 None
    assert cond.aqi is None
    assert cond.pm25 is None
    # grade_color는 weather_grade의 hex 색상 (grade와 다름)
    assert cond.grade_color.startswith("#")


def test_extract_conditions_uses_air_data():
    air = {"current": {"us_aqi": 42, "pm2_5": 8.1}}
    with patch.object(wb, "PAST_DAYS", 0):
        cond = wb.extract_conditions(_sample_weather(), air)
    assert cond.aqi == 42
    assert cond.pm25 == 8.1


# ──────────────────────────────────────────────────────────────
# calc_golden_hour — timedelta 기반, 경계값에서 예외 없음
# ──────────────────────────────────────────────────────────────

def test_golden_hour_basic():
    result = wb.calc_golden_hour("2026-06-01T05:20", "2026-06-01T19:40")
    assert "05:20~05:50" in result
    assert "19:10~19:40" in result


def test_golden_hour_minute_rollover_no_error():
    """분+30이 60을 넘어도(예: :45) ValueError 없이 시가 올라간다."""
    result = wb.calc_golden_hour("2026-06-01T05:45", "2026-06-01T19:10")
    assert "05:45~06:15" in result   # 05:45 + 30분 = 06:15
    assert "18:40~19:10" in result   # 19:10 - 30분 = 18:40


def test_golden_hour_hour_boundary_no_error():
    """자정 근처 경계에서도 예외가 나지 않는다."""
    result = wb.calc_golden_hour("2026-06-01T00:50", "2026-06-01T23:40")
    assert "00:50~01:20" in result
    assert "23:10~23:40" in result


# ──────────────────────────────────────────────────────────────
# get_seasonal_note — 장마철 연산자 우선순위 수정 검증
# ──────────────────────────────────────────────────────────────

def _seasonal_on(month, day):
    fake = datetime(2026, month, day, 12, 0)
    with patch.object(wb, "now_local", return_value=fake):
        return wb.get_seasonal_note()


def test_seasonal_jangma_mid_june():
    assert "장마철" in _seasonal_on(6, 20)


def test_seasonal_jangma_early_july():
    assert "장마철" in _seasonal_on(7, 10)


def test_seasonal_not_jangma_early_june():
    # 6/10은 장마철 범위(6/15~) 밖이어야 한다
    assert "장마철" not in _seasonal_on(6, 10)


def test_seasonal_not_jangma_late_july():
    # 7/25는 장마철(7/20까지) 밖이어야 한다
    assert "장마철" not in _seasonal_on(7, 25)
