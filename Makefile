.PHONY: run test lint install docker-build docker-run

install:
	pip install -r requirements.txt

run:
	python weather_bot.py

test:
	pytest tests/ -v

docker-build:
	docker build -t weather-slack-bot .

docker-run:
	docker run --env-file .env weather-slack-bot
