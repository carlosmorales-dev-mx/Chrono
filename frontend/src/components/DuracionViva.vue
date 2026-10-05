<script setup>
import { computed } from 'vue'
import { useAhora } from '../composables/useAhora'
import { useTiempo } from '../composables/useTiempo'

// Tiempo transcurrido desde `inicio`, con segundos en vivo. Es una hoja diminuta a propósito: es el ÚNICO sitio
// (junto con ActualizadoHace) que depende del reloj de 1 s, así que cada segundo se repinta solo este texto
// y no la lista de incidentes entera.
const props = defineProps({ inicio: { type: Number, required: true } })
const ahora = useAhora()
const { duracion } = useTiempo()
const texto = computed(() => duracion((ahora.value - props.inicio) / 1000))
</script>

<template>
  <span>{{ texto }}</span>
</template>
