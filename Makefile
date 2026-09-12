.PHONY: run weekly alert chart test lint install install-dev docker-build docker-run

# 코어 + 차트(matplotlib) — 로컬에서 `make run`/`make chart`까지 동작하도록
install:
	pip install -r requirements.txt "matplotlib>=3.8.0"

# 테스트/린트 도구 포함 (pyproject의 dev extra)
install-dev:
	pip install -e ".[dev]"

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
