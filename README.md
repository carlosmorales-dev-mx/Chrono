# Chrono

**English** | [Español](README.es.md)

Real-time status monitor for public APIs and services. Chrono checks a
configurable list of endpoints on an interval, persists the history, and
pushes live updates to every connected browser over a WebSocket -- no
manual refresh needed to see a service go down.

Originally scoped to track a handful of well-known developer-facing APIs
(OpenAI, Anthropic, DeepSeek, GitHub, Cloudflare, Vercel, the npm
registry, PyPI), it now supports adding, editing, and removing any HTTP
endpoint from the dashboard itself.

## Overview

Chrono splits status monitoring into three independent processes that
only talk to each other over HTTP and WebSocket, never by sharing a
database connection:

- A **worker** checks every monitored service in parallel on a fixed
  interval and reports the results to the backend. It holds no database
  credentials at all -- only the backend's URL.
- The **backend** is the only process that talks to PostgreSQL. It
  receives check results from the worker, detects state transitions to
  open and close incidents, and broadcasts live updates to every
  connected browser.
- The **frontend** renders the dashboard and receives updates over a
  WebSocket, so a service going down appears on screen within seconds,
  without polling.

## Screenshots

*Add a screenshot of the dashboard here before publishing.*

## Features

- Live status dashboard: per-service cards, sorted by severity (down
  first, then degraded, then healthy), with pinned services always shown
  first regardless of status
- Add, edit, and remove monitored services directly from the UI
- Real-time updates over WebSocket, with a visible reconnection banner
  if the connection drops
- Automatic incident detection: state transitions (healthy to degraded,
  degraded to down, and back) open and close incident records with
  start and end timestamps
- Incident timeline showing the most recent incidents across all
  services, with duration
- Latency history charts with adaptive downsampling: recent data renders
  as raw points; once a service accumulates more than roughly 30 points
  in a 24-hour window, they are grouped into equal-sized blocks instead
  of fixed hourly buckets, so a freshly added service is never stuck
  with an empty chart
- p50 / p95 / p99 latency percentiles per service over a rolling
  24-hour window
- Publicly embeddable SVG status badges, one per service, generated on
  demand
- Bilingual interface (Spanish / English)
- Summary bar with counts of operational, degraded, and down services,
  and an uptime percentage

## Architecture

```mermaid
graph LR
    External["External APIs<br/>(OpenAI, Anthropic, GitHub, npm...)"] -.->|"health checks<br/>every 30s"| Worker["Worker<br/>asyncio + httpx"]
    Worker -->|"POST /internal/ingest"| Backend["Backend<br/>FastAPI"]
    Backend --> DB[("PostgreSQL")]
    Backend -->|"WebSocket /ws"| Frontend["Frontend<br/>Vue 3"]
    Browser[Browser] --> Frontend
```

The worker never connects to PostgreSQL directly. It only knows the
backend's URL and reports results over a plain HTTP POST; the backend is
the single owner of the schema and the only process with database
credentials. This keeps the worker disposable and easy to scale or
replace without touching persistence at all.

## Tech Stack

| Layer     | Technology                       |
| ---------- | ----------------------------------- |
| Frontend   | Vue 3, Pinia, vue-i18n              |
| Backend    | FastAPI, SQLAlchemy, WebSockets     |
| Worker     | Python asyncio, httpx               |
| Database   | PostgreSQL 16 (Podman container)    |
| Realtime   | WebSocket (backend to frontend)     |

## Getting Started

