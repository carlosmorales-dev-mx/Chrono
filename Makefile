SHELL := /bin/bash

BACKEND_DIR  := backend
WORKER_DIR   := worker
FRONTEND_DIR := frontend

BACKEND_VENV    := $(CURDIR)/$(BACKEND_DIR)/venv
BACKEND_PY      := $(BACKEND_VENV)/bin/python
BACKEND_PIP     := $(BACKEND_VENV)/bin/pip
BACKEND_UVICORN := $(BACKEND_VENV)/bin/uvicorn

WORKER_VENV := $(CURDIR)/$(WORKER_DIR)/venv
WORKER_PY   := $(WORKER_VENV)/bin/python
WORKER_PIP  := $(WORKER_VENV)/bin/pip

BACKEND_PORT  := 8001
FRONTEND_PORT := 5173

# Cambia esto a "pnpm" o "yarn" si el frontend no usa npm.
FRONTEND_PKG := pnpm
.PHONY: help install install-backend install-worker install-frontend \
        start wait-db dev up db backend worker frontend down status \
        check-backend-ready check-worker-ready check-frontend-ready

.DEFAULT_GOAL := help

## ---------------------------------------------------------------------
## Ayuda
## ---------------------------------------------------------------------

help: ## muestra estos comandos
	@echo "MSC / Chrono"
	@echo
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_-]+:.*##/ { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

## ---------------------------------------------------------------------
## Instalación
## ---------------------------------------------------------------------

install: install-backend install-worker install-frontend ## instala todo: venv de backend, venv de worker, node_modules del frontend
	@echo "listo -- todo instalado"

install-backend: ## crea backend/venv e instala requirements.txt
	@test -d $(BACKEND_VENV) || python -m venv $(BACKEND_VENV)
	$(BACKEND_PIP) install -q --upgrade pip
	$(BACKEND_PIP) install -q -r $(BACKEND_DIR)/requirements.txt

install-worker: ## crea worker/venv e instala requirements.txt
	@test -d $(WORKER_VENV) || python -m venv $(WORKER_VENV)
	$(WORKER_PIP) install -q --upgrade pip
	$(WORKER_PIP) install -q -r $(WORKER_DIR)/requirements.txt

install-frontend: ## instala dependencias del frontend
	cd $(FRONTEND_DIR) && $(FRONTEND_PKG) install

## ---------------------------------------------------------------------
## Primer arranque (correr UNA vez después de install, antes de dev)
## ---------------------------------------------------------------------

start: check-backend-ready wait-db ## crea las tablas de la base de datos y carga los servicios iniciales
	cd $(BACKEND_DIR) && $(BACKEND_PY) init_db.py
	cd $(BACKEND_DIR) && $(BACKEND_PY) seed_servicios.py
	@echo "listo -- corre 'make dev' para levantar todo"

## ---------------------------------------------------------------------
## Componentes
## ---------------------------------------------------------------------

dev: check-backend-ready check-worker-ready check-frontend-ready wait-db ## levanta db + backend + worker + frontend (backend y worker se auto-reinician si truenan). Ctrl+C detiene los tres procesos de desarrollo (la DB se queda corriendo -- 'make down' para pararla)
	@echo "backend   http://127.0.0.1:$(BACKEND_PORT)  (auto-reinicio si truena)"
	@echo "frontend  http://localhost:$(FRONTEND_PORT)"
	@echo "worker    corriendo, sin puerto propio (auto-reinicio si truena)"
	@echo "Ctrl+C detiene backend/worker/frontend -- la DB sigue corriendo (make down para pararla)"
	@echo
	@PIDS=(); \
	setsid bash -c 'cd $(BACKEND_DIR) && while true; do $(BACKEND_UVICORN) main:app --reload --port $(BACKEND_PORT); echo "[backend] se cayó, reintentando en 2s..."; sleep 2; done' & PIDS+=($$!); \
	setsid bash -c 'cd $(WORKER_DIR) && while true; do $(WORKER_PY) check_servicios.py; echo "[worker] se cayó, reintentando en 2s..."; sleep 2; done' & PIDS+=($$!); \
	setsid bash -c 'cd $(FRONTEND_DIR) && exec $(FRONTEND_PKG) run dev --port $(FRONTEND_PORT)' & PIDS+=($$!); \
	STOPPED=0; \
	stop() { \
		if [ "$$STOPPED" = "1" ]; then return 0; fi; \
		STOPPED=1; \
		trap '' INT TERM; \
		echo; echo "deteniendo backend/worker/frontend..."; \
		for pid in "$${PIDS[@]}"; do kill -TERM "-$$pid" 2>/dev/null; done; \
		for _ in 1 2 3 4 5 6 7 8 9 10; do \
			alive=0; \
			for pid in "$${PIDS[@]}"; do kill -0 "$$pid" 2>/dev/null && alive=1; done; \
			[ "$$alive" = "0" ] && break; \
			sleep 0.5; \
		done; \
		for pid in "$${PIDS[@]}"; do kill -KILL "-$$pid" 2>/dev/null; done; \
		return 0; \
	}; \
	trap stop INT TERM; \
	wait "$${PIDS[@]}"; \
	stop; \
	true

