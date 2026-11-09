.PHONY: demo run test build

demo:
	python3 run_local.py --demo
run:
	python3 run_local.py
test:
	cd backend && ../.venv/bin/python -m pytest -q
	cd frontend && npm run typecheck
build:
	cd frontend && npm run build
