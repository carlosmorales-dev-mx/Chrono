# Chrono

[English](README.md) | **Español**

Monitor de estado en tiempo real para APIs y servicios públicos. Chrono
revisa una lista configurable de endpoints a intervalos regulares,
persiste el historial, y transmite actualizaciones en vivo a cada
navegador conectado por WebSocket — sin necesidad de refrescar
manualmente para ver que un servicio cayó.

Originalmente enfocado en monitorear un puñado de APIs conocidas de cara
a desarrolladores (OpenAI, Anthropic, DeepSeek, GitHub, Cloudflare,
Vercel, el registro de npm, PyPI), ahora permite agregar, editar y quitar
cualquier endpoint HTTP directamente desde el dashboard.

## Descripción general

Chrono divide el monitoreo de estado en tres procesos independientes que
solo se comunican entre sí por HTTP y WebSocket, nunca compartiendo una
conexión de base de datos:

- Un **worker** revisa todos los servicios monitoreados en paralelo a un
  intervalo fijo y reporta los resultados al backend. No tiene ninguna
  credencial de base de datos — solo conoce la URL del backend.
- El **backend** es el único proceso que habla con PostgreSQL. Recibe
  los resultados de chequeo del worker, detecta transiciones de estado
  para abrir y cerrar incidentes, y transmite actualizaciones en vivo a
  cada navegador conectado.
- El **frontend** renderiza el dashboard y recibe actualizaciones por
  WebSocket, así que un servicio que cae aparece en pantalla en
  segundos, sin necesidad de sondeo (polling).

## Capturas de pantalla

*Agrega aquí una captura del dashboard antes de publicar.*

## Funcionalidades

- Dashboard de estado en vivo: tarjetas por servicio, ordenadas por
  severidad (caídos primero, luego degradados, luego sanos), con
  servicios anclados siempre mostrados primero sin importar su estado
- Agregar, editar y quitar servicios monitoreados directamente desde la
  interfaz
- Actualizaciones en tiempo real por WebSocket, con un banner visible de
  reconexión si la conexión se cae
- Detección automática de incidentes: las transiciones de estado (sano a
  degradado, degradado a caído, y de regreso) abren y cierran registros
  de incidentes con marca de tiempo de inicio y fin
- Línea de tiempo de incidentes mostrando los más recientes de todos los
  servicios, con su duración
- Gráficas de historial de latencia con downsampling adaptativo: los
  datos recientes se muestran como puntos crudos; una vez que un
  servicio acumula más de aproximadamente 30 puntos en una ventana de 24
  horas, se agrupan en bloques de tamaño igual en vez de por hora fija
  de reloj, así un servicio recién agregado nunca se queda con una
  gráfica vacía
- Percentiles de latencia p50 / p95 / p99 por servicio en una ventana
  móvil de 24 horas
- Insignias (badges) SVG de estado públicamente embebibles, una por
  servicio, generadas bajo demanda
- Interfaz bilingüe (español / inglés)
- Barra de resumen con el conteo de servicios operativos, degradados y
  caídos, y un porcentaje de uptime

## Arquitectura

```mermaid
graph LR
    External["APIs externas<br/>(OpenAI, Anthropic, GitHub, npm...)"] -.->|"chequeos de salud<br/>cada 30s"| Worker["Worker<br/>asyncio + httpx"]
    Worker -->|"POST /internal/ingest"| Backend["Backend<br/>FastAPI"]
    Backend --> DB[("PostgreSQL")]
    Backend -->|"WebSocket /ws"| Frontend["Frontend<br/>Vue 3"]
    Browser[Navegador] --> Frontend
```

El worker nunca se conecta a PostgreSQL directamente. Solo conoce la URL
del backend y reporta resultados mediante un simple POST HTTP; el
backend es el único dueño del esquema y el único proceso con
credenciales de base de datos. Esto mantiene al worker desechable y
fácil de escalar o reemplazar sin tocar la persistencia en absoluto.

## Stack tecnológico

| Capa        | Tecnología                          |
| ------------- | -------------------------------------- |
| Frontend      | Vue 3, Pinia, vue-i18n                  |
| Backend       | FastAPI, SQLAlchemy, WebSockets         |
| Worker        | Python asyncio, httpx                   |
| Base de datos | PostgreSQL 16 (contenedor Podman)       |
| Tiempo real   | WebSocket (backend a frontend)          |

