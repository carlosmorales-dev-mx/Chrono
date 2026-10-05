import { ref } from 'vue'

// Dos relojes compartidos (un solo temporizador para toda la app):
//   · ahora    -> cada 1 s. SOLO para lo que muestra segundos en vivo (DuracionViva, ActualizadoHace).
//   · ahoraMin -> cada 30 s. Para todo lo demás: «hace 3 min», cortes de rango, etiquetas de día…
//
// Todo lo que lee un reloj se vuelve a calcular y a pintar cada vez que cambia. Con un único reloj de 1 s,
// la pantalla completa se repintaba cada segundo aunque casi nada hubiera cambiado.
//
// Con la pestaña oculta el temporizador se detiene (no hay nadie mirando) y al volver se pone al día.
const ahora = ref(Date.now())
const ahoraMin = ref(Date.now())
const PASO_GRUESO_MS = 30_000

let temporizador = null
let enlazado = false

function latido() {
  const t = Date.now()
  ahora.value = t
  if (t - ahoraMin.value >= PASO_GRUESO_MS) ahoraMin.value = t
}

function iniciar() {
  if (!temporizador) temporizador = setInterval(latido, 1000)
}

function alCambiarVisibilidad() {
  if (document.hidden) {
    clearInterval(temporizador)
    temporizador = null
  } else {
    latido()
    iniciar()
  }
}

function enlazar() {
  if (enlazado) return
  enlazado = true
  document.addEventListener('visibilitychange', alCambiarVisibilidad)
  if (!document.hidden) iniciar()
}

export function useAhora() {
  enlazar()
  return ahora
}

export function useAhoraMin() {
  enlazar()
  return ahoraMin
}
