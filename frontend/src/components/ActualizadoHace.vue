<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useServiciosStore } from '../stores/servicios'
import { useAhora } from '../composables/useAhora'

// «Actualizado hace N s» (o «Reconectando…»). Hoja diminuta: así el panel no se repinta cada segundo.
const { t } = useI18n()
const store = useServiciosStore()
const ahora = useAhora()
const texto = computed(() =>
  store.conectado
    ? t('headline.updated', { n: Math.max(0, Math.round((ahora.value - store.ultimaActualizacion) / 1000)) })
    : t('headline.reconnecting')
)
</script>

<template>
  <span>{{ texto }}</span>
</template>
