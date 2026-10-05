<script setup>
import { computed, ref, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useServiciosStore } from '../stores/servicios'
import { useIncidentesStore } from '../stores/incidentes'
import { useUiStore } from '../stores/ui'
import { DEMO, API_URL } from '../config'
import ServiceRow from '../components/ServiceRow.vue'
import ActualizadoHace from '../components/ActualizadoHace.vue'
import FleetCard from '../components/FleetCard.vue'
import IncidentList from '../components/IncidentList.vue'
import ServiceDetailDialog from '../components/ServiceDetailDialog.vue'
import ServiceFormModal from '../components/ServiceFormModal.vue'
import DeleteConfirmModal from '../components/DeleteConfirmModal.vue'

const { t } = useI18n()
const store = useServiciosStore()
const incidentes = useIncidentesStore()
const ui = useUiStore()

const guardando = ref(false)
const errorForm = ref('')

const esProblema = (s) => s.estado === 'down' || s.estado === 'degraded'
const nombrePrimero = (estado) => store.lista.find((s) => s.estado === estado)?.nombre

/* ---------- Titular y resumen ---------- */
const titular = computed(() => {
  const r = store.resumen
  if (!store.cargado) return t('headline.loading')
  if (store.errorCarga) return t('headline.error')
  if (!r.total) return t('headline.empty')
  if (r.down) return r.down === 1 ? t('headline.oneDown', { name: nombrePrimero('down') }) : t('headline.manyDown', { n: r.down })
  if (r.degraded) return r.degraded === 1 ? t('headline.oneSlow', { name: nombrePrimero('degraded') }) : t('headline.manySlow', { n: r.degraded })
  if (r.pending === r.total) return t('headline.waiting')
  return t('headline.allUp')
})

// La parte «Actualizado hace N s» cambia cada segundo: vive en <ActualizadoHace> para que no se repinte toda la vista.
const resumenLinea = computed(() => t('headline.of', { up: store.resumen.up, total: store.resumen.total }))

/* ---------- Lista ---------- */
const FILTROS = ['all', 'issues', 'pinned']
const LAYOUTS = ['list', 'grid']

const visibles = computed(() =>
  store.ordenados.filter((s) => ui.filtro === 'all' || (ui.filtro === 'issues' && esProblema(s)) || (ui.filtro === 'pinned' && s.anclado))
)
const atencion = computed(() => visibles.value.filter(esProblema))
const resto = computed(() => visibles.value.filter((s) => !esProblema(s)))
const conteo = computed(() => ({
  all: store.lista.length,
  issues: store.lista.filter(esProblema).length,
  pinned: store.lista.filter((s) => s.anclado).length,
}))

// En el mosaico el servicio abierto se muestra en un cuadro de detalle; en la lista, desplegado en su fila.
const servicioAbierto = computed(() => (ui.layout === 'grid' && ui.abiertoId != null ? store.servicios[ui.abiertoId] ?? null : null))

function editarDesdeDetalle(servicio) {
  ui.abiertoId = null
  ui.editando = servicio
}
function eliminarDesdeDetalle(servicio) {
  ui.abiertoId = null
  ui.eliminando = servicio
}

function alternar(id) {
  ui.abiertoId = ui.abiertoId === id ? null : id
}

// Clic en un segmento de la franja: abre ese servicio en la lista y lo hace parpadear.
async function enfocar(id) {
  ui.filtro = 'all'
  ui.abiertoId = id
  if (ui.layout === 'grid') return // en el mosaico se abre el cuadro de detalle
  await nextTick()
  const fila = document.getElementById(`svc-${id}`)
  if (!fila) return
  fila.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  fila.classList.add('pulse')
  setTimeout(() => fila.classList.remove('pulse'), 1300)
}

/* ---------- Altas, ediciones y bajas ---------- */
const formAbierto = computed(() => ui.agregarAbierto || !!ui.editando)

function cerrarForm() {
  ui.agregarAbierto = false
  ui.editando = null
  errorForm.value = ''
}

async function guardar({ id, nombre, url }) {
  guardando.value = true
  errorForm.value = ''
  try {
    if (id) await store.actualizarServicio(id, nombre, url)
    else await store.agregarServicio(nombre, url)
    cerrarForm()
  } catch {
    errorForm.value = t('form.addError')
  } finally {
    guardando.value = false
  }
}

async function confirmarEliminacion() {
  const id = ui.eliminando.id
  ui.eliminando = null
  if (ui.abiertoId === id) ui.abiertoId = null
  await store.eliminarServicio(id)
}

function reintentar() {
  store.cargado = false
  store.cargarEstadoInicial()
}
</script>

