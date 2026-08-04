<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import axios from 'axios'

const props = defineProps({
  servicio: { type: Object, default: null },
})
const emit = defineEmits(['cerrar'])
const { t } = useI18n()

const puntos = ref([])
const cargando = ref(false)
const svgEl = ref(null)
const indiceHover = ref(null)

watch(
  () => props.servicio,
  async (nuevo) => {
    indiceHover.value = null
    if (!nuevo) return
    cargando.value = true
    try {
      const { data } = await axios.get(`http://127.0.0.1:8001/chequeos/${nuevo.id}/historial`)
      puntos.value = data.filter((p) => p.latencia_ms !== null)
    } catch (e) {
      puntos.value = []
    } finally {
      cargando.value = false
    }
  }
)

const colorLinea = computed(() => {
  const mapa = { up: '#6FE3C4', degraded: '#E8A93E', down: '#F26B7A' }
  return mapa[props.servicio?.estado] || '#C9B8DE'
})

const minMax = computed(() => {
  if (!puntos.value.length) return { min: 0, max: 0 }
  const valores = puntos.value.map((p) => p.latencia_ms)
  return { min: Math.min(...valores), max: Math.max(...valores) }
})

const coords = computed(() => {
  if (puntos.value.length < 2) return []
  const valores = puntos.value.map((p) => p.latencia_ms)
  const max = Math.max(...valores, 1)
  const min = Math.min(...valores, 0)
  const rango = max - min || 1
  const stepX = 640 / (puntos.value.length - 1)
  return puntos.value.map((p, i) => {
    const x = i * stepX
    const y = 200 - ((p.latencia_ms - min) / rango) * 170 - 15
    return { x, y, latencia: p.latencia_ms, hora: p.creado_en }
  })
})

const pathLinea = computed(() => {
  if (coords.value.length < 2) return ''
  let d = `M${coords.value[0].x.toFixed(1)},${coords.value[0].y.toFixed(1)}`
  for (let i = 1; i < coords.value.length; i++) {
    const p0 = coords.value[i - 1]
    const p1 = coords.value[i]
    const mx = (p0.x + p1.x) / 2
    const my = (p0.y + p1.y) / 2
    d += ` Q${p0.x.toFixed(1)},${p0.y.toFixed(1)} ${mx.toFixed(1)},${my.toFixed(1)}`
  }
  return d
})

const pathArea = computed(() => {
  if (!pathLinea.value) return ''
  return `${pathLinea.value} L640,200 L0,200 Z`
})

function alMoverMouse(evento) {
  if (!svgEl.value || !coords.value.length) return
  const rect = svgEl.value.getBoundingClientRect()
  const xRelativo = ((evento.clientX - rect.left) / rect.width) * 640
  let masCercano = 0
  let distanciaMin = Infinity
  coords.value.forEach((c, i) => {
    const d = Math.abs(c.x - xRelativo)
    if (d < distanciaMin) {
      distanciaMin = d
      masCercano = i
    }
  })
  indiceHover.value = masCercano
}

function alSalirMouse() {
  indiceHover.value = null
}

const puntoActivo = computed(() => (indiceHover.value !== null ? coords.value[indiceHover.value] : null))

