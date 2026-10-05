<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useServiciosStore } from './stores/servicios'
import { useIncidentesStore } from './stores/incidentes'
import { useUiStore } from './stores/ui'
import { useDynamicTitle } from './composables/useDynamicTitle'
import { useTheme } from './composables/useTheme'
import { useTour } from './composables/useTour'
import { cambiarIdioma } from './i18n'
import { DEMO } from './config'
import WordMark from './components/WordMark.vue'
import DemoBanner from './components/DemoBanner.vue'
import TourOverlay from './components/TourOverlay.vue'

const { t, locale } = useI18n()
const route = useRoute()
const servicios = useServiciosStore()
const incidentes = useIncidentesStore()
const ui = useUiStore()
const tour = useTour()
const { oscuro, alternar: alternarTema } = useTheme()

// El botón del tutorial late unos segundos al abrir la app, hasta que se usa.
const llamar = ref(true)
let temporizadores = []

useDynamicTitle(computed(() => servicios.resumen))

// Servicios con problemas: es el número que acompaña a «Incidentes» en la navegación.
const problemas = computed(() => servicios.resumen.degraded + servicios.resumen.down)

// Los datos se cargan aquí (no en cada vista) para que la marca y la insignia del encabezado
// estén al día en cualquier pantalla.
onMounted(async () => {
  document.body.classList.add('intro')
  temporizadores = [
    setTimeout(() => document.body.classList.remove('intro'), 2400),
    setTimeout(() => (llamar.value = false), 7000),
  ]
  incidentes.iniciarPolling()
  await servicios.cargarEstadoInicial()
  servicios.conectarWebSocket()
  servicios.iniciarRefresco()
})

// Al volver a la pestaña (estuvo oculta y los temporizadores no pidieron nada) se pone todo al día de inmediato.
function alVolver() {
  if (document.hidden) return
  servicios.cargarHistoriales()
  incidentes.cargar()
}
document.addEventListener('visibilitychange', alVolver)

onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', alVolver)
  temporizadores.forEach(clearTimeout)
  servicios.detener()
  incidentes.detener()
})
</script>

<template>
  <div class="shell">
    <DemoBanner v-if="DEMO" />

    <header class="top">
      <RouterLink to="/" class="wm-link" :aria-label="t('nav.home')">
        <WordMark :estado="servicios.estadoGeneral" />
      </RouterLink>

      <nav id="nav" class="nav" :aria-label="t('nav.label')">
        <RouterLink to="/" class="nav-link" data-view="panel">{{ t('nav.panel') }}</RouterLink>
        <RouterLink to="/incidentes" class="nav-link" data-view="inc">
          {{ t('nav.incidents') }}
          <span v-if="problemas" class="n" :class="{ down: servicios.resumen.down > 0 }">{{ problemas }}</span>
        </RouterLink>
      </nav>

      <div id="tools" class="tools">
        <button type="button" class="btn" :class="{ nudge: llamar && !tour.visto.value }" data-act="tour" :aria-label="t('tools.tutorial')" :title="t('tools.tutorial')" @click="tour.iniciar()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 4.5v15l12-7.5z" /></svg>
          <span class="txt">{{ t('tools.tutorial') }}</span>
        </button>

        <button type="button" class="round" data-act="theme" :aria-label="t('tools.theme')" :title="t('tools.theme')" @click="alternarTema">
          <svg v-if="oscuro" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>
          <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></svg>
        </button>

        <div class="lang" role="group" aria-label="Idioma / Language">
          <button type="button" data-lang="es" :aria-pressed="locale === 'es'" @click="cambiarIdioma('es')">ES</button>
          <button type="button" data-lang="en" :aria-pressed="locale === 'en'" @click="cambiarIdioma('en')">EN</button>
        </div>

        <button v-if="route.name === 'panel'" type="button" class="btn primary" data-act="add" :aria-label="t('form.add')" :title="t('form.add')" @click="ui.agregarAbierto = true">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
          <span class="txt">{{ t('form.add') }}</span>
        </button>
      </div>
    </header>

    <RouterView />
    <TourOverlay />
  </div>
</template>
