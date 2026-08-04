<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import axios from 'axios'
import MiniChart from './MiniChart.vue'
import { useCountUp } from '../composables/useCountUp'

const props = defineProps({ servicio: { type: Object, required: true } })
const emit = defineEmits(['pedirEliminar', 'pedirEditar', 'expandir', 'alternarAnclado'])
const { t } = useI18n()

const p95 = ref(null)
const latenciaValor = computed(() => props.servicio.latencia_ms ?? 0)
const latenciaMostrada = useCountUp(latenciaValor, 350)

onMounted(async () => {
  try {
    const { data } = await axios.get(`http://127.0.0.1:8001/chequeos/${props.servicio.id}/percentiles`)
    p95.value = data.p95
  } catch (e) {
    p95.value = null
  }
})

const colorP95 = computed(() => {
  if (!p95.value || !props.servicio.latencia_ms) return 'neutral'
  const ratio = p95.value / props.servicio.latencia_ms
  if (ratio > 2) return 'alerta'
  if (ratio > 1.3) return 'atencion'
  return 'calmo'
})

// El badge de estado solo aparece cuando hay algo que decir: degradado,
// caído, o sin datos. "Operational" repetido en 9 tarjetas idénticas es
// ruido — el punto verde ya lo comunica.
const mostrarBadge = computed(() => props.servicio.estado !== 'up')
</script>

<template>
  <div class="card" :class="[servicio.estado || 'pending', { anclado: servicio.anclado }]">
    <div class="acciones-tarjeta">
      <button
        class="btn-accion btn-anclar"
        :class="{ activo: servicio.anclado }"
        :title="t(servicio.anclado ? 'pin.unpin' : 'pin.pin')"
        @click="emit('alternarAnclado', servicio.id)"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" :fill="servicio.anclado ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 4v6l-2 4v2h10v-2l-2-4V4" />
          <path d="M12 16v5" />
          <path d="M8 4h8" />
        </svg>
      </button>
      <button class="btn-accion btn-editar" :title="t('editModal.title')" @click="emit('pedirEditar', servicio)">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
        </svg>
      </button>
      <button class="btn-accion btn-eliminar" :title="t('confirm.deleteTitle')" @click="emit('pedirEliminar', servicio)">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round">
          <path d="M18 6 6 18" />
          <path d="M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="card-header">
      <span class="dot"></span>
      <strong class="nombre" :title="servicio.nombre">{{ servicio.nombre }}</strong>
      <svg v-if="servicio.anclado" class="icono-anclado" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M9 4v6l-2 4v2h10v-2l-2-4V4" />
        <path d="M12 16v5" />
      </svg>
    </div>

    <Transition name="badge-slide">
      <span v-if="mostrarBadge" class="badge">
        <span class="badge-dot"></span>
        {{ t(`status.${servicio.estado || 'pending'}`) }}
      </span>
    </Transition>

    <MiniChart :servicio-id="servicio.id" :estado="servicio.estado" @expandir="emit('expandir', servicio)" />

    <div class="footer">
      <span class="latencia">{{ servicio.latencia_ms !== null ? latenciaMostrada : '—' }}<small v-if="servicio.latencia_ms !== null">ms</small></span>
      <span v-if="p95" class="p95-badge" :class="colorP95">
        <svg width="11" height="11" viewBox="0 0 24 24"><path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z" fill="currentColor"/></svg>
        p95 {{ p95 }}ms
      </span>
    </div>
  </div>
</template>

