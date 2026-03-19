"""테스트 설정 — 외부 API 호출 실패 시 graceful skip"""
import os

import pytest
import requests

os.environ.setdefault("SLACK_BOT_TOKEN", "test")
os.environ.setdefault("SLACK_CHANNEL", "test")


@pytest.fixture(autouse=True)
def skip_on_api_timeout(request):
    """외부 API 호출 테스트에서 타임아웃 발생 시 skip 처리"""
    yield
    # post-test: 아무것도 안 함 (예외는 테스트 자체에서 처리)


def api_available():
    """Open-Meteo API 접근 가능 여부 확인"""
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast?latitude=0&longitude=0&current=temperature_2m", timeout=10)
        return r.status_code == 200
    except Exception:
        return False


requires_api = pytest.mark.skipif(
    not api_available(),
    reason="Open-Meteo API unavailable or timed out",
)
