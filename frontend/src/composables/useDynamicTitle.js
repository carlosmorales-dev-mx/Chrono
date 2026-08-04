import { watch } from 'vue'

function crearFaviconSvg(color) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="${color}" stroke="%230D0714" stroke-width="2.5"/></svg>`
  return `data:image/svg+xml,${svg}`
}

export function useDynamicTitle(resumen) {
  watch(
    resumen,
    (r) => {
      const link = document.querySelector("link[rel~='icon']") || document.createElement('link')
      link.rel = 'icon'
      document.head.appendChild(link)

      if (r.down > 0) {
        document.title = `🔴 Chrono — ${r.down} incidente${r.down > 1 ? 's' : ''}`
        link.href = crearFaviconSvg('%23F26B7A')
      } else if (r.degraded > 0) {
        document.title = `🟡 Chrono — ${r.degraded} degradado${r.degraded > 1 ? 's' : ''}`
        link.href = crearFaviconSvg('%23E8A93E')
      } else {
        document.title = 'Chrono — todo operativo'
        link.href = crearFaviconSvg('%236FE3C4')
      }
    },
    { immediate: true, deep: true }
  )
}
