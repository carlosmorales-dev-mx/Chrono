import axios from 'axios'
import { API_URL, WS_URL } from '../config'

const http = axios.create({ baseURL: API_URL, timeout: 10_000 })
const datos = (r) => r.data

export const getEstadoActual = () => http.get('/chequeos/estado-actual').then(datos)
export const getHistorial = (id) => http.get(`/chequeos/${id}/historial`).then(datos)
export const getPercentiles = (id) => http.get(`/chequeos/${id}/percentiles`).then(datos)
export const getIncidentes = () => http.get('/incidentes').then(datos)
export const crearServicio = (nombre, url) => http.post('/servicios', { nombre, url }).then(datos)
export const editarServicio = (id, nombre, url) => http.put(`/servicios/${id}`, { nombre, url }).then(datos)
export const anclarServicio = (id) => http.patch(`/servicios/${id}/anclar`).then(datos)
export const borrarServicio = (id) => http.delete(`/servicios/${id}`)

export function abrirSocket({ onOpen, onMessage, onClose }) {
  const socket = new WebSocket(WS_URL)
  socket.onopen = () => onOpen()
  socket.onmessage = (evento) => {
    try {
      onMessage(JSON.parse(evento.data))
    } catch {
      /* mensaje mal formado: se ignora */
    }
  }
  socket.onclose = () => onClose()
  return socket
}
