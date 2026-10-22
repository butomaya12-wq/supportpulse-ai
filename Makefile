.PHONY: dev test docker-up docker-down

dev:
	SP_MODE=synthetic_local uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

test:
	pytest -q

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
