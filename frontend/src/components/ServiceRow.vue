<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useServiciosStore } from '../stores/servicios'
import { useTiempo } from '../composables/useTiempo'
import { mediana, cubosDe } from '../utils/metrics'
import { partesMs, textoMs } from '../utils/format'
import ServiceDetail from './ServiceDetail.vue'

const props = defineProps({
  servicio: { type: Object, required: true },
  desde: { type: Number, default: null }, // inicio del incidente activo, si lo hay
  indice: { type: Number, default: 0 },
  abierto: { type: Boolean, default: false },
  modal: { type: Boolean, default: false }, // en el mosaico el detalle se abre en un cuadro, no en la fila
})
const emit = defineEmits(['alternar', 'pedirEditar', 'pedirEliminar', 'alternarAnclado'])

const { t } = useI18n()
const store = useServiciosStore()
const tiempo = useTiempo()

const estado = computed(() => props.servicio.estado ?? 'none')
const historial = computed(() => store.historiales[props.servicio.id] ?? [])
const normal = computed(() => mediana(historial.value))
const p95 = computed(() => store.p95[props.servicio.id] ?? null)

const cubos = computed(() => {
  const lista = cubosDe(historial.value, normal.value)
  const techo = Math.max(1, ...lista.map((c) => c.max))
  return lista.map((c) => ({
    estado: c.estado,
    alto: c.estado === 'down' ? 100 : c.estado === 'none' ? 0 : Math.max(16, Math.round((c.max / techo) * 100)),
    titulo: c.estado === 'none' ? '' : `${tiempo.hora(c.inicio)} · ${c.estado === 'down' ? t('status.down') : textoMs(c.max)}`,
  }))
})

const host = computed(() => {
  try {
    return new URL(props.servicio.url).host
  } catch {
    return props.servicio.url
  }
})

// Segunda línea bajo el nombre: el contexto exacto de lo que pasa, o el host si todo va bien.
const nota = computed(() => {
  const s = props.servicio
  const cuando = props.desde ? ` · ${tiempo.desde(props.desde)}` : ''
  if (s.estado === 'degraded') {
    const x = normal.value && s.latencia_ms ? (s.latencia_ms / normal.value).toFixed(1) : null
    return { clase: 'note degraded', texto: (x ? t('row.slow', { x }) : t('status.degraded')) + cuando }
  }
  if (s.estado === 'down') return { clase: 'note down', texto: t('row.noReply') + cuando }
  if (!s.estado) return { clase: 'note', texto: t('row.waiting') }
  return { clase: 'host', texto: host.value }
})

const ahora = computed(() => partesMs(props.servicio.latencia_ms))
const p95Partes = computed(() => partesMs(p95.value))
const idDetalle = computed(() => `detalle-${props.servicio.id}`)
</script>

<template>
  <article :id="`svc-${servicio.id}`" class="svc" :class="estado" :data-id="servicio.id" :style="{ '--r': indice }">
    <div class="svc-head">
      <button type="button" class="svc-main" data-act="open" :aria-expanded="modal ? undefined : abierto" :aria-controls="modal ? undefined : idDetalle" :aria-haspopup="modal ? 'dialog' : undefined" @click="emit('alternar')">
        <span class="dot" aria-hidden="true"></span>

        <span class="who">
          <span class="nm">
            <span class="t">{{ servicio.nombre }}</span>
            <svg v-if="servicio.anclado" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 4v6l-2 4v2h10v-2l-2-4V4" /><path d="M12 16v5" /><path d="M8 4h8" /></svg>
          </span>
          <span data-k="sub"><span :class="nota.clase">{{ nota.texto }}</span></span>
        </span>

        <span class="tape" data-k="tape" aria-hidden="true">
          <i v-for="(c, k) in cubos" :key="k" :class="c.estado" :style="{ '--h': c.alto + '%', '--k': k }" :title="c.titulo"></i>
        </span>

        <span class="val now" data-k="now" :data-sin="t('row.noResponse')">
          <template v-if="ahora">{{ ahora.valor }}<small>{{ ahora.unidad }}</small></template>
          <template v-else>—</template>
        </span>
        <span class="val p" data-k="p95">
          <template v-if="p95Partes">{{ p95Partes.valor }}<small>{{ p95Partes.unidad }}</small></template>
          <template v-else>—</template>
        </span>
      </button>

      <div class="svc-actions">
        <button type="button" class="ib" :class="{ on: servicio.anclado }" data-act="pin" :aria-pressed="!!servicio.anclado" :aria-label="t(servicio.anclado ? 'row.unpin' : 'row.pin')" :title="t(servicio.anclado ? 'row.unpin' : 'row.pin')" @click="emit('alternarAnclado', servicio.id)">
          <svg width="17" height="17" viewBox="0 0 24 24" :fill="servicio.anclado ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 4v6l-2 4v2h10v-2l-2-4V4" /><path d="M12 16v5" /><path d="M8 4h8" /></svg>
        </button>
        <button type="button" class="ib" data-act="edit" :aria-label="t('row.edit')" :title="t('row.edit')" @click="emit('pedirEditar', servicio)">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.1 2.1 0 0 1 3 3L12 15l-4 1z" /></svg>
        </button>
        <button type="button" class="ib del" data-act="del" :aria-label="t('row.delete')" :title="t('row.delete')" @click="emit('pedirEliminar', servicio)">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 7h16" /><path d="M10 11v6" /><path d="M14 11v6" /><path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-12" /><path d="M9 7V4h6v3" /></svg>
        </button>
      </div>
    </div>

    <ServiceDetail v-if="abierto" :id="idDetalle" :servicio="servicio" />
  </article>
</template>
