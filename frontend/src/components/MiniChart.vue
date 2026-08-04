<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import axios from 'axios'

const props = defineProps({
  servicioId: { type: Number, required: true },
  estado: { type: String, default: null },
})
defineEmits(['expandir'])
const { t } = useI18n()
const puntos = ref([])
const cargando = ref(true)

onMounted(async () => {
  try {
    const { data } = await axios.get(`http://127.0.0.1:8001/chequeos/${props.servicioId}/historial`)
    puntos.value = data.filter((p) => p.latencia_ms !== null)
  } catch (e) {
    puntos.value = []
  } finally {
    cargando.value = false
  }
})

const colorLinea = computed(() => {
  const mapa = { up: '#6FE3C4', degraded: '#E8A93E', down: '#F26B7A' }
  return mapa[props.estado] || '#C9B8DE'
})

const minMax = computed(() => {
  if (!puntos.value.length) return { min: 0, max: 0 }
  const valores = puntos.value.map((p) => p.latencia_ms)
  return { min: Math.min(...valores), max: Math.max(...valores) }
})

// Escala con RANGO MÍNIMO: un servicio muy estable (GitHub, PyPI)
// tiene variaciones de pocos ms -- con auto-escala pura se dibuja
// como línea plana "muerta". Forzamos que el rango visual nunca sea
// menor al 30% del promedio, así las variaciones pequeñas se ven
// como ondulación suave y honesta, no como electro plano.
function construirCoords() {
  const valores = puntos.value.map((p) => p.latencia_ms)
  const max = Math.max(...valores, 1)
  const min = Math.min(...valores, 0)
  const promedio = valores.reduce((a, b) => a + b, 0) / valores.length
  const rangoReal = max - min
  const rangoMinimo = promedio * 0.3
  let rMin = min
  let rMax = max
  if (rangoReal < rangoMinimo) {
    const centro = (max + min) / 2
    rMin = centro - rangoMinimo / 2
    rMax = centro + rangoMinimo / 2
  }
  const rango = rMax - rMin || 1
  const stepX = puntos.value.length > 1 ? 260 / (puntos.value.length - 1) : 0
  return puntos.value.map((p, i) => {
    const x = i * stepX
    const y = 58 - ((p.latencia_ms - rMin) / rango) * 48 - 5
    return [x, y]
  })
}

const pathLinea = computed(() => {
  if (puntos.value.length < 2) return ''
  const coords = construirCoords()
  let d = `M${coords[0][0].toFixed(1)},${coords[0][1].toFixed(1)}`
  for (let i = 1; i < coords.length; i++) {
    const [x0, y0] = coords[i - 1]
    const [x1, y1] = coords[i]
    const mx = (x0 + x1) / 2
    const my = (y0 + y1) / 2
    d += ` Q${x0.toFixed(1)},${y0.toFixed(1)} ${mx.toFixed(1)},${my.toFixed(1)}`
  }
  const [lx, ly] = coords[coords.length - 1]
  d += ` L${lx.toFixed(1)},${ly.toFixed(1)}`
  return d
})

const pathArea = computed(() => {
  if (!pathLinea.value || puntos.value.length < 2) return ''
  const coords = construirCoords()
  const [lx] = coords[coords.length - 1]
  return `${pathLinea.value} L${lx.toFixed(1)},58 L0,58 Z`
})
</script>

<template>
  <div v-if="pathLinea" class="chart-wrap" @click="$emit('expandir')" :title="t('metrics.hoverHint')">
    <span class="icono-expandir">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round">
        <path d="M16 4h4v4M8 20H4v-4M20 4l-6 6M4 20l6-6" />
      </svg>
    </span>

    <div class="rango-labels">
      <span class="rango-item"><small>max</small> {{ minMax.max }}ms</span>
      <span class="rango-item tenue"><small>min</small> {{ minMax.min }}ms</span>
    </div>

    <svg viewBox="0 0 260 58" class="mini-chart" preserveAspectRatio="none">
      <defs>
        <linearGradient :id="`grad-${servicioId}`" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" :stop-color="colorLinea" stop-opacity="0.35" />
          <stop offset="100%" :stop-color="colorLinea" stop-opacity="0" />
        </linearGradient>
      </defs>
      <path :d="pathArea" :fill="`url(#grad-${servicioId})`" />
      <path :d="pathLinea" class="linea-ink" />
      <path :d="pathLinea" class="linea-color" :style="{ stroke: colorLinea }" />
    </svg>
  </div>
  <div v-else-if="cargando" class="sin-datos skeleton"></div>
  <div v-else class="sin-datos">{{ t('metrics.noHistory') }}</div>
</template>

<style scoped>
.chart-wrap {
  position: relative;
  cursor: pointer;
}
.icono-expandir {
  position: absolute;
  top: -22px;
  right: 0;
  opacity: 0;
  color: #8A7AA8;
  transition: opacity 0.15s;
  z-index: 2;
}
.chart-wrap:hover .icono-expandir {
  opacity: 1;
}
.rango-labels {
  display: flex;
  justify-content: space-between;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11.5px;
  font-weight: 700;
  color: #E8DCF5;
  margin-bottom: 5px;
}
.rango-item small {
  font-size: 8.5px;
  font-weight: 600;
  color: #8A7AA8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-right: 3px;
}
.rango-item.tenue {
  opacity: 0.75;
}
.mini-chart {
  width: 100%;
  height: 58px;
  display: block;
  overflow: visible;
}
.linea-ink {
  fill: none;
  stroke: #0D0714;
  stroke-width: 5;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.linea-color {
  fill: none;
  stroke-width: 2.4;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 500;
  stroke-dashoffset: 500;
  animation: dibujar 0.9s ease-out forwards;
}
@keyframes dibujar {
  to { stroke-dashoffset: 0; }
}
.sin-datos {
  height: 58px;
  display: flex;
  align-items: center;
  font-size: 13px;
  color: #6B5D8A;
}
.skeleton {
  border-radius: 6px;
  background: linear-gradient(90deg, #2C1F42 25%, #3A2C52 50%, #2C1F42 75%);
  background-size: 200% 100%;
  animation: brillo 1.4s ease-in-out infinite;
}
@keyframes brillo {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
