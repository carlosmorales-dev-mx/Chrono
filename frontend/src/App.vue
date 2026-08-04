<script setup>
import { onMounted, computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useServiciosStore } from './stores/servicios'
import { useDynamicTitle } from './composables/useDynamicTitle'
import ServiceCard from './components/ServiceCard.vue'
import SummaryBar from './components/SummaryBar.vue'
import EmptyState from './components/EmptyState.vue'
import ChronoMascot from './components/ChronoMascot.vue'
import ChartModal from './components/ChartModal.vue'
import IncidentTimeline from './components/IncidentTimeline.vue'
import DeleteConfirmModal from './components/DeleteConfirmModal.vue'
import EditServiceModal from './components/EditServiceModal.vue'
import NotificationBell from './components/NotificationBell.vue'

const store = useServiciosStore()
const { t, locale } = useI18n()

const nuevoNombre = ref('')
const nuevaUrl = ref('')
const guardando = ref(false)
const error = ref('')
const servicioExpandido = ref(null)
const servicioAEliminar = ref(null)
const servicioAEditar = ref(null)
const panelIncidentesAbierto = ref(false)

async function confirmarEliminacion() {
  await store.eliminarServicio(servicioAEliminar.value.id)
  servicioAEliminar.value = null
}

async function guardarEdicion({ id, nombre, url }) {
  await store.actualizarServicio(id, nombre, url)
  servicioAEditar.value = null
}

onMounted(async () => {
  await store.cargarEstadoInicial()
  store.conectarWebSocket()
})

// Orden por severidad: lo urgente arriba, lo sano abajo -- igual que
// cualquier status page real (Vercel, GitHub, etc.)
const ORDEN_SEVERIDAD = { down: 0, degraded: 1, null: 2, undefined: 2, up: 3 }

const listaServicios = computed(() =>
  Object.values(store.servicios).sort((a, b) => {
    if (a.anclado !== b.anclado) return a.anclado ? -1 : 1
    const diff = ORDEN_SEVERIDAD[a.estado] - ORDEN_SEVERIDAD[b.estado]
    return diff !== 0 ? diff : a.id - b.id
  })
)

const resumen = computed(() => ({
  down: listaServicios.value.filter((s) => s.estado === 'down').length,
  degraded: listaServicios.value.filter((s) => s.estado === 'degraded').length,
}))

useDynamicTitle(resumen)

async function onAgregar() {
  if (!nuevoNombre.value.trim() || !nuevaUrl.value.trim()) return
  error.value = ''
  guardando.value = true
  try {
    let url = nuevaUrl.value.trim()
    if (!url.startsWith('http')) url = 'https://' + url
    await store.agregarServicio(nuevoNombre.value.trim(), url)
    nuevoNombre.value = ''
    nuevaUrl.value = ''
  } catch (e) {
    error.value = t('form.addError')
  } finally {
    guardando.value = false
  }
}

function alternarPanelIncidentes() {
  panelIncidentesAbierto.value = !panelIncidentesAbierto.value
}

function cambiarIdioma(nuevo) {
  locale.value = nuevo
  localStorage.setItem('pulse-idioma', nuevo)
}
</script>

<template>
  <div class="pagina">
    <div class="contenedor">

      <header class="topbar">
        <div class="marca">
          <ChronoMascot />
          <div class="marca-texto">
            <span class="nombre">{{ t('app.name') }}</span>
            <span class="tagline">{{ t('app.tagline') }}</span>
          </div>
        </div>

        <div class="topbar-derecha">
          <NotificationBell @click="alternarPanelIncidentes" />
          <div class="lang-toggle">
            <span :class="{ activo: locale === 'es' }" @click="cambiarIdioma('es')">ES</span>
            <span :class="{ activo: locale === 'en' }" @click="cambiarIdioma('en')">EN</span>
          </div>
        </div>
      </header>

      <SummaryBar :servicios="listaServicios" />

      <Transition name="fade">
        <div v-if="!store.conectado" class="banner-reconexion">{{ t('status.reconnectBanner') }}</div>
      </Transition>

      <form class="form-agregar" @submit.prevent="onAgregar">
        <input v-model="nuevoNombre" :placeholder="t('form.namePlaceholder')" />
        <input v-model="nuevaUrl" :placeholder="t('form.urlPlaceholder')" />
        <button type="submit" :disabled="guardando">
          {{ guardando ? t('form.adding') : t('form.add') }}
        </button>
      </form>
      <p v-if="error" class="mensaje-error">{{ error }}</p>

      <TransitionGroup v-if="listaServicios.length" name="tarjeta" tag="div" class="grid">
        <ServiceCard
          v-for="s in listaServicios"
          :key="s.id"
          :servicio="s"
          @pedir-eliminar="servicioAEliminar = $event"
          @pedir-editar="servicioAEditar = $event"
          @expandir="servicioExpandido = $event"
          @alternar-anclado="store.alternarAnclado($event)"
        />
      </TransitionGroup>
      <div v-else class="grid">
        <EmptyState />
      </div>

    </div>

    <ChartModal :servicio="servicioExpandido" @cerrar="servicioExpandido = null" />

    <IncidentTimeline :abierto="panelIncidentesAbierto" @cerrar="panelIncidentesAbierto = false" />

    <DeleteConfirmModal
      :servicio="servicioAEliminar"
      @confirmar="confirmarEliminacion"
      @cancelar="servicioAEliminar = null"
    />

    <EditServiceModal
      :servicio="servicioAEditar"
      @guardar="guardarEdicion"
      @cancelar="servicioAEditar = null"
    />
  </div>