<style scoped>
.card {
  background: #2C1F42;
  border: 2.5px solid #0D0714;
  border-radius: 14px;
  padding: 20px 20px 18px;
  position: relative;
  box-shadow: 4px 4px 0px #0D0714;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.card:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0px #0D0714;
}
.card.up:hover { border-color: #6FE3C4; }
.card.degraded:hover { border-color: #E8A93E; }
.card.down:hover { border-color: #F26B7A; }
.card.anclado {
  border-color: #E8A93E;
  box-shadow: 4px 4px 0px #0D0714, 0 0 0 2px rgba(232, 169, 62, 0.25);
}

.acciones-tarjeta {
  position: absolute;
  top: 10px;
  right: 10px;
  display: flex;
  gap: 6px;
  z-index: 3;
}
.btn-accion {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s, transform 0.15s, border-color 0.15s;
}
.btn-anclar {
  border: 1.5px solid #4A3468;
  background: #3A2C52;
  color: #C9B8DE;
}
.btn-anclar:hover {
  background: #6B4A18;
  border-color: #E8A93E;
  color: #E8A93E;
  transform: scale(1.08);
}
.btn-anclar.activo {
  background: #6B4A18;
  border-color: #E8A93E;
  color: #E8A93E;
}
.btn-editar {
  border: 1.5px solid #2C4A66;
  background: #1B3A5C33;
  color: #7EC1F0;
}
.btn-editar:hover {
  background: #1B3A5C;
  border-color: #4A9EE0;
  color: #A8D5F5;
  transform: scale(1.08);
}
.btn-eliminar {
  border: 1.5px solid #4A3468;
  background: #3A2C52;
  color: #C9B8DE;
}
.btn-eliminar:hover {
  background: #6B1E2E;
  border-color: #F26B7A;
  color: #F26B7A;
  transform: rotate(90deg) scale(1.05);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding-right: 100px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  background: #8A7AA8;
  box-shadow: 0 0 0 3px rgba(138, 125, 168, 0.2);
}
.card.up .dot { background: #6FE3C4; box-shadow: 0 0 0 3px rgba(111, 227, 196, 0.22); }
.card.degraded .dot { background: #E8A93E; box-shadow: 0 0 0 3px rgba(232, 169, 62, 0.22); }
.card.down .dot { background: #F26B7A; box-shadow: 0 0 0 3px rgba(242, 107, 122, 0.22); }
.nombre {
  color: #F5EAD3;
  font-size: 19.5px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.icono-anclado {
  color: #E8A93E;
  flex-shrink: 0;
}
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  font-weight: 700;
  padding: 4px 11px;
  border-radius: 999px;
  border: 1.5px solid #0D0714;
  margin-bottom: 13px;
  background: #3A2C52;
  color: #C9B8DE;
}
.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  animation: latido-badge 1.5s ease-in-out infinite;
}
@keyframes latido-badge {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
.card.degraded .badge { background: #6B4A18; color: #E8A93E; }
.card.down .badge { background: #6B1E2E; color: #F26B7A; }
.badge-slide-enter-active, .badge-slide-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.badge-slide-enter-from { opacity: 0; transform: translateY(-4px); }
.badge-slide-leave-to { opacity: 0; transform: translateY(4px); }

.footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 2px dashed #3A2C52;
}
.latencia {
  font-family: 'JetBrains Mono', monospace;
  font-size: 22px;
  font-weight: 700;
  color: #E8A93E;
  display: inline-block;
}
.latencia small {
  font-size: 10px;
  font-weight: 500;
  color: #C9B8DE;
}
.p95-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11.5px;
  font-weight: 700;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1.5px solid;
}
.p95-badge.calmo {
  background: #1A6E5C33;
  color: #6FE3C4;
  border-color: #1A6E5C;
}
.p95-badge.atencion {
  background: #6B4A1833;
  color: #E8A93E;
  border-color: #6B4A18;
}
.p95-badge.alerta {
  background: #4A2D6B33;
  color: #C9A0F5;
  border-color: #6B3FA0;
  animation: alerta-pulso 1.6s ease-in-out infinite;
}
.p95-badge.neutral {
  background: #3A2C5233;
  color: #8A7AA8;
  border-color: #3A2C52;
}
@keyframes alerta-pulso {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.65; }
}

@media (max-width: 768px) {
  .card {
    padding: 16px 16px 14px;
  }
  .btn-accion {
    width: 34px;
    height: 34px;
  }
  .acciones-tarjeta {
    gap: 8px;
  }
  .card-header {
    padding-right: 130px;
  }
  .nombre {
    font-size: 17.5px;
  }
  .latencia {
    font-size: 20px;
  }
}
</style>