function etiquetaHora(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
function etiquetaFechaHora(iso) {
  const d = new Date(iso)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>

<template>
  <Transition name="modal">
    <div v-if="servicio" class="overlay" @click.self="emit('cerrar')">
      <div class="modal">
        <button class="btn-cerrar" @click="emit('cerrar')">✕</button>

        <div class="modal-header">
          <strong>{{ servicio.nombre }}</strong>
          <span class="rango">{{ t('metrics.history') }}</span>
        </div>

        <div v-if="cargando" class="cargando">···</div>
        <div v-else-if="!pathLinea" class="sin-datos-grande">{{ t('metrics.noHistory') }}</div>
        <template v-else>
          <div class="eje-y">
            <span>{{ minMax.max }}ms</span>
            <span>{{ Math.round((minMax.max + minMax.min) / 2) }}ms</span>
            <span>{{ minMax.min }}ms</span>
          </div>

          <div class="chart-area">
            <Transition name="tooltip">
              <div
                v-if="puntoActivo"
                class="tooltip"
                :style="{ left: (puntoActivo.x / 640 * 100) + '%' }"
              >
                <div class="tooltip-hora">{{ etiquetaFechaHora(puntoActivo.hora) }}</div>
                <div class="tooltip-latencia" :style="{ color: colorLinea }">{{ puntoActivo.latencia }}ms</div>
              </div>
            </Transition>

            <svg
              ref="svgEl"
              viewBox="0 0 640 200"
              class="chart-grande"
              preserveAspectRatio="none"
              @mousemove="alMoverMouse"
              @mouseleave="alSalirMouse"
            >
              <line x1="0" y1="15" x2="640" y2="15" class="grid-h" />
              <line x1="0" y1="100" x2="640" y2="100" class="grid-h" />
              <line x1="0" y1="185" x2="640" y2="185" class="grid-h" />

              <path :d="pathArea" :style="{ fill: colorLinea }" class="area" />
              <path :d="pathLinea" class="linea-ink" />
              <path :d="pathLinea" :style="{ stroke: colorLinea }" class="linea-color" />

              <line
                v-if="puntoActivo"
                :x1="puntoActivo.x" y1="15" :x2="puntoActivo.x" y2="185"
                class="crosshair"
              />
              <circle
                v-if="puntoActivo"
                :cx="puntoActivo.x" :cy="puntoActivo.y" r="5"
                class="punto-ink"
              />
              <circle
                v-if="puntoActivo"
                :cx="puntoActivo.x" :cy="puntoActivo.y" r="3"
                :style="{ fill: colorLinea }"
              />
            </svg>
          </div>

          <div class="eje-x">
            <span>{{ etiquetaHora(puntos[0].creado_en) }}</span>
            <span>{{ etiquetaHora(puntos[Math.floor(puntos.length / 2)].creado_en) }}</span>
            <span>{{ etiquetaHora(puntos[puntos.length - 1].creado_en) }}</span>
          </div>
          <p class="hint">{{ t('metrics.hoverHint') }}</p>
        </template>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(13, 7, 20, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 20px;
}
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-active .modal, .modal-leave-active .modal { transition: transform 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .modal, .modal-leave-to .modal { transform: scale(0.95) translateY(10px); }
.modal {
  width: min(720px, 100%);
  background: #241633;
  border: 3px solid #0D0714;
  border-radius: 16px;
  padding: 26px 30px;
  position: relative;
  box-shadow: 6px 6px 0px #0D0714;
}
.btn-cerrar {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: 2px solid #0D0714;
  background: #3A2C52;
  color: #C9B8DE;
  cursor: pointer;
  font-size: 13px;
}
.modal-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 20px;
}
.modal-header strong {
  font-size: 20px;
  color: #F5EAD3;
}
.rango {
  font-size: 12px;
  color: #8A7AA8;
}
.cargando, .sin-datos-grande {
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6B5D8A;
  font-size: 14px;
}
.eje-y {
  position: absolute;
  left: 30px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 200px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11.5px;
  font-weight: 700;
  color: #D8C9EE;
}
.chart-area {
  position: relative;
  margin-left: 44px;
}
.chart-grande {
  width: 100%;
  height: 200px;
  display: block;
  cursor: crosshair;
}
.grid-h { stroke: #3A2C52; stroke-width: 1; stroke-dasharray: 3, 5; }
.area { opacity: 0.15; }
.linea-ink { fill: none; stroke: #0D0714; stroke-width: 5; stroke-linecap: round; stroke-linejoin: round; }
.linea-color { fill: none; stroke-width: 2.6; stroke-linecap: round; stroke-linejoin: round; }
.crosshair {
  stroke: #F5EAD3;
  stroke-width: 1;
  stroke-dasharray: 3, 3;
  opacity: 0.5;
}
.punto-ink {
  fill: #0D0714;
}
.tooltip {
  position: absolute;
  top: -6px;
  transform: translate(-50%, -100%);
  background: #0D0714;
  border: 2px solid #E8A93E;
  border-radius: 8px;
  padding: 6px 10px;
  font-family: 'JetBrains Mono', monospace;
  white-space: nowrap;
  pointer-events: none;
  z-index: 5;
}
.tooltip-hora {
  font-size: 9.5px;
  color: #8A7AA8;
}
.tooltip-latencia {
  font-size: 13px;
  font-weight: 700;
}
.tooltip-enter-active, .tooltip-leave-active {
  transition: opacity 0.1s ease;
}
.tooltip-enter-from, .tooltip-leave-to {
  opacity: 0;
}
.eje-x {
  display: flex;
  justify-content: space-between;
  margin-left: 44px;
  margin-top: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11.5px;
  font-weight: 600;
  color: #B8A6D9;
}
.hint {
  margin-left: 44px;
  margin-top: 10px;
  font-size: 10.5px;
  color: #6B5D8A;
  font-style: italic;
}

@media (max-width: 640px) {
  .modal {
    padding: 20px 16px;
  }
  .modal-header strong {
    font-size: 17px;
  }
  .eje-y {
    left: 16px;
    font-size: 10px;
  }
  .chart-area {
    margin-left: 34px;
  }
  .eje-x {
    margin-left: 34px;
    font-size: 10px;
  }
  .hint {
    margin-left: 34px;
    font-size: 10px;
  }
}
</style>
