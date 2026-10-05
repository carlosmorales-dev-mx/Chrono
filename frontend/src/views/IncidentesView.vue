<script setup>
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useIncidentesStore } from '../stores/incidentes'
import { useUiStore, INC_PAGINA } from '../stores/ui'
import { useTiempo } from '../composables/useTiempo'
import { useCurva } from '../composables/useCurva'
import { normalizar } from '../utils/incidentes'
import IncidentFeatured from '../components/IncidentFeatured.vue'
import DuracionViva from '../components/DuracionViva.vue'
import LatencyChart from '../components/LatencyChart.vue'

const { t } = useI18n()
const store = useIncidentesStore()
const ui = useUiStore()
const tiempo = useTiempo()
const { curvaDe } = useCurva()

const TIPOS = ['all', 'degraded', 'down']
const RANGOS = ['24h', '7d', '30d', 'all']
const MS_RANGO = { '24h': 24 * 3600000, '7d': 7 * 86400000, '30d': 30 * 86400000, all: Infinity }

// Al cambiar un filtro se vuelve a la primera página y se cierra el detalle abierto.
watch(
  () => [ui.incFiltros.svc, ui.incFiltros.tipo, ui.incFiltros.rango],
  () => {
    ui.incLimite = INC_PAGINA
    ui.incAbierto = null
  }
)

const todos = computed(() => store.lista.map((i) => normalizar(i, tiempo.ahoraMin.value)).sort((a, b) => b.inicio - a.inicio))
const nombres = computed(() => [...new Set(todos.value.map((i) => i.servicio))].sort((a, b) => a.localeCompare(b)))

const filtrados = computed(() => {
  const f = ui.incFiltros
  const corte = tiempo.ahoraMin.value - MS_RANGO[f.rango]
  return todos.value.filter((i) => (f.svc === 'all' || i.servicio === f.svc) && (f.tipo === 'all' || i.estado === f.tipo) && i.inicio >= corte)
})

const resumen = computed(() => {
  const l = filtrados.value
  const cerrados = l.filter((i) => !i.activo)
  return {
    total: l.length,
    enCurso: l.filter((i) => i.activo).length,
    afectado: l.reduce((s, i) => s + i.duracion, 0),
    promedio: cerrados.length ? cerrados.reduce((s, i) => s + i.duracion, 0) / cerrados.length : null,
    mayor: l.reduce((m, i) => (i.duracion > (m ? m.duracion : -1) ? i : m), null),
  }
})

