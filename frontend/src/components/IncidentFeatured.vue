<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useServiciosStore } from '../stores/servicios'
import { useUiStore } from '../stores/ui'
import { useTiempo } from '../composables/useTiempo'
import { useCurva } from '../composables/useCurva'
import { mediana } from '../utils/metrics'
import { textoMs } from '../utils/format'
import { porGravedad } from '../utils/incidentes'
import DuracionViva from './DuracionViva.vue'
import LatencyChart from './LatencyChart.vue'

// Lo que está pasando AHORA: el incidente en curso más grave (o el último, si no hay ninguno en curso).
// `incidentes` llega ya normalizado y ordenado del más reciente al más antiguo.
const props = defineProps({ incidentes: { type: Array, required: true } })

const { t } = useI18n()
const servicios = useServiciosStore()
const ui = useUiStore()
const tiempo = useTiempo()
const { servicioDe, curvaDe } = useCurva()

const enCurso = computed(() => props.incidentes.filter((i) => i.activo).sort(porGravedad))
const elegido = computed(() => (ui.featId ? props.incidentes.find((i) => i.id === ui.featId) : null))
const inc = computed(() => elegido.value ?? enCurso.value[0] ?? props.incidentes[0] ?? null)
const vivo = computed(() => !!inc.value && inc.value.activo)

const servicio = computed(() => servicioDe(inc.value))
const curva = computed(() => (inc.value ? curvaDe(inc.value) : null))
const p95 = computed(() => (servicio.value ? servicios.p95[servicio.value.id] ?? null : null))

// «Ahora»: latencia actual del servicio, con cuántas veces su normal si va lento.
const ahoraTxt = computed(() => {
  const s = servicio.value
  if (!s) return '—'
  if (s.latencia_ms === null || s.latencia_ms === undefined) return s.estado === 'down' ? t('row.noResponse') : '—'
  const normal = mediana(servicios.historiales[s.id] ?? [])
  const veces = s.estado === 'degraded' && normal ? ` · ${(s.latencia_ms / normal).toFixed(1)}×` : ''
  return textoMs(s.latencia_ms) + veces
})
</script>

<template>
  <section id="i-feat" class="card feat" :class="[inc ? inc.estado : '', { live: vivo }]">
    <template v-if="inc">
      <div class="card-h">
        <h2>{{ vivo ? t('incidents.featured.live') : t('incidents.featured.last') }}</h2>
        <div v-if="enCurso.length > 1" class="chips">
          <button v-for="o in enCurso" :key="o.id" type="button" class="f" data-act="feat-pick" :aria-pressed="o.id === inc.id" @click="ui.featId = o.id">{{ o.servicio }}</button>
        </div>
      </div>

      <div class="feat-body">
        <div class="feat-info">
          <div class="feat-name"><span class="dotf" aria-hidden="true"></span>{{ inc.servicio }}</div>
          <p class="feat-msg">{{ t(inc.estado === 'down' ? 'incidents.wentDown' : 'incidents.wentDegraded') }}</p>
          <dl class="feat-stats">
            <div><dt>{{ t('incidents.detail.start') }}</dt><dd>{{ tiempo.fechaHora(inc.inicio) }}</dd></div>
            <div><dt>{{ vivo ? t('incidents.featured.elapsed') : t('incidents.detail.duration') }}</dt><dd><DuracionViva v-if="vivo" :inicio="inc.inicio" /><template v-else>{{ tiempo.duracion(inc.duracion) }}</template></dd></div>
            <div><dt>{{ t('list.now') }}</dt><dd data-k="fnow">{{ ahoraTxt }}</dd></div>
            <div v-if="vivo"><dt>p95</dt><dd>{{ p95 ? textoMs(p95) : '—' }}</dd></div>
            <div v-else><dt>{{ t('incidents.featured.resolved') }}</dt><dd>{{ tiempo.hace(inc.fin) }}</dd></div>
          </dl>
        </div>
        <div class="feat-chart">
          <LatencyChart v-if="curva" :puntos="curva.puntos" :marca="curva.marca" :estado="curva.estado" />
          <p v-else class="nochart">{{ t('incidents.detail.noChart') }}</p>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="card-h"><h2>{{ t('incidents.featured.none') }}</h2></div>
      <p class="empty">{{ t('incidents.empty') }}</p>
    </template>
  </section>
</template>
