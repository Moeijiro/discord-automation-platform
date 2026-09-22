# Developer shortcuts. Everything here is optional -- the README lists the raw
# commands too.

BACKEND := backend
VENV := $(BACKEND)/.venv/bin

.PHONY: help install api bot web test clean

help:
	@echo "make install   install backend + frontend dependencies"
	@echo "make api       run the FastAPI backend on :8000"
	@echo "make bot       run the Discord gateway bot (needs DISCORD_BOT_TOKEN)"
	@echo "make web       run the dashboard on :5173"
	@echo "make test      run the backend test suite"

install:
	python3 -m venv $(BACKEND)/.venv
	$(VENV)/pip install -r $(BACKEND)/requirements-dev.txt
	cd frontend && npm install

api:
	cd $(BACKEND) && .venv/bin/uvicorn app.main:app --reload --port 8000

bot:
	cd $(BACKEND) && .venv/bin/python -m app.bot

web:
	cd frontend && npm run dev

test:
	cd $(BACKEND) && .venv/bin/python -m pytest

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -f $(BACKEND)/*.db
