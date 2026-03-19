"""테스트 설정 — 외부 API 타임아웃 시 graceful skip"""
import functools
import os

import pytest

os.environ.setdefault("SLACK_BOT_TOKEN", "test")
os.environ.setdefault("SLACK_CHANNEL", "test")


def requires_api(func):
    """외부 API 호출 중 타임아웃/네트워크 오류 시 skip 처리"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "timed out" in str(e).lower() or "timeout" in str(e).lower() or "connection" in str(e).lower():
                pytest.skip(f"API unavailable: {e}")
            raise
    return wrapper
