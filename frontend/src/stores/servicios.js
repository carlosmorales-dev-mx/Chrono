import { defineStore } from 'pinia'
import api from '../api'
import { REFRESCO_HISTORIAL_MS } from '../config'

const GRAVEDAD = { down: 0, degraded: 1, null: 2, up: 3 }
const esProblema = (s) => s.estado === 'down' || s.estado === 'degraded'

export const useServiciosStore = defineStore('servicios', {
  state: () => ({
    servicios: {}, // { [id]: { id, nombre, url, estado, latencia_ms, anclado, ... } }
    historiales: {}, // { [id]: [{ latencia_ms, creado_en }] }
    p95: {}, // { [id]: ms }
    cargado: false, // ya se intentó la primera carga
    errorCarga: false, // la primera carga falló
    conectado: false, // WebSocket abierto
    ultimaActualizacion: Date.now(),
  }),

  getters: {
    lista: (state) => Object.values(state.servicios),

    // Primero lo que falla; dentro de cada grupo, los anclados; después orden estable.
    ordenados() {
      return [...this.lista].sort((a, b) => {
        const g = (esProblema(a) ? 0 : 1) - (esProblema(b) ? 0 : 1)
        if (g) return g
        if (!!a.anclado !== !!b.anclado) return a.anclado ? -1 : 1
        const d = GRAVEDAD[a.estado] - GRAVEDAD[b.estado]
        return d || a.id - b.id
      })
    },

    resumen() {
      const l = this.lista
      return {
        total: l.length,
        up: l.filter((s) => s.estado === 'up').length,
        degraded: l.filter((s) => s.estado === 'degraded').length,
        down: l.filter((s) => s.estado === 'down').length,
        pending: l.filter((s) => !s.estado).length,
      }
    },

    estadoGeneral() {
      const r = this.resumen
      return r.down ? 'down' : r.degraded ? 'degraded' : 'up'
    },
  },

  actions: {
    async cargarEstadoInicial() {
      try {
        const data = await api.getEstadoActual()
        const mapa = {}
        for (const item of data) mapa[item.id] = item
        this.servicios = mapa
        this.errorCarga = false
        this.ultimaActualizacion = Date.now()
        await this.cargarHistoriales()
      } catch {
        this.errorCarga = true
      } finally {
        this.cargado = true
      }
    },

    async cargarHistorial(id) {
      const [h, p] = await Promise.allSettled([api.getHistorial(id), api.getPercentiles(id)])
      if (h.status === 'fulfilled') this.historiales[id] = h.value
      if (p.status === 'fulfilled') this.p95[id] = p.value.p95
    },

    cargarHistoriales() {
      return Promise.all(Object.keys(this.servicios).map((id) => this.cargarHistorial(Number(id))))
    },

    // Refresca historial y p95 cada minuto. Es idempotente: llamarlo dos veces no duplica el temporizador.
    iniciarRefresco() {
      if (this._refresco) return
      // Con la pestaña oculta no se pide nada (al volver, App.vue refresca de inmediato).
      this._refresco = setInterval(() => {
        if (!document.hidden) this.cargarHistoriales()
      }, REFRESCO_HISTORIAL_MS)
    },

    async agregarServicio(nombre, url) {
      const data = await api.crearServicio(nombre, url)
      // Aparece enseguida como "sin datos"; el worker lo chequea en su próxima vuelta (máx. 30 s).
      this.servicios[data.id] = { ...data, estado: null, latencia_ms: null }
    },

    async actualizarServicio(id, nombre, url) {
      const data = await api.editarServicio(id, nombre, url)
      this.servicios[id] = { ...this.servicios[id], nombre: data.nombre, url: data.url }
    },

    async alternarAnclado(id) {
      // Optimista: la interfaz cambia al instante y se revierte si el servidor falla.
      const anterior = this.servicios[id]?.anclado
      this.servicios[id] = { ...this.servicios[id], anclado: !anterior }
      try {
        const data = await api.anclarServicio(id)
        this.servicios[id] = { ...this.servicios[id], anclado: data.anclado }
      } catch {
        this.servicios[id] = { ...this.servicios[id], anclado: anterior }
      }
    },

    async eliminarServicio(id) {
      await api.borrarServicio(id)
      delete this.servicios[id]
      delete this.historiales[id]
      delete this.p95[id]
    },

    aplicarChequeo(m) {
      if (m.tipo !== 'chequeo' || !this.servicios[m.servicio_id]) return
      this.servicios[m.servicio_id] = {
        ...this.servicios[m.servicio_id],
        estado: m.estado,
        codigo_http: m.codigo_http,
        latencia_ms: m.latencia_ms,
      }
      this.ultimaActualizacion = Date.now()
      const hist = this.historiales[m.servicio_id]
      if (hist) hist.push({ latencia_ms: m.latencia_ms, estado: m.estado, creado_en: new Date().toISOString() })
    },

    conectarWebSocket() {
      // Evita duplicados (pasa seguido con el hot-reload de Vite).
      if (this._socket && this._socket.readyState <= 1) return
      this._cerrando = false
      this._socket = api.abrirSocket({
        onOpen: () => {
          this.conectado = true
        },
        onMessage: (m) => this.aplicarChequeo(m),
        onClose: () => {
          this.conectado = false
          if (!this._cerrando) setTimeout(() => this.conectarWebSocket(), 3000)
        },
      })
    },

    detener() {
      this._cerrando = true
      clearInterval(this._refresco)
      this._refresco = null
      this._socket?.close()
    },
  },
})
