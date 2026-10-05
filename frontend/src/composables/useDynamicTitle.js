import { watchEffect } from 'vue'
import { useI18n } from 'vue-i18n'

const COLOR = { ok: '%237b8096', degraded: '%23f0a43a', down: '%23e9587a' }

function favicon(color) {
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><circle cx='16' cy='16' r='9' fill='none' stroke='${color}' stroke-width='5'/></svg>`
  return `data:image/svg+xml,${svg}`
}

/** La pestaña refleja el estado: título corto y un anillo del color del semáforo. */
export function useDynamicTitle(resumen) {
  const { t } = useI18n()

  watchEffect(() => {
    const r = resumen.value
    const link = document.querySelector("link[rel~='icon']") || document.head.appendChild(Object.assign(document.createElement('link'), { rel: 'icon' }))
    if (r.down > 0) {
      document.title = `Chrono · ${t('title.down', { n: r.down })}`
      link.href = favicon(COLOR.down)
    } else if (r.degraded > 0) {
      document.title = `Chrono · ${t('title.slow', { n: r.degraded })}`
      link.href = favicon(COLOR.degraded)
    } else {
      document.title = `Chrono · ${t('title.allUp')}`
      link.href = favicon(COLOR.ok)
    }
  })
}
