import { ref, computed } from 'vue'
import { leer, guardar, borrar } from '../utils/storage'

const CLAVE = 'chrono-tema'
const tema = ref(leer(CLAVE)) // 'light' | 'dark' | null (null = seguir al sistema)

function aplicar() {
  const raiz = document.documentElement
  if (tema.value) raiz.setAttribute('data-theme', tema.value)
  else raiz.removeAttribute('data-theme')
}

/** Fija el tema explícitamente (o null para volver a seguir al sistema). Lo usa el tutorial al restaurar. */
export function fijarTema(valor) {
  tema.value = valor === 'light' || valor === 'dark' ? valor : null
  if (tema.value) guardar(CLAVE, tema.value)
  else borrar(CLAVE)
  aplicar()
}

export function temaActual() {
  return tema.value
}

export function useTheme() {
  const sistemaOscuro = () => window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
  const oscuro = computed(() => (tema.value ? tema.value === 'dark' : sistemaOscuro()))

  function alternar() {
    fijarTema(oscuro.value ? 'light' : 'dark')
  }

  aplicar()
  return { oscuro, alternar }
}
