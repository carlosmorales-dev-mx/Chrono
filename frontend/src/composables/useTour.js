import { reactive, ref, nextTick } from 'vue'
import router from '../router'
import i18n, { cambiarIdioma } from '../i18n'
import { DEMO } from '../config'
import { escenarioDemo } from '../api/demoControl'
import { useIncidentesStore } from '../stores/incidentes'
import { useUiStore } from '../stores/ui'
import { fijarTema, temaActual } from './useTheme'

// Estado visible del tutorial (lo pinta TourOverlay.vue).
const estado = reactive({ activo: false, idx: 0, total: 0, ocupado: false, pct: 0, n: 1, final: false })
export const tourVisto = ref(false)

let motor = null
let inicial = null // foto de la app al abrir el tutorial; se restaura al cerrarlo

const vistaActual = () => (router.currentRoute.value.name === 'incidentes' ? 'inc' : 'panel')

async function irA(vista) {
  const destino = vista === 'inc' ? '/incidentes' : '/'
  if (router.currentRoute.value.path !== destino) await router.push(destino)
  await nextTick()
}

let setEscenarioDemo = null // se carga junto con el tutorial, y solo en modo demo

// Cambia el escenario de la demo y refresca los incidentes enseguida (normalmente se consultan cada minuto).
async function escenarioTour(nombre) {
  setEscenarioDemo(nombre)
  await useIncidentesStore().cargar()
  await nextTick()
}

function snapshot() {
  inicial = {
    vista: vistaActual(),
    tema: temaActual(),
    idioma: i18n.global.locale.value,
    escenario: DEMO ? escenarioDemo.value : null,
    ui: useUiStore().instantanea(),
  }
  return inicial
}

// Cada paso arranca desde un estado limpio y conocido, sin importar qué pasó antes.
async function baseline(vista) {
  useUiStore().reiniciarTodo()
  fijarTema(inicial.tema)
  if (i18n.global.locale.value !== inicial.idioma) cambiarIdioma(inicial.idioma)
  if (DEMO && escenarioDemo.value !== 'lento') await escenarioTour('lento')
  await irA(vista)
}

async function restaurar(foto) {
  useUiStore().restaurar(foto.ui)
  fijarTema(foto.tema)
  if (i18n.global.locale.value !== foto.idioma) cambiarIdioma(foto.idioma)
  if (DEMO && foto.escenario && escenarioDemo.value !== foto.escenario) await escenarioTour(foto.escenario)
  await irA(foto.vista)
}

function alCambiarFoco() {
  nextTick(() => {
    const b = document.querySelector('#t-card [data-t="next"], #t-card [data-t="close"]')
    if (b) b.focus({ preventScroll: true })
  })
}

let cargandoMotor = null
let elementos = null // los de TourOverlay; se guardan por si se registran antes de que el motor exista

// El motor, los pasos (y la demo, si aplica) pesan lo suyo y casi nadie abre el tutorial: se descargan la
// primera vez que se pulsa «Tutorial», no al abrir la app.
function asegurar() {
  if (motor) return Promise.resolve(motor)
  cargandoMotor =
    cargandoMotor ||
    (async () => {
      const [{ crearMotor }, { PASOS }, demo] = await Promise.all([
        import('../tour/engine'),
        import('../tour/steps'),
        DEMO ? import('../api/demo') : null,
      ])
      setEscenarioDemo = demo ? demo.setEscenario : null
      // Los pasos que necesitan datos simulados (p. ej. provocar una caída) solo existen en la demo.
      const pasos = PASOS.filter((p) => DEMO || !p.soloDemo)
      estado.total = pasos.length
      motor = crearMotor({
        estado,
        pasos,
        baseline,
        snapshot,
        restaurar,
        escenario: DEMO ? escenarioTour : null,
        alCambiarFoco,
        esperarDom: nextTick,
      })
      if (elementos) motor.registrar(elementos)
      return motor
    })()
  return cargandoMotor
}

export function useTour() {
  return {
    estado,
    visto: tourVisto,
    registrar(e) {
      elementos = e
      if (motor) motor.registrar(e)
    },
    async iniciar() {
      tourVisto.value = true
      const m = await asegurar()
      m.iniciar()
    },
    accion(a) {
      if (motor) motor.accion(a)
    },
  }
}
