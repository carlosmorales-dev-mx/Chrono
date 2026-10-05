<script setup>
import { ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({ servicio: { type: Object, default: null } })
const emit = defineEmits(['confirmar', 'cancelar'])
const { t } = useI18n()
const el = ref(null)

function sincronizar() {
  if (!el.value) return
  if (props.servicio && !el.value.open) el.value.showModal()
  if (!props.servicio && el.value.open) el.value.close()
}
watch(() => props.servicio, sincronizar, { flush: 'post' })
onMounted(sincronizar)
</script>

<template>
  <dialog ref="el" aria-labelledby="dlg-del-titulo" @cancel.prevent="emit('cancelar')">
    <div v-if="servicio">
      <h2 id="dlg-del-titulo">{{ t('confirm.deleteTitle') }}</h2>
      <p>{{ t('confirm.deleteBody', { name: servicio.nombre }) }}</p>
      <div class="dlg-actions">
        <button type="button" class="btn" data-dlg="cancel" @click="emit('cancelar')">{{ t('confirm.cancel') }}</button>
        <button type="button" class="btn danger" data-dlg="confirm" @click="emit('confirmar')">{{ t('confirm.delete') }}</button>
      </div>
    </div>
  </dialog>
</template>
