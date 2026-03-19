#!/bin/bash
# 서울 날씨 Slack 봇 - 설정 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$(command -v python3)"

echo "=== 서울 날씨 Slack 봇 설정 ==="

# 1. 가상환경 생성
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "가상환경 생성 중..."
    "$PYTHON" -m venv "$SCRIPT_DIR/venv"
fi

# 2. 패키지 설치
echo "패키지 설치 중..."
"$SCRIPT_DIR/venv/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"

# 3. .env 파일 확인
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo ""
    echo "⚠️  .env 파일이 생성되었습니다. 아래 값을 설정해주세요:"
    echo "    $SCRIPT_DIR/.env"
    echo ""
    echo "    OPENWEATHERMAP_API_KEY  → https://openweathermap.org/api 에서 발급"
    echo "    SLACK_BOT_TOKEN         → Slack App 생성 후 Bot Token 발급"
    echo "    SLACK_CHANNEL           → 메시지를 보낼 채널명"
    echo ""
    exit 1
fi

# 4. crontab 등록
CRON_CMD="0 7 * * * cd $SCRIPT_DIR && $SCRIPT_DIR/venv/bin/python $SCRIPT_DIR/weather_bot.py >> $SCRIPT_DIR/weather_bot.log 2>&1"

if crontab -l 2>/dev/null | grep -qF "weather_bot.py"; then
    echo "cron 작업이 이미 등록되어 있습니다."
else
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "✅ cron 등록 완료! 매일 아침 7시에 실행됩니다."
fi

echo ""
echo "=== 설정 완료 ==="
echo "테스트 실행: $SCRIPT_DIR/venv/bin/python $SCRIPT_DIR/weather_bot.py"
