<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useIncidentesStore } from '../stores/incidentes'
import { useTiempo } from '../composables/useTiempo'
import { useCurva } from '../composables/useCurva'
import { normalizar, porGravedad } from '../utils/incidentes'
import DuracionViva from './DuracionViva.vue'
import LatencyChart from './LatencyChart.vue'

// Tarjeta del panel: lo que está pasando ahora (con su curva) y lo más reciente.
const props = defineProps({ limite: { type: Number, default: 5 } })
const { t } = useI18n()
const incidentes = useIncidentesStore()
const tiempo = useTiempo()
const { curvaDe } = useCurva()

const items = computed(() => incidentes.lista.map((i) => normalizar(i, tiempo.ahoraMin.value)).sort((a, b) => b.inicio - a.inicio))
const enCurso = computed(() => items.value.filter((i) => i.activo).sort(porGravedad))
const peor = computed(() => (enCurso.value.some((i) => i.estado === 'down') ? 'down' : 'degraded'))

// Los últimos incidentes ya cerrados, agrupados por día.
const grupos = computed(() => {
  const salida = []
  for (const i of items.value.filter((x) => !x.activo).slice(0, props.limite)) {
    const llave = tiempo.llaveDia(i.inicio)
    let g = salida[salida.length - 1]
    if (!g || g.llave !== llave) {
      g = { llave, etiqueta: tiempo.etiquetaDia(i.inicio), items: [] }
      salida.push(g)
    }
    g.items.push(i)
  }
  return salida
})
</script>

<template>
  <section id="c-inc" class="card">
    <div class="card-h">
      <h2>{{ t('incidents.title') }}</h2>
      <span v-if="enCurso.length" class="chip" :class="peor">{{ t('incidents.activeCount', { n: enCurso.length }) }}</span>
    </div>

    <div v-if="enCurso.length" class="live-block">
      <div class="day"><span>{{ t('incidents.ongoing') }}</span></div>
      <template v-for="(o, idx) in enCurso" :key="o.id">
        <div class="inc ongoing" :class="o.estado">
          <span class="mk" aria-hidden="true"></span>
          <div>
            <strong>{{ o.servicio }}</strong>
            <span class="sub">{{ t(o.estado === 'down' ? 'incidents.wentDown' : 'incidents.wentDegraded') }} · {{ t('incidents.started', { when: tiempo.hace(o.inicio) }) }}</span>
          </div>
          <span class="dur"><DuracionViva :inicio="o.inicio" /></span>
        </div>
        <div v-if="idx === 0 && curvaDe(o)" class="inc-chart">
          <LatencyChart :puntos="curvaDe(o).puntos" :marca="curvaDe(o).marca" :estado="curvaDe(o).estado" />
        </div>
      </template>
    </div>

    <div class="scroll">
      <p v-if="incidentes.error && !items.length" class="empty">{{ t('incidents.loadError') }}</p>
      <p v-else-if="incidentes.cargado && !items.length" class="empty">{{ t('incidents.empty') }}</p>
      <template v-for="g in grupos" :key="g.llave">
        <div class="day">
          <span>{{ g.etiqueta }}</span>
          <span>{{ t('incidents.count', { n: g.items.length }, g.items.length) }}</span>
        </div>
        <div v-for="i in g.items" :key="i.id" class="inc" :class="i.estado">
          <span class="mk" aria-hidden="true"></span>
          <div>
            <strong>{{ i.servicio }}</strong>
            <span class="sub">{{ t(i.estado === 'down' ? 'incidents.wentDown' : 'incidents.wentDegraded') }} · {{ tiempo.hora(i.inicio) }}</span>
          </div>
          <span class="dur">{{ tiempo.duracion(i.duracion) }}</span>
        </div>
      </template>
    </div>

    <RouterLink to="/incidentes" class="link" data-view="inc">{{ t('incidents.viewAll') }}</RouterLink>
  </section>
</template>
