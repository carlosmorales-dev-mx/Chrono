<script setup>
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useIncidentesStore } from '../stores/incidentes'

const props = defineProps({ abierto: { type: Boolean, required: true } })
const emit = defineEmits(['cerrar'])
const { t, locale } = useI18n()
const store = useIncidentesStore()

onMounted(() => {
  store.iniciarPolling()
})

function formatoDuracion(segundos) {
  if (segundos < 60) return `${segundos}s`
  const min = Math.floor(segundos / 60)
  if (min < 60) return `${min}min`
  const horas = Math.floor(min / 60)
  return `${horas}h ${min % 60}min`
}

function tiempoRelativo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return t('incidents.justNow')
  if (diffMin < 60) return t('incidents.minutesAgo', { n: diffMin })
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return t('incidents.hoursAgo', { n: diffH })
  return new Date(iso).toLocaleDateString(locale.value === 'es' ? 'es-MX' : 'en-US', { month: 'short', day: 'numeric' })
}
</script>

<template>
  <Transition name="overlay-fade">
    <div v-if="abierto" class="overlay" @click.self="emit('cerrar')"></div>
  </Transition>

  <Transition name="drawer-slide">
    <aside v-if="abierto" class="drawer">
      <div class="drawer-header">
        <div class="titulo-grupo">
          <div class="icono-header">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 8v4" />
              <path d="M12 16h.01" />
              <circle cx="12" cy="12" r="9" />
            </svg>
          </div>
          <h2>{{ t('incidents.title') }}</h2>
        </div>
        <button class="btn-cerrar" @click="emit('cerrar')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round">
            <path d="M18 6 6 18" /><path d="M6 6l12 12" />
          </svg>
        </button>
      </div>

      <span v-if="store.totalActivos" class="contador-activos">
        {{ t('incidents.activeCount', { n: store.totalActivos }) }}
      </span>

      <div class="lista-eventos">
        <div v-if="!store.lista.length" class="sin-eventos">
          {{ t('incidents.empty') }}
        </div>

        <TransitionGroup v-else name="evento">
          <div v-for="inc in store.lista" :key="inc.id" class="evento" :class="{ activo: inc.activo }">
            <div class="evento-icono" :class="inc.estado">
              <svg v-if="inc.estado === 'down'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 9v4" /><path d="M10.363 3.591 2.257 17.5a1.914 1.914 0 0 0 1.636 2.87h16.214a1.914 1.914 0 0 0 1.636-2.87L13.637 3.59a1.914 1.914 0 0 0-3.274 0Z" /><path d="M12 16h.01" />
              </svg>
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="9" /><path d="M12 8v4" /><path d="M12 16h.01" />
              </svg>
            </div>

            <div class="evento-cuerpo">
              <div class="evento-fila-top">
                <strong>{{ inc.servicio }}</strong>
                <span class="badge-estado" :class="inc.estado">
                  {{ inc.activo ? t('incidents.ongoing') : t(`status.${inc.estado}`) }}
                </span>
              </div>
              <p class="evento-mensaje">
                {{ t(inc.estado === 'down' ? 'incidents.wentDown' : 'incidents.wentDegraded') }}
              </p>
              <div class="evento-meta">
                <span>{{ tiempoRelativo(inc.inicio) }}</span>
                <span class="punto-sep">·</span>
                <span>{{ t('incidents.duration') }}: {{ formatoDuracion(inc.duracion_seg) }}</span>
              </div>
            </div>
          </div>
        </TransitionGroup>
      </div>
    </aside>
  </Transition>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(13, 7, 20, 0.6);
  z-index: 150;
}
.overlay-fade-enter-active, .overlay-fade-leave-active {
  transition: opacity 0.25s ease;
}
.overlay-fade-enter-from, .overlay-fade-leave-to {
  opacity: 0;
}

.drawer {
  position: fixed;
  top: 0;
  right: 0;
  height: 100vh;
  width: min(420px, 92vw);
  background: #241633;
  border-left: 3px solid #0D0714;
  box-shadow: -8px 0 0 rgba(13, 7, 20, 0.15);
  z-index: 160;
  display: flex;
  flex-direction: column;
}
.drawer-slide-enter-active, .drawer-slide-leave-active {
  transition: transform 0.28s cubic-bezier(0.32, 0.72, 0, 1);
}
.drawer-slide-enter-from, .drawer-slide-leave-to {
  transform: translateX(100%);
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 22px;
  border-bottom: 2px solid #3A2C52;
  background: #2C1F42;
  flex-shrink: 0;
}
.titulo-grupo {
  display: flex;
  align-items: center;
  gap: 10px;
}
.icono-header {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: #3A2C52;
  color: #E8A93E;
  display: flex;
  align-items: center;
  justify-content: center;
}
.drawer-header h2 {
  font-size: 16px;
  font-weight: 800;
  color: #F5EAD3;
}
.btn-cerrar {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: 2px solid #0D0714;
  background: #3A2C52;
  color: #C9B8DE;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s;
}
.btn-cerrar:hover {
  background: #6B1E2E;
  color: #F26B7A;
}
.contador-activos {
  align-self: flex-start;
  margin: 16px 22px 0;
  font-size: 11px;
  font-weight: 700;
  color: #F26B7A;
  background: #6B1E2E;
  border: 1.5px solid #F26B7A;
  padding: 4px 11px;
  border-radius: 999px;
  animation: latir-contador 1.6s ease-in-out infinite;
}
@keyframes latir-contador {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.65; }
}
.lista-eventos {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
}
.sin-eventos {
  padding: 40px 22px;
  text-align: center;
  color: #6B5D8A;
  font-size: 13px;
}
.evento {
  display: flex;
  gap: 13px;
  padding: 14px 22px;
  border-bottom: 1px solid #3A2C52;
  transition: background 0.15s;
}
.evento:last-child { border-bottom: none; }
.evento:hover { background: #2C1F4260; }
.evento.activo {
  background: linear-gradient(90deg, rgba(242, 107, 122, 0.08), transparent 60%);
}
.evento-icono {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid;
}
.evento-icono.down {
  background: #6B1E2E;
  color: #F26B7A;
  border-color: #F26B7A;
}
.evento-icono.degraded {
  background: #6B4A18;
  color: #E8A93E;
  border-color: #E8A93E;
}
.evento-cuerpo { flex: 1; min-width: 0; }
.evento-fila-top {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 3px;
  flex-wrap: wrap;
}
.evento-fila-top strong {
  font-size: 13.5px;
  color: #F5EAD3;
}
.badge-estado {
  font-size: 9.5px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1.5px solid;
}
.badge-estado.degraded { background: #6B4A18; color: #E8A93E; border-color: #E8A93E; }
.badge-estado.down { background: #6B1E2E; color: #F26B7A; border-color: #F26B7A; }
.evento-mensaje {
  font-size: 12px;
  color: #C9B8DE;
  margin-bottom: 5px;
}
.evento-meta {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px;
  color: #8A7AA8;
}
.punto-sep { margin: 0 6px; opacity: 0.5; }

.evento-enter-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.evento-enter-from { opacity: 0; transform: translateX(-10px); }

@media (max-width: 480px) {
  .drawer { width: 100vw; }
}
</style>
