import { ref, watch } from 'vue'

/**
 * Anima un numero desde su valor actual hasta uno nuevo cada vez que
 * cambia -- interpolacion lineal cuadro a cuadro con requestAnimationFrame,
 * no un simple fade. Devuelve un ref con el valor MOSTRADO en pantalla,
 * que "persigue" al valor real.
 */
export function useCountUp(valorObjetivo, duracionMs = 450) {
  const mostrado = ref(valorObjetivo.value ?? 0)

  watch(valorObjetivo, (nuevo, viejo) => {
    if (nuevo === null || nuevo === undefined) {
      mostrado.value = nuevo
      return
    }
    const inicio = viejo ?? nuevo
    const inicioTiempo = performance.now()

    function paso(ahora) {
      const progreso = Math.min((ahora - inicioTiempo) / duracionMs, 1)
      const facilitado = 1 - Math.pow(1 - progreso, 3) // ease-out cubic
      mostrado.value = Math.round(inicio + (nuevo - inicio) * facilitado)
      if (progreso < 1) requestAnimationFrame(paso)
    }
    requestAnimationFrame(paso)
  })

  return mostrado
}
