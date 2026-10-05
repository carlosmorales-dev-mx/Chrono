<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTour } from '../composables/useTour'
import { DEMO } from '../config'

const { t } = useI18n()
const tour = useTour()
const s = tour.estado

const raiz = ref(null)
const foco = ref(null)
const tarjeta = ref(null)
const cursor = ref(null)
const ondas = ref(null)

onMounted(() => {
  tour.registrar({ raiz: raiz.value, foco: foco.value, tarjeta: tarjeta.value, cursor: cursor.value, ondas: ondas.value })
})

// Un solo oyente para todos los botones de la tarjeta (cada uno lleva data-t="…").
function alClic(e) {
  const boton = e.target.closest('[data-t]')
  if (boton) tour.accion(boton.dataset.t)
}
</script>

<template>
  <div id="tour" ref="raiz" popover="manual" aria-hidden="true" @click="alClic">
    <div class="shield"></div>
    <div id="t-spot" ref="foco" class="spot"></div>

    <div id="t-card" ref="tarjeta" class="tcard" :class="{ 'is-busy': s.ocupado }" role="dialog" aria-modal="true" aria-labelledby="t-title" aria-live="polite" tabindex="-1">
      <template v-if="s.activo">
        <div class="thead">
          <h2 id="t-title">{{ t(`tour.s${s.n}.t`) }}</h2>
          <button v-if="!s.final" type="button" class="tic" data-t="replay" :aria-label="t('tour.replay')" :title="t('tour.replay')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 12a9 9 0 1 0 3-6.7" /><path d="M3 4v5h5" /></svg>
          </button>
        </div>
        <p>{{ t(`tour.s${s.n}.d`) }}</p>
        <div class="tprog" aria-hidden="true"><i :style="{ width: s.pct + '%' }"></i></div>
        <div class="tfoot">
          <span class="tcount">{{ t('tour.of', { n: s.idx + 1, total: s.total }) }}</span>
          <template v-if="s.final">
            <button type="button" class="btn sm" data-t="again">{{ t('tour.again') }}</button>
            <button v-if="DEMO" type="button" class="btn sm" data-t="try">{{ t('tour.try') }}</button>
            <button type="button" class="btn primary sm" data-t="close">{{ t('tour.close') }}</button>
          </template>
          <template v-else>
            <button v-if="s.idx > 0" type="button" class="btn sm" data-t="prev">{{ t('tour.prev') }}</button>
            <button v-else type="button" class="btn sm" data-t="skip">{{ t('tour.skip') }}</button>
            <button type="button" class="btn primary sm" data-t="next">{{ t('tour.next') }}</button>
          </template>
        </div>
      </template>
    </div>

    <div id="t-cur" ref="cursor" class="cur">
      <svg viewBox="0 0 26 26" aria-hidden="true"><path d="M3 2.5v17.2l4.6-4.3 3.3 7.1 3-1.4-3.2-6.9 6.3-.5z" fill="#fff" stroke="#14172b" stroke-width="1.6" stroke-linejoin="round" /></svg>
    </div>
    <div ref="ondas"></div>
  </div>
</template>
