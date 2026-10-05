import { parseFecha } from './tiempo'
import { VENTANA_MS } from './metrics'

/**
 * Normaliza un incidente del backend a una forma estable para la interfaz.
 * Espera: { id, servicio, estado, activo, inicio, duracion_seg }
 * Si el incidente sigue en curso, la duración se calcula en vivo.
 */
export function normalizar(inc, ahora = Date.now()) {
  const inicio = parseFecha(inc.inicio)
  const activo = !!inc.activo
  const duracion = activo ? Math.max(0, Math.round((ahora - inicio) / 1000)) : (inc.duracion_seg ?? 0)
  return {
    id: inc.id,
    servicio: inc.servicio,
    servicioId: inc.servicio_id ?? null,
    estado: inc.estado === 'down' ? 'down' : 'degraded',
    activo,
    inicio,
    fin: activo ? null : inicio + duracion * 1000,
    duracion,
  }
}

/**
 * Tramo del incidente que cae dentro de las últimas 24 h de historial, para marcarlo en la curva.
 * Devuelve null si no hay curva que mostrar (historial insuficiente o incidente más viejo que la ventana).
 */
export function marcaDe(inc, historial, ahora = Date.now()) {
  if (!inc || !historial) return null
  const numeros = historial.filter((p) => typeof p.latencia_ms === 'number')
  if (numeros.length < 2) return null
  const desde = ahora - VENTANA_MS
  const fin = inc.fin ?? ahora
  if (fin < desde) return null
  return { inicio: Math.max(inc.inicio, desde), fin: Math.min(fin, ahora), estado: inc.estado }
}

/** Mayor gravedad primero (caída antes que lentitud), luego el más reciente. */
export function porGravedad(a, b) {
  return (a.estado === 'down' ? 0 : 1) - (b.estado === 'down' ? 0 : 1) || b.inicio - a.inicio
}
