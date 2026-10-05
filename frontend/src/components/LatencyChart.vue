<script setup>
import { computed, ref, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTiempo } from '../composables/useTiempo'
import { parseFecha } from '../utils/tiempo'
import { textoMs } from '../utils/format'

// puntos: [{ latencia_ms, creado_en }] (se ignoran los que no tienen latencia)
// marca:  { inicio, fin, estado } en ms -> resalta el tramo de un incidente sobre la curva
const props = defineProps({
  puntos: { type: Array, required: true },
  estado: { type: String, default: null },
  marca: { type: Object, default: null },
})

const { t } = useI18n()
const { hora } = useTiempo()
const gid = useId()

const W = 600
const MAX_PUNTOS = 120
const ANCHO_MIN_BANDA = 12

const caja = ref(null)
const hover = ref(null)

// Reduce miles de chequeos a ~120 puntos promediando por tramos.
const base = computed(() => {
  const src = props.puntos
    .map((p) => ({ ts: parseFecha(p.creado_en), lat: p.latencia_ms }))
    .filter((p) => Number.isFinite(p.ts) && typeof p.lat === 'number')
    .sort((a, b) => a.ts - b.ts)
  if (src.length < 2) return []
  const n = Math.min(MAX_PUNTOS, src.length)
  const tam = src.length / n
  const out = []
  for (let i = 0; i < n; i++) {
    const desde = Math.floor(i * tam)
    const hasta = Math.max(desde + 1, Math.floor((i + 1) * tam))
    const grupo = src.slice(desde, hasta)
    out.push({
      ts: grupo[Math.floor(grupo.length / 2)].ts,
      lat: Math.round(grupo.reduce((a, p) => a + p.lat, 0) / grupo.length),
    })
  }
  return out
})

const escala = computed(() => {
  const v = base.value.map((p) => p.lat)
  if (!v.length) return null
  let mn = Math.min(...v)
  let mx = Math.max(...v)
  const pad = Math.max((mx - mn) * 0.12, mx * 0.04, 1)
  mn = Math.max(0, mn - pad)
  mx = mx + pad
  const t0 = base.value[0].ts
  const t1 = base.value[base.value.length - 1].ts
  const span = t1 - t0 || 1
  return { t0, t1, X: (ts) => ((ts - t0) / span) * W, Y: (lat) => 110 - ((lat - mn) / (mx - mn || 1)) * 100 }
})

const serie = computed(() => {
  const e = escala.value
  return e ? base.value.map((p) => ({ ...p, x: e.X(p.ts), y: e.Y(p.lat) })) : []
})

const linea = computed(() => serie.value.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' '))
const area = computed(() => {
  const s = serie.value
  return s.length ? `${linea.value} L${s[s.length - 1].x.toFixed(1)},110 L${s[0].x.toFixed(1)},110 Z` : ''
})

const color = computed(() => (props.estado === 'down' ? 'var(--down-tape)' : props.estado === 'degraded' ? 'var(--slow-tape)' : 'var(--ok-tape)'))

const banda = computed(() => {
  const e = escala.value
  const m = props.marca
  if (!e || !m) return null
  const x1 = Math.max(0, Math.min(W, e.X(m.inicio)))
  const x2 = Math.max(0, Math.min(W, e.X(m.fin)))
  const ancho = Math.max(x2 - x1, ANCHO_MIN_BANDA)
  const x = Math.min(x1, W - ancho)
  return { x: x.toFixed(1), w: ancho.toFixed(1), color: m.estado === 'down' ? 'var(--down-tape)' : 'var(--slow-tape)' }
})

// Sonda que sigue al cursor (o al cursor animado del tutorial, que envía los mismos eventos).
const sonda = computed(() => {
  const p = hover.value === null ? null : serie.value[hover.value]
  if (!p) return { estilo: { display: 'none' }, punto: {}, tip: {}, texto: '' }
  const izq = (p.x / W) * 100
  return {
    estilo: { display: 'block', left: `${izq}%` },
    punto: { top: `${(p.y / 120) * 100}%` },
    tip: { left: '0', transform: izq > 75 ? 'translateX(-100%)' : izq < 25 ? 'translateX(0)' : 'translateX(-50%)' },
    texto: `${hora(p.ts)} · ${textoMs(p.lat)}`,
  }
})

function mover(evento) {
  if (!caja.value || !serie.value.length) return
  const r = caja.value.getBoundingClientRect()
  const x = ((evento.clientX - r.left) / (r.width || 1)) * W
  let mejor = 0
  let distancia = Infinity
  serie.value.forEach((p, i) => {
    const d = Math.abs(p.x - x)
    if (d < distancia) {
      distancia = d
      mejor = i
    }
  })
  hover.value = mejor
}

function salir(evento) {
  if (!evento.relatedTarget || !caja.value || !caja.value.contains(evento.relatedTarget)) hover.value = null
}
</script>

<template>
  <div ref="caja" class="chart" @pointermove="mover" @pointerout="salir">
    <svg viewBox="0 0 600 120" preserveAspectRatio="none" role="img" :aria-label="t('detail.chartLabel')">
      <defs>
        <linearGradient :id="gid" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" :style="{ stopColor: color, stopOpacity: 0.32 }" />
          <stop offset="1" :style="{ stopColor: color, stopOpacity: 0 }" />
        </linearGradient>
      </defs>
      <line x1="0" y1="10" x2="600" y2="10" class="gl" vector-effect="non-scaling-stroke" />
      <line x1="0" y1="60" x2="600" y2="60" class="gl" vector-effect="non-scaling-stroke" />
      <line x1="0" y1="110" x2="600" y2="110" class="gl" vector-effect="non-scaling-stroke" />
      <rect v-if="banda" :x="banda.x" y="0" :width="banda.w" height="120" :style="{ fill: banda.color }" opacity="0.28" />
      <path v-if="area" :d="area" :fill="`url(#${gid})`" />
      <path v-if="linea" :d="linea" class="ln" :style="{ stroke: color }" vector-effect="non-scaling-stroke" />
    </svg>
    <div class="probe" :style="sonda.estilo">
      <i :style="sonda.punto"></i>
      <span class="tip" :style="sonda.tip">{{ sonda.texto }}</span>
    </div>
  </div>
</template>