</template>

<style scoped>
.pagina {
  min-height: 100vh;
  width: 100%;
  background:
    radial-gradient(circle at 15% 10%, rgba(232, 169, 62, 0.08) 0%, transparent 35%),
    radial-gradient(circle at 85% 90%, rgba(111, 227, 196, 0.06) 0%, transparent 35%),
    #1A1026;
  padding: 40px clamp(20px, 5vw, 64px);
  font-family: 'Segoe UI', system-ui, sans-serif;
  box-sizing: border-box;
}
.contenedor {
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  flex-wrap: wrap;
  gap: 16px;
}
.topbar-derecha {
  display: flex;
  align-items: center;
  gap: 14px;
}

.marca {
  display: flex;
  align-items: center;
  gap: 14px;
}
.marca-texto {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}
.nombre {
  font-family: 'Sora', 'Segoe UI', sans-serif;
  font-size: 33px;
  font-weight: 800;
  color: #F5EAD3;
  letter-spacing: -0.02em;
  line-height: 1;
  background: linear-gradient(135deg, #F5EAD3 40%, #E8A93E 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.tagline {
  font-size: 13px;
  color: #8A7AA8;
  font-weight: 600;
}
.lang-toggle {
  display: flex;
  gap: 3px;
  background: #2C1F42;
  border: 2px solid #0D0714;
  border-radius: 999px;
  padding: 4px;
}
.lang-toggle span {
  font-size: 12px;
  font-weight: 700;
  padding: 6px 13px;
  border-radius: 999px;
  cursor: pointer;
  color: #8A7AA8;
  transition: all 0.15s;
}
.lang-toggle span.activo {
  background: #E8A93E;
  color: #0D0714;
}
.form-agregar {
  display: flex;
  gap: 12px;
  margin-bottom: 26px;
  flex-wrap: wrap;
}
.form-agregar input {
  flex: 1;
  min-width: 210px;
  padding: 14px 18px;
  border-radius: 12px;
  border: 2px solid #4A3468;
  background: #241633;
  color: #F5EAD3;
  font-size: 15px;
}
.form-agregar input::placeholder {
  color: #8A7AA8;
}
.form-agregar input:hover {
  border-color: #6B5D8A;
  background: #2C1F42;
}
.form-agregar input:focus {
  outline: none;
  border-color: #E8A93E;
  background: #2C1F42;
  box-shadow: 0 0 0 3px rgba(232, 169, 62, 0.15);
}
.form-agregar button {
  padding: 14px 28px;
  border-radius: 12px;
  border: 2.5px solid #0D0714;
  background: linear-gradient(135deg, #F5C56E 0%, #E8A93E 55%, #D48A2A 100%);
  color: #0D0714;
  font-weight: 800;
  font-size: 14.5px;
  cursor: pointer;
  box-shadow: 3px 3px 0px #0D0714;
  transition: transform 0.1s, box-shadow 0.1s, filter 0.15s;
}
.form-agregar button:hover:not(:disabled) {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0px #0D0714;
  filter: brightness(1.08);
}
.form-agregar button:active:not(:disabled) {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0px #0D0714;
}
.form-agregar button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.mensaje-error {
  color: #F26B7A;
  font-size: 13px;
  margin-bottom: 16px;
  font-weight: 600;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
  gap: 20px;
}
.tarjeta-enter-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.tarjeta-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
  position: absolute;
}
.tarjeta-enter-from {
  opacity: 0;
  transform: translateY(10px) scale(0.97);
}
.tarjeta-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
.tarjeta-move {
  transition: transform 0.3s ease;
}
* {
  transition: color 0.25s ease, background-color 0.25s ease, border-color 0.25s ease;
}
.banner-reconexion {
  background: #6B1E2E;
  border: 2px solid #0D0714;
  color: #F5C2CB;
  font-size: 12.5px;
  font-weight: 700;
  padding: 10px 16px;
  border-radius: 10px;
  margin-bottom: 18px;
  text-align: center;
}
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

/* ============ RESPONSIVE MÓVIL ============ */
@media (max-width: 768px) {
  .pagina {
    padding: 20px 14px;
  }
  .topbar {
    margin-bottom: 18px;
  }
  .nombre {
    font-size: 26px;
  }
  .tagline {
    font-size: 11px;
  }
  .form-agregar {
    flex-direction: column;
    gap: 10px;
  }
  .form-agregar input {
    min-width: 0;
    width: 100%;
    box-sizing: border-box;
  }
  .form-agregar button {
    width: 100%;
  }
  .grid {
    grid-template-columns: 1fr;
    gap: 14px;
  }
}

@media (max-width: 400px) {
  .topbar {
    flex-direction: column;
    align-items: flex-start;
  }
  .topbar-derecha {
    width: 100%;
    justify-content: space-between;
  }
}
</style>