// Primero lo que sigue en curso; después, un grupo por día (del más reciente al más antiguo).
const grupos = computed(() => {
  const vis = filtrados.value.slice(0, ui.incLimite)
  const salida = []
  const enCurso = vis.filter((i) => i.activo)
  if (enCurso.length) salida.push({ llave: 'curso', etiqueta: t('incidents.ongoing'), items: enCurso })
  for (const i of vis.filter((x) => !x.activo)) {
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

const hayFiltros = computed(() => ui.incFiltros.svc !== 'all' || ui.incFiltros.tipo !== 'all' || ui.incFiltros.rango !== '30d')

function alternar(id) {
  ui.incAbierto = ui.incAbierto === id ? null : id
}
</script>

<template>
  <div id="v-inc" class="vista">
    <section class="band">
      <h1>{{ t('incidents.title') }}</h1>
      <p id="i-line" class="subline">{{ t('incidents.summaryLine', { n: resumen.total, running: resumen.enCurso }) }}</p>
    </section>

    <div class="inc-top">
      <IncidentFeatured :incidentes="todos" />

      <section id="i-sum" class="card resumen" :aria-label="t('incidents.summary')">
        <div class="dato">
          <span class="num">{{ resumen.total }}</span>
          <span class="lab">{{ t('incidents.statTotal') }}</span>
        </div>
        <div class="dato">
          <span class="num">{{ resumen.total ? tiempo.duracion(resumen.afectado) : '—' }}</span>
          <span class="lab">{{ t('incidents.statAffected') }}</span>
        </div>
        <div class="dato">
          <span class="num">{{ resumen.promedio !== null ? tiempo.duracion(resumen.promedio) : '—' }}</span>
          <span class="lab">{{ t('incidents.statAverage') }}</span>
        </div>
        <div class="dato">
          <span class="num">{{ resumen.mayor ? tiempo.duracion(resumen.mayor.duracion) : '—' }}</span>
          <span class="lab">{{ resumen.mayor ? t('incidents.statLongestOf', { name: resumen.mayor.servicio }) : t('incidents.statLongest') }}</span>
        </div>
      </section>
    </div>

    <section class="card historial">
      <div class="controls">
        <label class="sr-only" for="i-svc">{{ t('incidents.filterService') }}</label>
        <select id="i-svc" v-model="ui.incFiltros.svc" class="select">
          <option value="all">{{ t('incidents.allServices') }}</option>
          <option v-for="n in nombres" :key="n" :value="n">{{ n }}</option>
        </select>

        <div id="i-type" class="filters" role="group" :aria-label="t('incidents.filterType')">
          <button v-for="k in TIPOS" :key="k" type="button" class="f" :data-ifilter="`type:${k}`" :aria-pressed="ui.incFiltros.tipo === k" @click="ui.incFiltros.tipo = k">
            {{ t(`incidents.type.${k}`) }}
          </button>
        </div>

        <div id="i-range" class="filters" role="group" :aria-label="t('incidents.filterRange')">
          <button v-for="k in RANGOS" :key="k" type="button" class="f" :data-ifilter="`range:${k}`" :aria-pressed="ui.incFiltros.rango === k" @click="ui.incFiltros.rango = k">
            {{ t(`incidents.range.${k}`) }}
          </button>
        </div>
      </div>

      <div id="i-list" class="scroll">
        <p v-if="store.error && !todos.length" class="empty" role="alert">{{ t('incidents.loadError') }}</p>
        <div v-else-if="store.cargado && !filtrados.length" class="empty">
          <p>{{ todos.length ? t('incidents.noMatches') : t('incidents.empty') }}</p>
          <button v-if="hayFiltros && todos.length" type="button" class="btn" @click="ui.reiniciarIncidentes()">{{ t('incidents.clear') }}</button>
        </div>

        <section v-for="g in grupos" :key="g.llave" class="igrp">
          <h2 class="day">
            <span>{{ g.etiqueta }}</span>
            <span v-if="g.llave !== 'curso'">{{ t('incidents.count', { n: g.items.length }, g.items.length) }}</span>
          </h2>

          <article v-for="i in g.items" :key="i.id" class="irow" :class="[i.estado, { ongoing: i.activo }]">
            <button type="button" class="irow-main" data-act="inc-open" :data-iid="i.id" :aria-expanded="ui.incAbierto === i.id" @click="alternar(i.id)">
              <span class="mk" aria-hidden="true"></span>
              <span class="quien">
                <strong>{{ i.servicio }}</strong>
                <span class="sub">{{ t(i.estado === 'down' ? 'incidents.wentDown' : 'incidents.wentDegraded') }}</span>
              </span>
              <span class="rg">{{ tiempo.hora(i.inicio) }} – {{ i.activo ? t('incidents.ongoing') : tiempo.hora(i.fin) }}</span>
              <span class="dur"><DuracionViva v-if="i.activo" :inicio="i.inicio" /><template v-else>{{ tiempo.duracion(i.duracion) }}</template></span>
            </button>

            <div v-if="ui.incAbierto === i.id" class="idet">
              <div class="dstats">
                <div><span>{{ t('incidents.detail.start') }}</span><b>{{ tiempo.fechaHora(i.inicio) }}</b></div>
                <div><span>{{ t('incidents.detail.end') }}</span><b>{{ i.activo ? t('incidents.ongoing') : tiempo.fechaHora(i.fin) }}</b></div>
                <div><span>{{ t('incidents.detail.duration') }}</span><b><DuracionViva v-if="i.activo" :inicio="i.inicio" /><template v-else>{{ tiempo.duracion(i.duracion) }}</template></b></div>
                <div><span>{{ t('incidents.detail.type') }}</span><b>{{ t(`status.${i.estado}`) }}</b></div>
              </div>
              <LatencyChart v-if="curvaDe(i)" :puntos="curvaDe(i).puntos" :marca="curvaDe(i).marca" :estado="curvaDe(i).estado" />
              <p v-else class="nochart">{{ t('incidents.detail.noChart') }}</p>
            </div>
          </article>
        </section>

        <div v-if="filtrados.length > ui.incLimite" class="mas">
          <button type="button" class="btn" @click="ui.incLimite += INC_PAGINA">{{ t('incidents.showMore', { n: filtrados.length - ui.incLimite }) }}</button>
        </div>
      </div>
    </section>
  </div>
</template>
