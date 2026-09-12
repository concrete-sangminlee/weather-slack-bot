FROM python:3.12-slim

WORKDIR /app

# 코어 의존성 + 차트(matplotlib): 일일 브리핑은 차트를 포함한다
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt "matplotlib>=3.8.0"

# 런타임에 필요한 소스와 설정 (config_loader/locales가 없으면 import 단계에서 실패)
COPY weather_bot.py config_loader.py cli.py chart.py ./
COPY config.yml ./
COPY locales ./locales

CMD ["python", "cli.py", "daily"]
