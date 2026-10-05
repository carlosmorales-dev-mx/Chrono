import { useServiciosStore } from '../stores/servicios'
import { useTiempo } from './useTiempo'
import { marcaDe } from '../utils/incidentes'

/**
 * Relaciona un incidente con la curva de latencia de su servicio.
 * El historial guardado cubre las últimas 24 h: fuera de eso no hay curva que mostrar.
 */
export function useCurva() {
  const servicios = useServiciosStore()
  const tiempo = useTiempo()

  function servicioDe(inc) {
    if (!inc) return null
    return servicios.lista.find((s) => s.id === inc.servicioId) ?? servicios.lista.find((s) => s.nombre === inc.servicio) ?? null
  }

  // { puntos, marca, estado } listo para pasar a <LatencyChart>, o null si no hay curva.
  function curvaDe(inc) {
    const s = servicioDe(inc)
    const hist = s ? servicios.historiales[s.id] : null
    const marca = marcaDe(inc, hist, tiempo.ahoraMin.value)
    return marca ? { puntos: hist, marca, estado: inc.estado } : null
  }

  return { servicioDe, curvaDe }
}
