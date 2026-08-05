import { defineStore } from 'pinia'
import axios from 'axios'

const API_URL = 'http://127.0.0.1:8001'
const WS_URL = 'ws://127.0.0.1:8001/ws'

export const useServiciosStore = defineStore('servicios', {
  state: () => ({
    servicios: {}, // { [id]: { id, nombre, url, estado, latencia_ms, ... } }
    conectado: false,
  }),

  actions: {
    async cargarEstadoInicial() {
      const { data } = await axios.get(`${API_URL}/chequeos/estado-actual`)
      const mapa = {}
      for (const item of data) mapa[item.id] = item
      this.servicios = mapa
    },

    async agregarServicio(nombre, url) {
      const { data } = await axios.post(`${API_URL}/servicios`, { nombre, url })
      // Aparece de inmediato con "sin datos aun" -- el worker lo
      // chequea en su proxima vuelta (maximo 30s despues).
      this.servicios[data.id] = { ...data, estado: null, latencia_ms: null }
    },

    async actualizarServicio(id, nombre, url) {
      const { data } = await axios.put(`${API_URL}/servicios/${id}`, { nombre, url })
      this.servicios[id] = { ...this.servicios[id], nombre: data.nombre, url: data.url }
    },

    async actualizarServicio(id, nombre, url) {
      const { data } = await axios.put(`${API_URL}/servicios/${id}`, { nombre, url })
      this.servicios[id] = { ...this.servicios[id], nombre: data.nombre, url: data.url }
    },

    async alternarAnclado(id) {
      // Actualizacion OPTIMISTA: cambia la UI de inmediato, sin
      // esperar la respuesta del servidor -- antes el boton parecia
      // "no reaccionar" durante el round-trip de red, lo que llevaba
      // a un segundo clic que terminaba revirtiendo el primero.
      const valorAnterior = this.servicios[id]?.anclado
      this.servicios[id] = { ...this.servicios[id], anclado: !valorAnterior }

      try {
        const { data } = await axios.patch(`${API_URL}/servicios/${id}/anclar`)
        // Confirma con el valor real del servidor (por si acaso)
        this.servicios[id] = { ...this.servicios[id], anclado: data.anclado }
      } catch (e) {
        // Si el servidor fallo, revierte al valor anterior
        this.servicios[id] = { ...this.servicios[id], anclado: valorAnterior }
      }
    },

    async eliminarServicio(id) {
      await axios.delete(`${API_URL}/servicios/${id}`)
      delete this.servicios[id]
    },

conectarWebSocket() {
  // Evita duplicados: si ya hay una conexión abierta o conectándose,
  // no abras otra encima (pasa seguido con el hot-reload de Vite).
  if (this._socket && this._socket.readyState <= 1) return

  const socket = new WebSocket(WS_URL)
  this._socket = socket

  socket.onopen = () => {
    this.conectado = true
  }

  socket.onmessage = (evento) => {
    const mensaje = JSON.parse(evento.data)
    if (mensaje.tipo === 'chequeo' && this.servicios[mensaje.servicio_id]) {
      this.servicios[mensaje.servicio_id] = {
        ...this.servicios[mensaje.servicio_id],
        estado: mensaje.estado,
        codigo_http: mensaje.codigo_http,
        latencia_ms: mensaje.latencia_ms,
      }
    }
  }

  socket.onclose = () => {
    this.conectado = false
    setTimeout(() => this.conectarWebSocket(), 3000)
  }
},
  },
})
