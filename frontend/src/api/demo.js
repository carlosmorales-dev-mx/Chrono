// Backend simulado. Devuelve EXACTAMENTE las mismas formas que la API real,
// así los stores y componentes no saben (ni les importa) cuál están usando.
import { escenarioDemo } from './demoControl'

const N = 48
const PASO = 30 * 60 * 1000

function rng(seed) {
  return () => {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const SEMILLA = [
  { nombre: 'cmorales.dev', host: 'cmorales.dev', base: 380, anclado: true },
  { nombre: 'DeepSeek API', host: 'api.deepseek.com', base: 1100 },
  { nombre: 'OpenAI API', host: 'api.openai.com', base: 930 },
  { nombre: 'Anthropic API', host: 'api.anthropic.com', base: 330 },
  { nombre: 'GitHub API', host: 'api.github.com', base: 235 },
  { nombre: 'Cloudflare', host: 'cloudflare.com', base: 310 },
  { nombre: 'Vercel', host: 'vercel.com', base: 300 },
  { nombre: 'npm registry', host: 'registry.npmjs.org', base: 80 },
  { nombre: 'PyPI', host: 'pypi.org', base: 130 },
]

function estadoDe(lat, base) {
  if (lat === null) return 'down'
  return lat > base * 1.8 ? 'degraded' : 'up'
}

function construirHist(d, i) {
  const r = rng(1000 + i * 77)
  const h = []
  for (let k = 0; k < N; k++) {
    let lat = d.base * (0.88 + r() * 0.26)
    if (r() < 0.035) lat *= 2.2
    h.push(Math.round(lat))
  }
  if (d.nombre === 'Vercel') h[26] = null
  if (d.nombre === 'OpenAI API') h[41] = Math.round(h[41] * 2.4)
  if (d.nombre === 'GitHub API') h[12] = Math.round(h[12] * 2.3)
  if (d.nombre === 'DeepSeek API') {
    ;[14, 15, 33].forEach((k) => (h[k] = Math.round(h[k] * 2.2)))
    for (let k = N - 5; k < N; k++) h[k] = Math.round(h[k] * 2.2)
  }
  return h
}

const T0 = Date.now()
let siguienteId = SEMILLA.length + 1

// 'modo' dice cómo se comporta cada servicio ahora mismo: up | slow | down
const servicios = SEMILLA.map((d, i) => {
  const hist = construirHist(d, i)
  const lat = hist[N - 1]
  return {
    id: i + 1,
    nombre: d.nombre,
    url: `https://${d.host}`,
    base: d.base,
    anclado: !!d.anclado,
    hist,
    modo: d.nombre === 'DeepSeek API' ? 'slow' : 'up',
    estado: estadoDe(lat, d.base),
    latencia_ms: lat,
    codigo_http: lat === null ? null : 200,
    desde: estadoDe(lat, d.base) === 'up' ? null : T0 - 3 * 60000,
    nuevo: false,
  }
})
const porNombre = (n) => servicios.find((s) => s.nombre === n)

// Incidentes pasados: un puñado repartido en ~10 días, con una racha de lentitud
// de DeepSeek (justo el caso que llena la lista con filas repetidas).
const PASADOS = (() => {
  const r = rng(4242)
  const nombres = SEMILLA.map((s) => s.nombre)
  const lista = []
  for (let i = 0; i < 26; i++) {
    const nombre = nombres[Math.floor(r() * nombres.length)]
    const bajo = r() < 0.18
    lista.push({ servicio: nombre, estado: bajo ? 'down' : 'degraded', horas: 1 + r() * 240, dur: Math.round(20 + r() * (bajo ? 400 : 600)) })
  }
  for (let k = 0; k < 8; k++) {
    lista.push({ servicio: 'DeepSeek API', estado: 'degraded', horas: 30 + k * 0.4, dur: Math.round(20 + r() * 90) })
  }
  return lista
    .sort((a, b) => a.horas - b.horas)
    .map((x, idx) => ({ ...x, id: 1000 + idx, inicio: T0 - x.horas * 3600000 }))
})()

const copia = (v) => JSON.parse(JSON.stringify(v))
const demora = (v, ms = 140) => new Promise((resolve) => setTimeout(() => resolve(copia(v)), ms))
const buscar = (id) => servicios.find((s) => s.id === Number(id))

const publico = (s) => ({
  id: s.id,
  nombre: s.nombre,
  url: s.url,
  anclado: s.anclado,
  estado: s.nuevo ? null : s.estado,
  latencia_ms: s.nuevo ? null : s.latencia_ms,
  codigo_http: s.codigo_http,
})

export const getEstadoActual = () => demora(servicios.map(publico))

export const getHistorial = (id) => {
  const s = buscar(id)
  if (!s || s.nuevo) return demora([])
  const ahora = Date.now()
  return demora(s.hist.map((lat, k) => ({ latencia_ms: lat, estado: estadoDe(lat, s.base), creado_en: new Date(ahora - (N - 1 - k) * PASO).toISOString() })))
}

export const getPercentiles = (id) => {
  const s = buscar(id)
  const v = (s?.hist ?? []).filter((n) => typeof n === 'number').sort((a, b) => a - b)
  return demora({ p95: v.length ? v[Math.min(v.length - 1, Math.floor(v.length * 0.95))] : null })
}

export const getIncidentes = () => {
  const ahora = Date.now()
  const activos = servicios
    .filter((s) => !s.nuevo && s.estado !== 'up')
    .map((s) => ({
      id: 5000 + s.id,
      servicio: s.nombre,
      servicio_id: s.id,
      estado: s.estado,
      activo: true,
      inicio: new Date(s.desde ?? ahora).toISOString(),
      duracion_seg: Math.round((ahora - (s.desde ?? ahora)) / 1000),
    }))
  const pasados = PASADOS.map((p) => ({
    id: p.id,
    servicio: p.servicio,
    servicio_id: servicios.find((s) => s.nombre === p.servicio)?.id,
    estado: p.estado,
    activo: false,
    inicio: new Date(p.inicio).toISOString(),
    duracion_seg: p.dur,
  }))
  return demora([...activos, ...pasados].sort((a, b) => new Date(b.inicio) - new Date(a.inicio)))
}

export const crearServicio = (nombre, url) => {
  const s = {
    id: siguienteId++,
    nombre,
    url,
    base: 150 + Math.round(Math.random() * 400),
    anclado: false,
    hist: Array(N).fill(null),
    modo: 'up',
    estado: null,
    latencia_ms: null,
    codigo_http: null,
    desde: null,
    nuevo: true,
    creado: Date.now(),
  }
  servicios.push(s)
  return demora({ id: s.id, nombre: s.nombre, url: s.url, anclado: false })
}

export const editarServicio = (id, nombre, url) => {
  const s = buscar(id)
  if (s) {
    s.nombre = nombre
    s.url = url
  }
  return demora({ id: Number(id), nombre, url })
}

export const anclarServicio = (id) => {
  const s = buscar(id)
  if (s) s.anclado = !s.anclado
  return demora({ id: Number(id), anclado: !!s?.anclado })
}

export const borrarServicio = (id) => {
  const i = servicios.findIndex((s) => s.id === Number(id))
  if (i > -1) servicios.splice(i, 1)
  return demora({})
}

/* ------------------------------------------------------------------ chequeos en vivo */
const suscriptores = new Set()
let temporizador = null

// Un "ciclo" es lo que haría el worker: medir cada servicio y avisar por el WebSocket.
function ciclo() {
  servicios.forEach((s) => {
    if (s.nuevo) {
      if (Date.now() - s.creado < 4000) return
      s.nuevo = false
    }
    const f = s.modo === 'slow' ? 2.2 : 1
    const lat = s.modo === 'down' ? null : Math.round(s.base * f * (0.9 + Math.random() * 0.2))
    const estado = estadoDe(lat, s.base)
    if (estado !== s.estado) s.desde = estado === 'up' ? null : Date.now()
    s.latencia_ms = lat
    s.estado = estado
    s.codigo_http = lat === null ? null : 200
    s.hist[N - 1] = lat
    suscriptores.forEach((envia) => envia({ tipo: 'chequeo', servicio_id: s.id, estado, codigo_http: s.codigo_http, latencia_ms: lat }))
  })
}

/**
 * Cambia el escenario de la demo y lo hace visible al instante:
 *   lento -> DeepSeek responde lento · caida -> además OpenAI no responde · ok -> todo operativo
 */
export function setEscenario(nombre) {
  const ds = porNombre('DeepSeek API')
  const oa = porNombre('OpenAI API')
  if (ds) ds.modo = nombre === 'ok' ? 'up' : 'slow'
  if (oa) oa.modo = nombre === 'caida' ? 'down' : 'up'
  escenarioDemo.value = nombre
  ciclo()
  // La lentitud "de siempre" de DeepSeek conserva su hora de inicio al volver al escenario base.
  if (ds && ds.estado === 'degraded' && nombre !== 'ok') ds.desde = T0 - 3 * 60000
}

// Arranque: aplica el escenario pedido en la URL (?demo=caida | ?demo=ok) sin avisar a nadie todavía.
{
  const inicial = escenarioDemo.value
  const ds = porNombre('DeepSeek API')
  const oa = porNombre('OpenAI API')
  if (inicial === 'ok' && ds) ds.modo = 'up'
  if (inicial === 'caida' && oa) oa.modo = 'down'
  if (inicial !== 'lento') ciclo() // que el primer estado que se pida ya refleje el escenario
}

// WebSocket simulado: cada 3 s "llega" un chequeo por servicio.
export function abrirSocket({ onOpen, onMessage, onClose }) {
  let activo = true
  const abrir = setTimeout(() => activo && onOpen(), 250)
  suscriptores.add(onMessage)
  if (!temporizador) temporizador = setInterval(ciclo, 3000)
  return {
    get readyState() {
      return activo ? 1 : 3
    },
    close() {
      activo = false
      clearTimeout(abrir)
      suscriptores.delete(onMessage)
      if (!suscriptores.size && temporizador) {
        clearInterval(temporizador)
        temporizador = null
      }
      onClose()
    },
  }
}
