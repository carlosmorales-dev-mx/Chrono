# Chrono · frontend

Interfaz del monitor de estado y latencia de servicios. Vue 3 + Vite, Pinia, vue-i18n (ES/EN) y vue-router.

## Cómo correrlo

```bash
pnpm install
pnpm dev            # http://localhost:5173
pnpm build          # genera dist/
```

Necesita el backend en `http://127.0.0.1:8001` (se cambia con `VITE_API_URL`, ver `.env.example`).

## Modo demo

Funciona **sin backend**, con datos simulados. Úsalo para ver la interfaz o para compartirla:

| URL | Escenario |
|---|---|
| `/?demo` | DeepSeek responde lento |
| `/?demo=caida` | además OpenAI no responde |
| `/?demo=ok` | todo operativo |

En el aviso superior puedes cambiar de escenario sin recargar. También se activa con `VITE_DEMO=true`.

## Estructura

```
src/
  api/          real.js (backend) · demo.js (simulado) · index.js (elige uno)
  stores/       servicios · incidentes · ui
  views/        PanelView · IncidentesView
  components/   ServiceRow · LatencyChart · FleetCard · IncidentList · IncidentFeatured
                ServiceFormModal · DeleteConfirmModal · WordMark · DemoBanner · TourOverlay
  composables/  useTiempo · useAhora · useTheme · useDynamicTitle · useCurva · useTour
  tour/         engine.js (motor del tutorial) · steps.js (los pasos)
  utils/        metrics · incidentes · format · tiempo · storage
  styles/       tokens → base → incidentes → tutorial → refinamientos → app (el orden importa)
  locales/      es.json · en.json
```

## Decisiones de diseño

- **Lo sano se ve callado, lo roto destaca.** El color fuerte (ámbar/coral) se reserva para estados; la interfaz usa azul cielo y lavanda.
- **Una sola URL del backend**, en `src/config.js`.
- **Tutorial interactivo** (botón «Tutorial»): un cursor animado ejecuta las acciones reales sobre la interfaz. Los pasos que provocan una caída solo existen en el modo demo.
- **Accesibilidad:** contraste AA medido en ambos temas, foco visible, `prefers-reduced-motion`, y superficies sólidas con `prefers-contrast: more`.
- Si las horas aparecen corridas, ajusta `parseFecha` en `src/utils/tiempo.js` (único punto).
