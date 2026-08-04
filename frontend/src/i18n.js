import { createI18n } from 'vue-i18n'
import es from './locales/es.json'
import en from './locales/en.json'

const idiomaGuardado = localStorage.getItem('pulse-idioma')

function detectarIdiomaPorDefecto() {
  const idiomaNavegador = navigator.language || navigator.languages?.[0] || 'en'
  return idiomaNavegador.toLowerCase().startsWith('es') ? 'es' : 'en'
}

export default createI18n({
  legacy: false,
  locale: idiomaGuardado || detectarIdiomaPorDefecto(),
  fallbackLocale: 'en',
  messages: { es, en },
})
