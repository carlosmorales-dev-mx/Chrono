import { defineStore } from 'pinia'
import { leer, guardar } from '../utils/storage'

const CLAVE_VISTA = 'chrono-vista'
const FILTROS_INC = () => ({ svc: 'all', tipo: 'all', rango: '30d' })
export const INC_PAGINA = 40

// Todo el estado de interfaz que debe sobrevivir a un cambio de pantalla, o que el tutorial necesita
// poder restablecer, vive aquí y no dentro de cada vista.
export const useUiStore = defineStore('ui', {
  state: () => ({
    // formularios y diálogos
    agregarAbierto: false,
    editando: null, // servicio que se está editando
    eliminando: null, // servicio pendiente de confirmar baja
    // panel
    filtro: 'all', // all | issues | pinned
    layout: leer(CLAVE_VISTA) === 'grid' ? 'grid' : 'list',
    abiertoId: null, // servicio con el detalle desplegado
    // incidentes
    incFiltros: FILTROS_INC(),
    incAbierto: null, // incidente con el detalle desplegado
    incLimite: INC_PAGINA,
    featId: null, // incidente elegido manualmente en la tarjeta destacada
  }),

  actions: {
    fijarLayout(valor) {
      this.layout = valor === 'grid' ? 'grid' : 'list'
      this.abiertoId = null // el detalle se muestra distinto en cada vista
      guardar(CLAVE_VISTA, this.layout)
    },

    cerrarDialogos() {
      this.agregarAbierto = false
      this.editando = null
      this.eliminando = null
    },

    reiniciarIncidentes() {
      this.incFiltros = FILTROS_INC()
      this.incAbierto = null
      this.incLimite = INC_PAGINA
      this.featId = null
    },

    // Estado "limpio" de todas las pantallas (lo usa el tutorial entre un paso y otro).
    reiniciarTodo() {
      this.cerrarDialogos()
      this.layout = 'list' // el tutorial se apoya en la lista; no se guarda como preferencia
      this.filtro = 'all'
      this.abiertoId = null
      this.reiniciarIncidentes()
    },

    instantanea() {
      return {
        layout: this.layout,
        filtro: this.filtro,
        abiertoId: this.abiertoId,
        incFiltros: { ...this.incFiltros },
        incAbierto: this.incAbierto,
        incLimite: this.incLimite,
        featId: this.featId,
      }
    },

    restaurar(s) {
      this.cerrarDialogos()
      this.layout = s.layout
      this.filtro = s.filtro
      this.abiertoId = s.abiertoId
      this.incFiltros = { ...s.incFiltros }
      this.incAbierto = s.incAbierto
      this.incLimite = s.incLimite
      this.featId = s.featId
    },
  },
})
