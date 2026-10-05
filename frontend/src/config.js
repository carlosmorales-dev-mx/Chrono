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

// VITE_API_URL:
//   · sin definir  -> http://127.0.0.1:8001 (desarrollo con `make dev`)
//   · una URL      -> el backend está en otro sitio
//   · VACÍA ("")   -> el backend está en el MISMO origen que la página: así se construye la imagen de
//                     contenedor, donde nginx reenvía /servicios, /ws… al backend (sin CORS).
const mismoOrigen = env.VITE_API_URL === ''
export const API_URL = mismoOrigen ? '' : (env.VITE_API_URL ?? 'http://127.0.0.1:8001').replace(/\/$/, '')

const origenWs = () => {
  if (typeof window === 'undefined') return ''
  return `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
}
export const WS_URL = env.VITE_WS_URL ?? (mismoOrigen ? `${origenWs()}/ws` : `${API_URL.replace(/^http/, 'ws')}/ws`)

// Para mostrar en mensajes («No hay respuesta de …»): si el backend está en el mismo origen, el de la página.
export const API_ETIQUETA = API_URL || (typeof window !== 'undefined' ? window.location.origin : '')

export const POLL_INCIDENTES_MS = 60_000
export const REFRESCO_HISTORIAL_MS = 60_000
