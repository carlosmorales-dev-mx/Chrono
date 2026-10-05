import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAhora, useAhoraMin } from './useAhora'

const llave = (ms) => {
  const d = new Date(ms)
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
}

export function useTiempo() {
  const { t, locale } = useI18n()
  const ahora = useAhora() // 1 s: solo para quien muestra segundos en vivo
  const ahoraMin = useAhoraMin() // 30 s: «hace 3 min», etiquetas de día…
  const loc = computed(() => (locale.value === 'es' ? 'es-MX' : 'en-US'))

  function hace(ts) {
    const m = Math.floor((ahoraMin.value - ts) / 60000)
    if (m < 1) return t('time.justNow')
    if (m < 60) return t('time.minAgo', { n: m })
    const h = Math.floor(m / 60)
    if (h < 24) return t('time.hourAgo', { n: h })
    return t('time.dayAgo', { n: Math.floor(h / 24) })
  }

  function desde(ts) {
    const m = Math.floor((ahoraMin.value - ts) / 60000)
    return m < 1 ? t('time.sinceNow') : t('time.since', { when: hace(ts) })
  }

  const hora = (ts) => new Intl.DateTimeFormat(loc.value, { hour: '2-digit', minute: '2-digit' }).format(ts)

  const fechaHora = (ts) =>
    new Intl.DateTimeFormat(loc.value, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(ts)

  function etiquetaDia(ts) {
    if (llave(ts) === llave(ahoraMin.value)) return t('time.today')
    if (llave(ts) === llave(ahoraMin.value - 86400000)) return t('time.yesterday')
    return new Intl.DateTimeFormat(loc.value, { weekday: 'long', day: 'numeric', month: 'long' }).format(ts)
  }

  function duracion(seg) {
    seg = Math.max(0, Math.round(seg))
    if (seg < 60) return `${seg} s`
    const m = Math.floor(seg / 60)
    if (m < 60) return `${m} min`
    const h = Math.floor(m / 60)
    if (h < 24) return `${h} h ${m % 60} min`
    return `${Math.floor(h / 24)} d ${h % 24} h`
  }

  return { ahora, ahoraMin, loc, hace, desde, hora, fechaHora, etiquetaDia, duracion, llaveDia: llave }
}
