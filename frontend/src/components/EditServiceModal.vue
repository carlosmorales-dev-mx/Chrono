<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({ servicio: { type: Object, default: null } })
const emit = defineEmits(['guardar', 'cancelar'])
const { t } = useI18n()

const nombre = ref('')
const url = ref('')
const guardando = ref(false)

watch(
  () => props.servicio,
  (nuevo) => {
    if (nuevo) {
      nombre.value = nuevo.nombre
      url.value = nuevo.url
    }
  }
)

async function confirmar() {
  if (!nombre.value.trim() || !url.value.trim()) return
  guardando.value = true
  try {
    let urlFinal = url.value.trim()
    if (!urlFinal.startsWith('http')) urlFinal = 'https://' + urlFinal
    emit('guardar', { id: props.servicio.id, nombre: nombre.value.trim(), url: urlFinal })
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <Transition name="modal-editar">
    <div v-if="servicio" class="overlay" @click.self="emit('cancelar')">
      <div class="modal">
        <div class="franja-editar"></div>

        <div class="icono-editar">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
          </svg>
        </div>

        <h3>{{ t('editModal.title') }}</h3>

        <label>{{ t('form.namePlaceholder').split(' (')[0] }}</label>
        <input v-model="nombre" type="text" :placeholder="t('form.namePlaceholder')" />

        <label>{{ t('form.urlPlaceholder').split(' (')[0] }}</label>
        <input v-model="url" type="text" :placeholder="t('form.urlPlaceholder')" />

        <div class="acciones">
          <button class="btn-cancelar" @click="emit('cancelar')" :disabled="guardando">
            {{ t('confirm.cancel') }}
          </button>
          <button class="btn-guardar" @click="confirmar" :disabled="guardando">
            {{ guardando ? t('editModal.saving') : t('editModal.save') }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(13, 7, 20, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 20px;
}

/* Paleta AZUL a proposito -- para que sea imposible confundirlo con el
   modal rojo de eliminar. Mismo lenguaje de "franja + icono redondo"
   pero en un tono completamente distinto. */
.modal {
  width: min(400px, 100%);
  background: #170B1F;
  border: 3px solid #4A9EE0;
  border-radius: 18px;
  padding: 0 28px 26px;
  position: relative;
  box-shadow: 0 0 0 5px rgba(74, 158, 224, 0.12), 8px 8px 0px #0D0714;
  overflow: hidden;
}
.franja-editar {
  height: 8px;
  margin: 0 -28px 22px;
  background: repeating-linear-gradient(
    -45deg, #4A9EE0, #4A9EE0 10px, #170B1F 10px, #170B1F 20px
  );
}
.icono-editar {
  width: 54px;
  height: 54px;
  margin: 0 auto 14px;
  border-radius: 50%;
  background: #1B3A5C;
  border: 3px solid #4A9EE0;
  color: #7EC1F0;
  display: flex;
  align-items: center;
  justify-content: center;
}
h3 {
  font-size: 18px;
  font-weight: 800;
  color: #F5EAD3;
  text-align: center;
  margin-bottom: 18px;
}
label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #7EC1F0;
  margin-top: 12px;
  margin-bottom: 5px;
}
input {
  width: 100%;
  padding: 11px 14px;
  border-radius: 10px;
  border: 2px solid #2C4A66;
  background: #14202E;
  color: #F5EAD3;
  font-size: 14px;
  box-sizing: border-box;
}
input::placeholder {
  color: #5C7A94;
}
input:focus {
  outline: none;
  border-color: #4A9EE0;
  box-shadow: 0 0 0 3px rgba(74, 158, 224, 0.18);
}
.acciones {
  display: flex;
  gap: 10px;
  margin-top: 22px;
}
.acciones button {
  flex: 1;
  padding: 12px;
  border-radius: 11px;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.1s, filter 0.15s;
}
.acciones button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.btn-cancelar {
  background: #241633;
  border: 2px solid #4A3468;
  color: #C9B8DE;
}
.btn-cancelar:hover:not(:disabled) {
  background: #2C1F42;
}
.btn-guardar {
  background: #4A9EE0;
  border: 2px solid #0D0714;
  color: #0D1B26;
  box-shadow: 3px 3px 0px #0D0714;
}
.btn-guardar:hover:not(:disabled) {
  filter: brightness(1.08);
  transform: translate(-1px, -1px);
}

.modal-editar-enter-active { transition: opacity 0.2s ease; }
.modal-editar-leave-active { transition: opacity 0.15s ease; }
.modal-editar-enter-active .modal {
  animation: entrada-editar 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
@keyframes entrada-editar {
  from { transform: scale(0.85) translateY(20px); opacity: 0; }
  to { transform: scale(1) translateY(0); opacity: 1; }
}
.modal-editar-enter-from, .modal-editar-leave-to { opacity: 0; }

@media (max-width: 480px) {
  .modal {
    padding-left: 20px;
    padding-right: 20px;
  }
  .franja-peligro, .franja-editar {
    margin-left: -20px;
    margin-right: -20px;
  }
  .acciones {
    flex-direction: column;
  }
}
</style>
