import { defineStore } from 'pinia'
import api from '../api'
import { POLL_INCIDENTES_MS } from '../config'

export const useIncidentesStore = defineStore('incidentes', {
  state: () => ({
    lista: [], // tal como llega del backend
    cargado: false,
    error: false,
  }),

  getters: {
    totalActivos: (state) => state.lista.filter((i) => i.activo).length,
    hayCaidos: (state) => state.lista.some((i) => i.activo && i.estado === 'down'),
    // nombre del servicio -> inicio (ms) del incidente activo; sirve para "desde hace 3 min"
    inicioActivo: (state) => {
      const mapa = {}
      for (const i of state.lista) if (i.activo) mapa[i.servicio] = new Date(i.inicio).getTime()
      return mapa
    },
  },

  actions: {
    async cargar() {
      try {
        this.lista = await api.getIncidentes()
        this.error = false
      } catch {
        this.error = true
      } finally {
        this.cargado = true
      }
    },

    // Idempotente: abrir y cerrar vistas no acumula temporizadores.
    iniciarPolling() {
      if (this._timer) return
      this.cargar()
      this._timer = setInterval(() => {
        if (!document.hidden) this.cargar() // con la pestaña oculta no hay nadie mirando
      }, POLL_INCIDENTES_MS)
    },

    detener() {
      clearInterval(this._timer)
      this._timer = null
    },
  },
})