<template>
  <div id="v-panel" class="vista">
    <section class="band">
      <h1 id="h1" aria-live="polite">{{ titular }}</h1>
      <p id="subline" class="subline">
        <template v-if="store.errorCarga">{{ t('headline.errorSub') }}</template>
        <template v-else-if="!store.resumen.total">{{ t('headline.emptySub') }}</template>
        <template v-else>{{ resumenLinea }} · <ActualizadoHace /></template>
      </p>
      <div v-if="store.lista.length" id="strip" class="strip">
        <button
          v-for="s in store.ordenados"
          :key="s.id"
          type="button"
          class="seg"
          :class="s.estado ?? 'none'"
          data-act="focus"
          :title="`${s.nombre} · ${t('status.' + (s.estado ?? 'none'))}`"
          :aria-label="`${t('strip.view')} ${s.nombre}: ${t('status.' + (s.estado ?? 'none'))}`"
          @click="enfocar(s.id)"
        ></button>
      </div>
    </section>

    <main class="grid">
      <section id="c-svc" class="card">
        <div class="card-h">
          <h2>{{ t('list.title') }}</h2>
          <div class="filters">
            <button v-for="f in FILTROS" :key="f" type="button" class="f" :data-filter="f" :aria-pressed="ui.filtro === f" @click="ui.filtro = f">
              {{ t('filter.' + f) }} <small>{{ conteo[f] }}</small>
            </button>
          </div>
          <div class="filters lay-sel" role="group" :aria-label="t('layout.label')">
            <button v-for="l in LAYOUTS" :key="l" type="button" class="f" :data-layout="l" :aria-pressed="ui.layout === l" @click="ui.fijarLayout(l)">
              {{ t('layout.' + l) }}
            </button>
          </div>
        </div>

        <div class="scroll">
          <div class="list" :class="{ mosaico: ui.layout === 'grid' }">
            <div class="cols" aria-hidden="true">
              <span></span><span>{{ t('list.service') }}</span><span>{{ t('list.history') }}</span><span class="r">{{ t('list.now') }}</span><span class="r">p95</span>
            </div>

            <!-- Cargando -->
            <template v-if="!store.cargado">
              <div v-for="n in 4" :key="n" class="skeleton"></div>
            </template>

            <!-- No se pudo conectar con el servidor -->
            <div v-else-if="store.errorCarga" class="empty" role="alert">
              <p>{{ t('error.body', { url: API_URL }) }}</p>
              <div class="fila-botones">
                <button type="button" class="btn" @click="reintentar">{{ t('error.retry') }}</button>
                <a v-if="!DEMO" class="btn primary" href="?demo">{{ t('error.demo') }}</a>
              </div>
            </div>

            <!-- Aún no hay servicios -->
            <div v-else-if="!store.lista.length" class="empty">
              <p>{{ t('list.empty') }}</p>
              <button type="button" class="btn primary" @click="ui.agregarAbierto = true">{{ t('form.add') }}</button>
            </div>

            <!-- Lista -->
            <template v-else>
              <p v-if="!visibles.length" class="empty">{{ t('list.emptyFilter') }}</p>

              <template v-if="atencion.length">
                <div class="grp">{{ t('list.attention') }} · {{ atencion.length }}</div>
                <ServiceRow
                  v-for="(s, i) in atencion"
                  :key="s.id"
                  :servicio="s"
                  :indice="i"
                  :desde="incidentes.inicioActivo[s.nombre] ?? null"
                  :abierto="ui.layout === 'list' && ui.abiertoId === s.id"
                  :modal="ui.layout === 'grid'"
                  @alternar="alternar(s.id)"
                  @pedir-editar="ui.editando = $event"
                  @pedir-eliminar="ui.eliminando = $event"
                  @alternar-anclado="store.alternarAnclado($event)"
                />
              </template>

              <template v-if="resto.length">
                <div v-if="atencion.length" class="grp">{{ t('list.operational') }} · {{ resto.length }}</div>
                <ServiceRow
                  v-for="(s, i) in resto"
                  :key="s.id"
                  :servicio="s"
                  :indice="atencion.length + i"
                  :abierto="ui.layout === 'list' && ui.abiertoId === s.id"
                  :modal="ui.layout === 'grid'"
                  @alternar="alternar(s.id)"
                  @pedir-editar="ui.editando = $event"
                  @pedir-eliminar="ui.eliminando = $event"
                  @alternar-anclado="store.alternarAnclado($event)"
                />
              </template>
            </template>
          </div>
        </div>
      </section>

      <div class="side">
        <FleetCard />
        <IncidentList />
      </div>
    </main>

    <ServiceDetailDialog :servicio="servicioAbierto" @cerrar="ui.abiertoId = null" @anclar="store.alternarAnclado($event)" @editar="editarDesdeDetalle" @eliminar="eliminarDesdeDetalle" />
    <ServiceFormModal :abierto="formAbierto" :servicio="ui.editando" :guardando="guardando" :error="errorForm" @guardar="guardar" @cancelar="cerrarForm" />
    <DeleteConfirmModal :servicio="ui.eliminando" @confirmar="confirmarEliminacion" @cancelar="ui.eliminando = null" />
  </div>
</template>
