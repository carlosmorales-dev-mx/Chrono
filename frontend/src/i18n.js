import { createI18n } from 'vue-i18n'
import es from './locales/es.json'
import en from './locales/en.json'
import { leer, guardar } from './utils/storage'

export const CLAVE_IDIOMA = 'chrono-idioma'

function idiomaInicial() {
  // 'pulse-idioma' era el nombre anterior de la clave: se respeta para no perder la preferencia.
  const guardado = leer(CLAVE_IDIOMA) || leer('pulse-idioma')
  if (guardado === 'es' || guardado === 'en') return guardado
  return (navigator.language || 'en').toLowerCase().startsWith('es') ? 'es' : 'en'
}

const i18n = createI18n({
  legacy: false,
  locale: idiomaInicial(),
  fallbackLocale: 'en',
  messages: { es, en },
})

export function cambiarIdioma(idioma) {
  i18n.global.locale.value = idioma
  guardar(CLAVE_IDIOMA, idioma)
  document.documentElement.lang = idioma
}

document.documentElement.lang = i18n.global.locale.value

export default i18n
