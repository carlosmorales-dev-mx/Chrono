<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useServiciosStore } from '../stores/servicios'
import { useTiempo } from '../composables/useTiempo'
import { resumenFlota, N_CUBOS, VENTANA_MS } from '../utils/metrics'
import { porcentaje } from '../utils/format'

const { t } = useI18n()
const store = useServiciosStore()
const tiempo = useTiempo()

const flota = computed(() => resumenFlota(store.lista, store.historiales))
const inicio = computed(() => tiempo.ahoraMin.value - VENTANA_MS)
const paso = VENTANA_MS / N_CUBOS

const etiqueta = (estado) => (estado === 'none' ? t('status.none') : t(`status.${estado}`))
</script>

<template>
  <section id="c-act" class="card">
    <div class="card-h"><h2>{{ t('fleet.title') }}</h2></div>

    <template v-if="flota.total">
      <div class="fleet-head">
        <div class="big">{{ flota.uptime }}<small>%</small></div>
        <div class="cap">{{ t('fleet.caption') }} · {{ t('fleet.slowDown', { s: porcentaje(flota.pctLento), d: porcentaje(flota.pctCaido) }) }}</div>
      </div>
      <div class="fleet" aria-hidden="true">
        <i v-for="(estado, k) in flota.celdas" :key="k" :class="estado" :title="`${tiempo.hora(inicio + k * paso)} · ${etiqueta(estado)}`"></i>
      </div>
      <div class="fx" aria-hidden="true">
        <span>{{ tiempo.hora(inicio) }}</span>
        <span>{{ tiempo.hora(inicio + VENTANA_MS / 2) }}</span>
        <span>{{ tiempo.hora(tiempo.ahoraMin.value) }}</span>
      </div>
    </template>
    <p v-else class="empty">{{ t('fleet.noData') }}</p>
  </section>
</template>
