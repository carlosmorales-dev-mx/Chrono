import { defineStore } from 'pinia'
import axios from 'axios'

export const useIncidentesStore = defineStore('incidentes', {
  state: () => ({
    lista: [],
  }),

  getters: {
    activos: (state) => state.lista.filter((i) => i.activo),
    totalActivos: (state) => state.lista.filter((i) => i.activo).length,
  },

  actions: {
    async cargar() {
      try {
        const { data } = await axios.get('http://127.0.0.1:8001/incidentes')
        this.lista = data
      } catch (e) {
        this.lista = []
      }
    },
    iniciarPolling() {
      this.cargar()
      setInterval(() => this.cargar(), 60000)
    },
  },
})
