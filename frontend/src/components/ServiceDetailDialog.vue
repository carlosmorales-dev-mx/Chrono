<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { textoMs } from '../utils/format'
import ServiceDetail from './ServiceDetail.vue'

// Detalle de un servicio en el MOSAICO. Se abre en un cuadro centrado (<dialog>), así la cuadrícula
// nunca se reacomoda ni el detalle queda fuera de la pantalla. En la lista el detalle se despliega en la fila.
const props = defineProps({ servicio: { type: Object, default: null } })
const emit = defineEmits(['cerrar', 'anclar', 'editar', 'eliminar'])

const { t } = useI18n()
const el = ref(null)

const estado = computed(() => props.servicio?.estado ?? 'none')
const host = computed(() => {
  try {
    return new URL(props.servicio.url).host
  } catch {
    return props.servicio?.url ?? ''
  }
})

function sincronizar() {
  if (!el.value) return
  if (props.servicio && !el.value.open) el.value.showModal()
  if (!props.servicio && el.value.open) el.value.close()
}
watch(() => props.servicio, sincronizar, { flush: 'post' })
onMounted(sincronizar)

// Un clic en el fondo oscuro (el propio <dialog>, que no tiene relleno) cierra el cuadro.
const alClic = (e) => e.target === el.value && emit('cerrar')
</script>

<template>
  <dialog ref="el" class="dlg-detalle" aria-labelledby="dlg-det-titulo" @cancel.prevent="emit('cerrar')" @click="alClic">
    <div v-if="servicio" class="dd">
      <header class="dd-cab" :class="estado">
        <div>
          <h2 id="dlg-det-titulo"><span class="dot" aria-hidden="true"></span>{{ servicio.nombre }}</h2>
          <a class="dd-host" :href="servicio.url" target="_blank" rel="noopener noreferrer">{{ host }}</a>
        </div>
        <button type="button" class="ib" data-dlg="close" :aria-label="t('detail.close')" :title="t('detail.close')" @click="emit('cerrar')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18" /><path d="M6 6l12 12" /></svg>
        </button>
      </header>

      <div class="dd-fila">
        <span class="chip" :class="estado">{{ t('status.' + estado) }}</span>
        <span class="dd-ahora">{{ textoMs(servicio.latencia_ms) }}</span>
      </div>

      <ServiceDetail :servicio="servicio" />

      <div class="dlg-actions dd-acciones">
        <div class="dd-izq">
          <button type="button" class="btn" :aria-pressed="!!servicio.anclado" @click="emit('anclar', servicio.id)">{{ t(servicio.anclado ? 'row.unpin' : 'row.pin') }}</button>
          <button type="button" class="btn" @click="emit('editar', servicio)">{{ t('row.edit') }}</button>
        </div>
        <button type="button" class="btn" @click="emit('eliminar', servicio)">{{ t('row.delete') }}</button>
      </div>
    </div>
  </dialog>
</template>
