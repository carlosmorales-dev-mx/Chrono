<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCountUp } from '../composables/useCountUp'

const props = defineProps({ servicios: { type: Array, required: true } })
const { t } = useI18n()

const total = computed(() => props.servicios.length)
const arribaCount = computed(() => props.servicios.filter((s) => s.estado === 'up').length)
const degradedCount = computed(() => props.servicios.filter((s) => s.estado === 'degraded').length)
const downCount = computed(() => props.servicios.filter((s) => s.estado === 'down').length)
const uptimePct = computed(() => (total.value ? Math.round((arribaCount.value / total.value) * 1000) / 10 : 100))

const arribaMostrado = useCountUp(arribaCount)
const degradedMostrado = useCountUp(degradedCount)
const downMostrado = useCountUp(downCount)
const uptimeMostrado = useCountUp(uptimePct)
</script>

<template>
  <div class="resumen">
    <div class="stat">
      <span class="stat-num c-up">{{ arribaMostrado }}</span>
      <span class="stat-label">{{ t('summary.operational') }}</span>
    </div>
    <div class="stat">
      <span class="stat-num c-degraded">{{ degradedMostrado }}</span>
      <span class="stat-label">{{ t('summary.degraded') }}</span>
    </div>
    <div class="stat">
      <span class="stat-num c-down">{{ downMostrado }}</span>
      <span class="stat-label">{{ t('summary.down') }}</span>
    </div>
    <div class="separador"></div>
    <div class="stat-hero">
      <span class="stat-hero-num">{{ uptimeMostrado }}<small>%</small></span>
      <span class="stat-label">{{ t('summary.uptime') }}</span>
    </div>
  </div>
</template>

<style scoped>
/* Ya NO ocupa todo el ancho pegada a la izquierda -- se recorre a la
   derecha, del mismo lado donde vive el reloj/ES-EN, quedando como
   un bloque compacto en vez de una barra que estira todo el header. */
.resumen {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 32px;
  background: #241633;
  border: 2.5px solid #0D0714;
  border-radius: 14px;
  padding: 16px 24px;
  margin: 0 auto 22px;
  width: fit-content;
  box-shadow: 3px 3px 0px #0D0714;
}
.separador {
  width: 2px;
  height: 28px;
  background: #3A2C52;
  flex-shrink: 0;
}
.stat {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.stat-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 21px;
  font-weight: 700;
  color: #F5EAD3;
  line-height: 1.1;
}
.stat-num.c-up { color: #6FE3C4; }
.stat-num.c-degraded { color: #E8A93E; }
.stat-num.c-down { color: #F26B7A; }
.stat-label {
  font-size: 10px;
  font-weight: 600;
  color: #8A7AA8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.stat-hero {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.stat-hero-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 26px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #6FE3C4 0%, #E8A93E 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.stat-hero-num small {
  font-size: 13px;
  font-weight: 600;
}

@media (max-width: 640px) {
  .resumen {
    width: 100%;
    box-sizing: border-box;
    margin: 0 0 20px 0;
    gap: 0;
    padding: 14px 12px;
    justify-content: space-around;
  }
  .separador { display: none; }
  .stat, .stat-hero { align-items: center; text-align: center; }
  .stat-num { font-size: 19px; }
  .stat-hero-num { font-size: 23px; }
  .stat-label { font-size: 9px; }
}
</style>
