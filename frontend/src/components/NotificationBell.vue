<script setup>
import { useIncidentesStore } from '../stores/incidentes'

const store = useIncidentesStore()
const emit = defineEmits(['click'])
</script>

<template>
  <button class="reloj-btn" :class="{ alerta: store.totalActivos > 0 }" @click="emit('click')">
    <span v-if="store.totalActivos > 0" class="anillo-alerta"></span>

    <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3.5 2" />
    </svg>

    <Transition name="badge-pop">
      <span v-if="store.totalActivos > 0" class="badge">{{ store.totalActivos }}</span>
    </Transition>
  </button>
</template>

<style scoped>
.reloj-btn {
  position: relative;
  width: 40px;
  height: 40px;
  border-radius: 11px;
  border: 2px solid #0D0714;
  background: #2C1F42;
  color: #C9B8DE;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, color 0.2s, border-color 0.2s, transform 0.1s;
}
.reloj-btn:hover {
  background: #3A2C52;
  color: #F5EAD3;
  transform: translateY(-1px);
}

/* Cuando hay incidentes activos, el boton COMPLETO se tiñe de rojo --
   no solo el numero chico del badge, para que se note desde lejos sin
   tener que fijarse en detalle. */
.reloj-btn.alerta {
  background: #6B1E2E;
  border-color: #F26B7A;
  color: #F26B7A;
  animation: respirar-alerta 2s ease-in-out infinite;
}
.reloj-btn.alerta:hover {
  background: #7A2536;
}
@keyframes respirar-alerta {
  0%, 100% { box-shadow: 0 0 0 0 rgba(242, 107, 122, 0.35); }
  50% { box-shadow: 0 0 0 6px rgba(242, 107, 122, 0); }
}

.anillo-alerta {
  position: absolute;
  inset: -4px;
  border-radius: 13px;
  border: 2px solid #F26B7A;
  opacity: 0;
  animation: expandir-anillo 1.8s ease-out infinite;
}
@keyframes expandir-anillo {
  0% { transform: scale(0.9); opacity: 0.7; }
  100% { transform: scale(1.25); opacity: 0; }
}

.badge {
  position: absolute;
  top: -7px;
  right: -7px;
  min-width: 19px;
  height: 19px;
  padding: 0 5px;
  border-radius: 999px;
  background: #F26B7A;
  border: 2px solid #0D0714;
  color: #170B1F;
  font-size: 10px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}
.badge-pop-enter-active {
  animation: pop-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
@keyframes pop-in {
  from { transform: scale(0); }
  to { transform: scale(1); }
}
</style>
