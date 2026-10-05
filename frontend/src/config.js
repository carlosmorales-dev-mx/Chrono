// Configuración central. Es el ÚNICO sitio donde aparece la URL del backend.
const env = import.meta.env ?? {}
const params = new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '')

// Modo demo: datos simulados, no necesita backend.
//   ?demo         -> DeepSeek responde lento
//   ?demo=caida   -> además OpenAI está caído
//   ?demo=ok      -> todo operativo
export const DEMO = env.VITE_DEMO === 'true' || params.has('demo')
const escenario = params.get('demo')
export const DEMO_ESCENARIO = escenario === 'caida' || escenario === 'ok' ? escenario : 'lento'

export const API_URL = (env.VITE_API_URL ?? 'http://127.0.0.1:8001').replace(/\/$/, '')
export const WS_URL = env.VITE_WS_URL ?? API_URL.replace(/^http/, 'ws') + '/ws'

export const POLL_INCIDENTES_MS = 60_000
export const REFRESCO_HISTORIAL_MS = 60_000
