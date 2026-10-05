import { parseFecha } from './tiempo'

export const N_CUBOS = 48 // 48 cubos de 30 min = 24 h
export const VENTANA_MS = 24 * 60 * 60 * 1000
export const UMBRAL_LENTO = 1.8 // más de 1.8x su mediana = lento

const GRAVEDAD = { up: 0, degraded: 1, down: 2 }

const esNumero = (n) => typeof n === 'number' && Number.isFinite(n)

/** Latencia "normal" de un servicio: la mediana de su historial. */
export function mediana(historial) {
  const v = historial
    .map((p) => p.latencia_ms)
    .filter(esNumero)
    .sort((a, b) => a - b)
  return v.length ? v[Math.floor(v.length / 2)] : null
}

const ESTADOS = new Set(['up', 'degraded', 'down'])

/**
 * Estado de un punto del historial. Si el backend ya lo clasificó (trae `estado`, el PEOR del tramo) se usa tal cual:
 * es el mismo criterio del worker. Si no (puntos en vivo antiguos o la demo), se infiere comparando con lo normal.
 */
export function estadoDe(p, normal) {
  return ESTADOS.has(p.estado) ? p.estado : clasificar(p.latencia_ms, normal)
}

/** Clasifica un chequeo individual respecto a lo normal del servicio. */
export function clasificar(latencia, normal) {
  if (!esNumero(latencia)) return 'down'
  return normal && latencia > normal * UMBRAL_LENTO ? 'degraded' : 'up'
}

/** Mínima, promedio y máxima del historial (null si no hay datos). */
export function estadisticas(historial) {
  const v = historial.map((p) => p.latencia_ms).filter(esNumero)
  if (!v.length) return null
  return {
    min: Math.min(...v),
    max: Math.max(...v),
    avg: v.reduce((a, b) => a + b, 0) / v.length,
  }
}

/** Reparte el historial de 24 h en 48 cubos; cada cubo toma su peor estado. */
export function cubosDe(historial, normal, ahora = Date.now()) {
  const inicio = ahora - VENTANA_MS
  const ancho = VENTANA_MS / N_CUBOS
  const acc = Array.from({ length: N_CUBOS }, () => ({ n: 0, max: 0, peor: 'up' }))

  for (const p of historial) {
    const ts = parseFecha(p.creado_en)
    if (Number.isNaN(ts) || ts < inicio) continue
    const idx = Math.min(N_CUBOS - 1, Math.max(0, Math.floor((ts - inicio) / ancho)))
    const b = acc[idx]
    b.n++
    const lat = esNumero(p.latencia_max) ? p.latencia_max : p.latencia_ms
    if (esNumero(lat) && lat > b.max) b.max = lat
    const st = estadoDe(p, normal)
    if (GRAVEDAD[st] > GRAVEDAD[b.peor]) b.peor = st
  }
  return acc.map((b, i) => ({ estado: b.n ? b.peor : 'none', max: b.max, inicio: inicio + i * ancho }))
}

/** Resumen de toda la flota en las últimas 24 h. */
export function resumenFlota(servicios, historiales, ahora = Date.now()) {
  const celdas = Array.from({ length: N_CUBOS }, () => 'none')
  let up = 0
  let degraded = 0
  let down = 0
  const inicio = ahora - VENTANA_MS
  const ancho = VENTANA_MS / N_CUBOS

  for (const s of servicios) {
    const hist = historiales[s.id] ?? []
    const normal = mediana(hist)
    for (const p of hist) {
      const ts = parseFecha(p.creado_en)
      if (Number.isNaN(ts) || ts < inicio) continue
      const idx = Math.min(N_CUBOS - 1, Math.max(0, Math.floor((ts - inicio) / ancho)))
      const st = estadoDe(p, normal)
      if (st === 'up') up++
      else if (st === 'degraded') degraded++
      else down++
      if (celdas[idx] === 'none' || GRAVEDAD[st] > GRAVEDAD[celdas[idx]]) celdas[idx] = st
    }
  }
  const total = up + degraded + down
  return {
    celdas,
    total,
    uptime: total ? Math.round((up / total) * 1000) / 10 : null,
    pctLento: total ? (degraded / total) * 100 : 0,
    pctCaido: total ? (down / total) * 100 : 0,
  }
}
