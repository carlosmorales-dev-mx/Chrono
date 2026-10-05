<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'

// Sirve para agregar (servicio = null) y para editar (servicio = objeto).
const props = defineProps({
  abierto: { type: Boolean, default: false },
  servicio: { type: Object, default: null },
  guardando: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
const emit = defineEmits(['guardar', 'cancelar'])
const { t } = useI18n()

const el = ref(null)
const nombre = ref('')
const url = ref('')
const campoNombre = ref(null)

function sincronizar() {
  if (!el.value) return
  if (props.abierto && !el.value.open) {
    nombre.value = props.servicio?.nombre ?? ''
    url.value = props.servicio?.url ?? ''
    el.value.showModal()
    nextTick(() => campoNombre.value?.focus())
  }
  if (!props.abierto && el.value.open) el.value.close()
}
watch(() => props.abierto, sincronizar, { flush: 'post' })
onMounted(sincronizar)

function enviar() {
  const n = nombre.value.trim()
  let u = url.value.trim()
  if (!n || !u) return
  if (!/^https?:\/\//i.test(u)) u = 'https://' + u
  emit('guardar', { id: props.servicio?.id ?? null, nombre: n, url: u })
}
</script>

<template>
  <dialog ref="el" aria-labelledby="dlg-form-titulo" @cancel.prevent="emit('cancelar')">
    <form @submit.prevent="enviar">
      <h2 id="dlg-form-titulo">{{ t(servicio ? 'form.editTitle' : 'form.addTitle') }}</h2>

      <label for="f-name">{{ t('form.name') }}</label>
      <input id="f-name" ref="campoNombre" v-model="nombre" name="name" required autocomplete="off" :placeholder="t('form.namePlaceholder')" />

      <label for="f-url">{{ t('form.url') }}</label>
      <input id="f-url" v-model="url" name="url" required autocomplete="off" inputmode="url" :placeholder="t('form.urlPlaceholder')" />

      <p v-if="error" class="dlg-error" role="alert">{{ error }}</p>

      <div class="dlg-actions">
        <button type="button" class="btn" data-dlg="cancel" :disabled="guardando" @click="emit('cancelar')">{{ t('confirm.cancel') }}</button>
        <button type="submit" class="btn primary" :disabled="guardando">
          {{ guardando ? t('form.saving') : t(servicio ? 'form.save' : 'form.add') }}
        </button>
      </div>
    </form>
  </dialog>
</template>
