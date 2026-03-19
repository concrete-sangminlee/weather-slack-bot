.PHONY: run weekly alert chart test lint install docker-build docker-run

install:
	pip install -r requirements.txt

run:
	python cli.py daily

weekly:
	python cli.py weekly

alert:
	python cli.py alert

chart:
	python cli.py chart

version:
	python cli.py version

test:
	pytest tests/ -v

lint:
	ruff check .

docker-build:
	docker build -t weather-slack-bot .

docker-run:
	docker run --env-file .env weather-slack-bot