Run the setup in this order: **install, then start, then dev.** Skipping
`start` is the most common cause of a broken first run (the schema
won't exist yet).

### Prerequisites

- Python 3.12 or newer
- Node.js with `npm`
- [Podman](https://podman.io) and `podman-compose`

### Installation

```bash
git clone <this-repository-url> chrono
cd chrono
make install
```

This creates a virtual environment for the backend, one for the worker,
and installs the frontend's npm dependencies.

### Configuration

The backend reads its database connection string from `backend/.env`:

```
DATABASE_URL=postgresql://pulse:pulse@localhost:5433/pulse
```

Adjust the credentials and port to match `docker-compose.yml` if you
change either. The worker needs to know where the backend is reachable;
check its own configuration for the relevant variable before running it
against a non-default host or port.

### First run

```bash
make start
```

This starts PostgreSQL, waits for it to become ready, creates the
schema, and seeds the eight initial services. Run it once after `make
install`, or again any time you recreate the database volume from
scratch.

### Running

```bash
make dev
```

Starts PostgreSQL (if not already running), the backend, the worker,
and the frontend together, and stops the three development processes
cleanly on `Ctrl+C` (PostgreSQL keeps running; stop it separately with
`make down`). Components can also run individually:

```bash
make db          # PostgreSQL only
make backend     # FastAPI only, with auto-reload
make worker      # the checking worker only
make frontend    # the Vite dev server only
make status      # list running containers
```

**Be patient after the first run.** The worker checks every 30 seconds,
so the dashboard populates gradually, not instantly. Latency charts and
percentiles are computed over a rolling 24-hour window; a freshly seeded
service will look sparse until several check cycles have run. This is
expected, not a bug.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --------- | -------------- | ----- |
| `uvicorn: command not found` after `make backend` | The backend venv has no dependencies installed, or was never created | `make install-backend` |
| `externally-managed-environment` from `pip install` | The shell is not actually inside the venv | Use the venv's binary directly: `backend/venv/bin/pip install -r backend/requirements.txt` |
| `ImportError` / `ModuleNotFoundError` right after copying the project from another machine | Virtual environments are not portable; they bake in absolute paths from the machine that created them | `rm -rf backend/venv && python -m venv backend/venv && backend/venv/bin/pip install -r backend/requirements.txt` (repeat for `worker/venv`) |
| `npm` errors after copying the project from another machine | `node_modules` uses symlinks and machine-specific native binaries, also not portable | `rm -rf frontend/node_modules && cd frontend && npm install` |
| `Makefile:N: *** missing separator. Stop.` | A recipe line is indented with spaces instead of a literal tab | Check with `cat -A Makefile` -- real tabs show as `^I` |
| `'case' builtin usado fuera de un bloque 'switch'` when activating a venv | The shell is `fish`, and `venv/bin/activate` is a `bash`/`sh` script | Use `source venv/bin/activate.fish` directly, or rely on `make`, which forces `bash` |
| `short-name "postgres:16-alpine" did not resolve to an alias` | Podman needs either a fully-qualified image reference or `containers-common` | Use `docker.io/library/postgres:16-alpine` in `docker-compose.yml`, or install `containers-common` |
| `relation "servicios" does not exist` | The schema was never created | Run `make start` |
| Dashboard says "no services monitored yet" right after `make start` | Expected -- tables exist but the worker hasn't completed a check cycle yet | Wait up to 30 seconds; confirm `make worker` is running |
| Charts or percentiles look sparse or empty | Both are computed over a rolling 24-hour window; a freshly seeded service has very few points so far | Let the worker run for a while -- this is expected, not a bug |
| "Connection lost -- reconnecting..." banner | Usually a CORS mismatch between the frontend's actual port and the backend's allowed origins | Confirm `backend/main.py` uses `allow_origin_regex`, not a fixed `allow_origins` list, and that the backend is running |

## Project Structure

```
.
├── backend
│   ├── main.py                FastAPI app, CORS, WebSocket endpoint
│   ├── database.py            SQLAlchemy engine and session
│   ├── db_models.py           ORM models
│   ├── models_schemas.py      Pydantic request/response schemas
│   ├── websocket_manager.py   Broadcast to connected clients
│   ├── incident_detector.py   State-transition to incident logic
│   ├── init_db.py             Creates the schema (run once)
│   ├── seed_servicios.py      Seeds the initial service list
│   └── api/routes.py          All HTTP routes
├── worker
│   └── check_servicios.py     Parallel health checks, reports to the backend
├── frontend
│   └── src
│       ├── components/          Dashboard UI components
│       ├── stores/               Pinia store
│       └── composables/          Shared reactive logic (e.g. dynamic tab title)
├── docker-compose.yml
└── Makefile
```

## Notable Design Decisions

- **The worker never touches the database.** It only knows the
  backend's HTTP URL. This keeps database credentials in exactly one
  place and makes the worker trivial to scale, restart, or replace
  independently of the schema.
- **Latency history uses adaptive downsampling, not fixed time
  buckets.** Grouping by clock hour means a freshly added service, or a
  freshly recreated database, has an empty chart until a full hour of
  data accumulates -- unacceptable for a live demo. Instead, raw points
  are returned until a service accumulates more than roughly 30 checks
  in 24 hours, after which they are grouped into equal-sized blocks by
  row count rather than by wall-clock time.
- **Incidents are detected at write time, not reconstructed later.**
  Every ingested check result is compared against the previous state
  for that service; a transition opens or closes an incident record
  immediately, rather than being inferred retroactively from raw
  history.
- **CORS is configured with an origin regex, not a fixed list.** Vite
  increments its dev server port automatically when the default is
  already taken (for example, when another project is also running
  locally). A fixed list of allowed origins breaks silently the moment
  that happens; matching any `localhost`/`127.0.0.1` origin regardless
  of port avoids the failure mode entirely for local development.
- **Broadcast failures prune themselves.** If a connected browser has
  gone away without a clean disconnect (closed tab, lost network), the
  WebSocket manager removes it from the active list instead of letting
  one dead connection interrupt the broadcast to everyone else.

## Known Limitations

- No authentication on any endpoint. Anything that can reach the
  backend can add, edit, or delete monitored services, or submit fake
  check results through the ingest endpoint. This is acceptable for a
  local or trusted-network deployment; it is not safe to expose
  publicly as-is.
- No automated test suite yet.
- The project went through several development phases (the codebase
  still references "Fase 5.5" for the incident timeline in code
  comments), but not all of that history is reflected in this document.

## Author

Carlos Morales — [cmorales.dev](https://cmorales.dev)
