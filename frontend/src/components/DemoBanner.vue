<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { escenarioDemo } from '../api/demoControl'
import { useIncidentesStore } from '../stores/incidentes'

const { t } = useI18n()
const incidentes = useIncidentesStore()
const opciones = ['lento', 'caida', 'ok']
const salir = computed(() => window.location.pathname)

// Cambia el escenario simulado y refresca los incidentes de inmediato.
async function elegir(nombre) {
  const { setEscenario } = await import('../api/demo')
  setEscenario(nombre)
  await incidentes.cargar()
}
</script>

<template>
  <p class="demo-banner" role="note">
    <span>{{ t('demo.banner') }}</span>
    <span class="esc" role="group" :aria-label="t('demo.try')">
      <button v-for="o in opciones" :key="o" type="button" :aria-pressed="escenarioDemo === o" @click="elegir(o)">
        {{ t(`demo.esc.${o}`) }}
      </button>
    </span>
    <a :href="salir">{{ t('demo.exit') }}</a>
  </p>
</template>
