// Un solo punto de entrada: según la configuración usa el backend real o el demo.
//
// Cada implementación se descarga SOLO cuando hace falta (import dinámico): quien usa el backend real
// no baja el código de la demo (datos simulados) y quien ve la demo no baja axios.
import { DEMO } from '../config'

let cargando = null
const modulo = () => (cargando = cargando || (DEMO ? import('./demo') : import('./real')))

const llamar = (nombre) => (...args) => modulo().then((m) => m[nombre](...args))

export default {
  getEstadoActual: llamar('getEstadoActual'),
  getHistorial: llamar('getHistorial'),
  getPercentiles: llamar('getPercentiles'),
  getIncidentes: llamar('getIncidentes'),
  crearServicio: llamar('crearServicio'),
  editarServicio: llamar('editarServicio'),
  anclarServicio: llamar('anclarServicio'),
  borrarServicio: llamar('borrarServicio'),

  // El WebSocket no puede esperar al módulo para devolver algo: entrega un manejador de inmediato
  // (estado 0 = «conectando») y lo conecta en cuanto el módulo está cargado.
  abrirSocket(opciones) {
    let socket = null
    let cerrado = false
    modulo()
      .then((m) => {
        if (!cerrado) socket = m.abrirSocket(opciones)
      })
      .catch(() => opciones.onClose()) // si el módulo no carga, el store reintenta como con cualquier desconexión
    return {
      get readyState() {
        return socket ? socket.readyState : 0
      },
      close() {
        cerrado = true
        if (socket) socket.close()
      },
    }
  },
}
