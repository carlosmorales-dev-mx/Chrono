<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useServiciosStore } from '../stores/servicios'
import { estadisticas } from '../utils/metrics'
import { textoMs } from '../utils/format'
import LatencyChart from './LatencyChart.vue'

// Mínima, promedio, máxima y p95 de un servicio, más su curva de las últimas 24 h.
// Lo comparten la fila desplegable de la lista y el cuadro de detalle del mosaico.
const props = defineProps({ servicio: { type: Object, required: true } })

const { t } = useI18n()
const store = useServiciosStore()

const historial = computed(() => store.historiales[props.servicio.id] ?? [])
const puntos = computed(() => historial.value.filter((p) => typeof p.latencia_ms === 'number'))
const stats = computed(() => estadisticas(historial.value))
const p95 = computed(() => store.p95[props.servicio.id] ?? null)
</script>

<template>
  <div class="detail">
    <template v-if="stats">
      <div class="dstats">
        <div><span>{{ t('detail.min') }}</span><b>{{ textoMs(stats.min) }}</b></div>
        <div><span>{{ t('detail.avg') }}</span><b>{{ textoMs(stats.avg) }}</b></div>
        <div><span>{{ t('detail.max') }}</span><b>{{ textoMs(stats.max) }}</b></div>
        <div v-if="p95"><span>p95</span><b>{{ textoMs(p95) }}</b></div>
        <div v-if="servicio.codigo_http"><span>HTTP</span><b>{{ servicio.codigo_http }}</b></div>
      </div>
      <LatencyChart v-if="puntos.length > 1" :puntos="puntos" :estado="servicio.estado" />
    </template>
    <p v-else class="empty">{{ t('detail.noHistory') }}</p>
  </div>
</template>