## Primeros pasos

Corre la instalación en este orden: **install, luego start, luego dev.**
Saltarte `start` es la causa más común de que el primer arranque salga
mal (el esquema todavía no va a existir).

### Requisitos previos

- Python 3.12 o superior
- Node.js con `npm`
- [Podman](https://podman.io) y `podman-compose`

### Instalación

```bash
git clone <url-de-este-repositorio> chrono
cd chrono
make install
```

Esto crea un entorno virtual para el backend, uno para el worker, e
instala las dependencias npm del frontend.

### Configuración

El backend lee su cadena de conexión de base de datos desde
`backend/.env`:

```
DATABASE_URL=postgresql://pulse:pulse@localhost:5433/pulse
```

Ajusta las credenciales y el puerto para que coincidan con
`docker-compose.yml` si cambias alguno. El worker necesita saber dónde
alcanzar al backend; revisa su propia configuración para la variable
correspondiente antes de correrlo contra un host o puerto distinto al
default.

### Primer arranque

```bash
make start
```

Esto levanta PostgreSQL, espera a que esté listo, crea el esquema, y
siembra los ocho servicios iniciales. Córrelo una vez después de `make
install`, o de nuevo cada vez que recrees el volumen de la base de datos
desde cero.

### Ejecución

```bash
make dev
```

Levanta PostgreSQL (si no está corriendo ya), el backend, el worker y el
frontend juntos, y detiene los tres procesos de desarrollo de forma
limpia con `Ctrl+C` (PostgreSQL sigue corriendo; detenlo aparte con
`make down`). Los componentes también se pueden correr por separado:

```bash
make db          # Solo PostgreSQL
make backend     # Solo FastAPI, con auto-recarga
make worker      # Solo el worker de chequeo
make frontend    # Solo el servidor de desarrollo de Vite
make status      # Lista los contenedores corriendo
```

**Ten paciencia después del primer arranque.** El worker chequea cada 30
segundos, así que el dashboard se llena poco a poco, no de golpe. Las
gráficas de latencia y los percentiles se calculan sobre una ventana
móvil de 24 horas; un servicio recién sembrado se va a ver escaso hasta
que corran varios ciclos de chequeo. Esto es esperado, no un bug.

## Solución de problemas

| Síntoma | Causa probable | Arreglo |
| --------- | ----------------- | --------- |
| `uvicorn: command not found` después de `make backend` | El venv del backend no tiene dependencias instaladas, o nunca se creó | `make install-backend` |
| `externally-managed-environment` al hacer `pip install` | La shell en realidad no está dentro del venv | Usa el binario del venv directo: `backend/venv/bin/pip install -r backend/requirements.txt` |
| `ImportError` / `ModuleNotFoundError` justo después de copiar el proyecto de otra PC | Los entornos virtuales no son portables; hornean rutas absolutas de la máquina que los creó | `rm -rf backend/venv && python -m venv backend/venv && backend/venv/bin/pip install -r backend/requirements.txt` (repite para `worker/venv`) |
| Errores de `npm` después de copiar el proyecto de otra PC | `node_modules` usa symlinks y binarios nativos específicos de la máquina, tampoco portable | `rm -rf frontend/node_modules && cd frontend && npm install` |
| `Makefile:N: *** missing separator. Stop.` | Una línea de receta está indentada con espacios en vez de un tab literal | Revisa con `cat -A Makefile` -- los tabs reales se ven como `^I` |
| `'case' builtin usado fuera de un bloque 'switch'` al activar un venv | La shell es `fish`, y `venv/bin/activate` es un script de `bash`/`sh` | Usa `source venv/bin/activate.fish` directo, o confía en `make`, que fuerza `bash` |
| `short-name "postgres:16-alpine" did not resolve to an alias` | Podman necesita una referencia de imagen completa, o le falta `containers-common` | Usa `docker.io/library/postgres:16-alpine` en `docker-compose.yml`, o instala `containers-common` |
| `relation "servicios" does not exist` | El esquema nunca se creó | Corre `make start` |
| El dashboard dice "aún no monitoreas nada" justo después de `make start` | Esperado -- las tablas existen pero el worker todavía no completa un ciclo de chequeo | Espera hasta 30 segundos; confirma que `make worker` esté corriendo |
| Las gráficas o percentiles se ven escasos o vacíos | Ambos se calculan sobre una ventana móvil de 24 horas; un servicio recién sembrado tiene muy pocos puntos todavía | Deja correr al worker un rato -- esto es esperado, no un bug |
| Banner "Conexión perdida — reconectando..." | Normalmente un desajuste de CORS entre el puerto real del frontend y los orígenes permitidos del backend | Confirma que `backend/main.py` use `allow_origin_regex`, no una lista fija de `allow_origins`, y que el backend esté corriendo |

## Estructura del proyecto

```
.
├── backend
│   ├── main.py                App de FastAPI, CORS, endpoint WebSocket
│   ├── database.py            Engine y sesión de SQLAlchemy
│   ├── db_models.py           Modelos del ORM
│   ├── models_schemas.py      Esquemas Pydantic de request/response
│   ├── websocket_manager.py   Transmisión a clientes conectados
│   ├── incident_detector.py   Lógica de transición-de-estado a incidente
│   ├── init_db.py             Crea el esquema (correr una vez)
│   ├── seed_servicios.py      Siembra la lista inicial de servicios
│   └── api/routes.py          Todas las rutas HTTP
├── worker
│   └── check_servicios.py     Chequeos de salud en paralelo, reporta al backend
├── frontend
│   └── src
│       ├── components/          Componentes de la interfaz del dashboard
│       ├── stores/               Store de Pinia
│       └── composables/          Lógica reactiva compartida (p.ej. título dinámico de pestaña)
├── docker-compose.yml
└── Makefile
```

## Decisiones de diseño destacadas

- **El worker nunca toca la base de datos.** Solo conoce la URL HTTP
  del backend. Esto mantiene las credenciales de base de datos en un
  único lugar y hace que el worker sea trivial de escalar, reiniciar o
  reemplazar sin depender del esquema.
- **El historial de latencia usa downsampling adaptativo, no bloques de
  tiempo fijos.** Agrupar por hora de reloj significa que un servicio
  recién agregado, o una base de datos recién recreada, tiene una
  gráfica vacía hasta que se acumula una hora completa de datos —
  inaceptable para una demo en vivo. En su lugar, se devuelven los
  puntos crudos hasta que un servicio acumula más de aproximadamente 30
  chequeos en 24 horas, después de lo cual se agrupan en bloques de
  tamaño igual por cantidad de filas, no por tiempo de reloj.
- **Los incidentes se detectan al momento de escribir, no se
  reconstruyen después.** Cada resultado de chequeo que llega se compara
  contra el estado anterior de ese servicio; una transición abre o
  cierra un registro de incidente de inmediato, en vez de inferirse
  retroactivamente a partir del historial crudo.
- **CORS se configura con un regex de origen, no una lista fija.** Vite
  incrementa el puerto de su servidor de desarrollo automáticamente
  cuando el default ya está ocupado (por ejemplo, cuando otro proyecto
  también está corriendo localmente). Una lista fija de orígenes
  permitidos se rompe en silencio en el momento en que eso pasa;
  aceptar cualquier origen `localhost`/`127.0.0.1` sin importar el
  puerto evita ese modo de falla por completo para desarrollo local.
- **Los fallos de transmisión se autolimpian.** Si un navegador
  conectado desapareció sin un cierre limpio (cerró la pestaña, perdió
  la red), el manejador de WebSocket lo quita de la lista de conexiones
  activas en vez de dejar que una conexión muerta interrumpa la
  transmisión hacia todos los demás.

## Limitaciones conocidas

- Sin autenticación en ningún endpoint. Cualquiera que pueda alcanzar el
  backend puede agregar, editar o borrar servicios monitoreados, o
  mandar resultados de chequeo falsos a través del endpoint de ingesta.
  Esto es aceptable para un despliegue local o en red de confianza; no
  es seguro exponerlo públicamente tal como está.
- Todavía no hay suite de tests automatizados.
- El proyecto pasó por varias fases de desarrollo (el código todavía
  hace referencia a "Fase 5.5" para la línea de tiempo de incidentes en
  comentarios), pero no todo ese historial está reflejado en este
  documento.

## Licencia

Todavía no decidida. Agrega un archivo `LICENSE` antes de tratar esto
como open source bajo una licencia específica.

## Autor

Carlos Morales — [cmorales.dev](https://cmorales.dev)