up: dev ## alias de 'dev'


db: ## levanta PostgreSQL con podman-compose
	podman-compose up -d
	@echo "PostgreSQL corriendo en localhost:5433"

backend: check-backend-ready ## corre el backend con reload
	cd $(BACKEND_DIR) && $(BACKEND_UVICORN) main:app --reload --port $(BACKEND_PORT)

worker: check-worker-ready ## corre el worker de chequeo de servicios
	cd $(WORKER_DIR) && $(WORKER_PY) check_servicios.py

frontend: check-frontend-ready ## corre el servidor de desarrollo del frontend
	cd $(FRONTEND_DIR) && $(FRONTEND_PKG) run dev --port $(FRONTEND_PORT)

down: ## detiene el contenedor de PostgreSQL
	podman-compose down

status: ## contenedores corriendo
	podman ps

## ---------------------------------------------------------------------
## Guardas
## ---------------------------------------------------------------------

wait-db: ## levanta el contenedor de Postgres si no está corriendo y espera a que responda (uso interno de start/dev)
	@podman-compose up -d
	@echo "esperando a que Postgres esté listo..."
	@for i in $$(seq 1 15); do \
		podman exec pulse_db pg_isready -U pulse >/dev/null 2>&1 && break; \
		sleep 1; \
	done

check-backend-ready:
	@test -d $(BACKEND_VENV) || { echo "falta $(BACKEND_DIR)/venv -- corre: make install-backend"; exit 1; }

check-worker-ready:
	@test -d $(WORKER_VENV) || { echo "falta $(WORKER_DIR)/venv -- corre: make install-worker"; exit 1; }

check-frontend-ready:
	@test -d $(FRONTEND_DIR)/node_modules || { echo "falta $(FRONTEND_DIR)/node_modules -- corre: make install-frontend"; exit 1; }

# --- Chrono: pruebas, migraciones y mantenimiento (agregado por fase2.sh) ---
PYTHON ?= python3

.PHONY: test test-backend test-worker smoke migrate purge unused unused-clean empty

test: test-backend test-worker ## corre las pruebas de backend y worker (sin base de datos)

test-backend: check-backend-ready ## pruebas unitarias del backend
	cd $(BACKEND_DIR) && $(BACKEND_PY) -m unittest discover -s tests

test-worker: check-worker-ready ## pruebas unitarias del worker
	cd $(WORKER_DIR) && $(WORKER_PY) -m unittest discover -s tests

smoke: ## prueba de humo contra un backend ya encendido (make dev): endpoints, seguridad e incidentes
	$(PYTHON) tools/humo_backend.py http://127.0.0.1:$(BACKEND_PORT) --token "$$(grep -E '^INGEST_TOKEN=' $(BACKEND_DIR)/.env | cut -d= -f2-)"

migrate: check-backend-ready wait-db ## aplica a la base existente los ajustes de esquema (índices); es seguro repetirlo
	cd $(BACKEND_DIR) && $(BACKEND_PY) migrar.py

purge: check-backend-ready wait-db ## borra los chequeos más viejos que RETENCION_DIAS (30 por defecto)
	cd $(BACKEND_DIR) && $(BACKEND_PY) retencion.py

unused: ## informe: archivos sin uso, carpetas vacías y cachés (no borra nada)
	$(PYTHON) tools/mantenimiento.py todo

unused-clean: ## borra (con confirmación) lo que es seguro: archivos sin uso y carpetas vacías
	$(PYTHON) tools/mantenimiento.py sin-uso --borrar
	$(PYTHON) tools/mantenimiento.py vacias --borrar

empty: ## solo carpetas vacías (informe)
	$(PYTHON) tools/mantenimiento.py vacias
