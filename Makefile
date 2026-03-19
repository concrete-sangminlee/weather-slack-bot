.PHONY: run weekly alert chart test install docker-build docker-run

install:
	pip install -r requirements.txt

run:
	python weather_bot.py

weekly:
	python weekly_summary.py

alert:
	python alert.py

chart:
	python chart.py

test:
	pytest tests/ -v

docker-build:
	docker build -t weather-slack-bot .

docker-run:
	docker run --env-file .env weather-slack-bot
