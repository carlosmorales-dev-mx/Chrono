<script setup>
import { useI18n } from 'vue-i18n'

const props = defineProps({ servicio: { type: Object, default: null } })
const emit = defineEmits(['confirmar', 'cancelar'])
const { t } = useI18n()
</script>

<template>
  <Transition name="modal-alerta">
    <div v-if="servicio" class="overlay" @click.self="emit('cancelar')">
      <div class="modal">
        <div class="franja-peligro"></div>

        <div class="icono-alerta">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 9v4" />
            <path d="M10.363 3.591 2.257 17.5a1.914 1.914 0 0 0 1.636 2.87h16.214a1.914 1.914 0 0 0 1.636-2.87L13.637 3.59a1.914 1.914 0 0 0-3.274 0Z" />
            <path d="M12 16h.01" />
          </svg>
        </div>

        <h3>{{ t('confirm.deleteTitle') }}</h3>
        <p>
          {{ t('confirm.deleteBody', { name: servicio.nombre }) }}
        </p>

        <div class="acciones">
          <button class="btn-cancelar" @click="emit('cancelar')">{{ t('confirm.cancel') }}</button>
          <button class="btn-confirmar" @click="emit('confirmar')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 7h16" />
              <path d="M10 11v6" />
              <path d="M14 11v6" />
              <path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-12" />
              <path d="M9 7V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3" />
            </svg>
            {{ t('confirm.delete') }}
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
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 20px;
}

/* A propósito MUY distinto del resto: fondo casi negro con borde rojo
   grueso, en vez de la paleta púrpura/dorada habitual -- así el ojo
   entiende de inmediato "esto es una acción destructiva", sin
   confundirlo con cualquier otro modal informativo de la app. */
.modal {
  width: min(400px, 100%);
  background: #170B1F;
  border: 3px solid #F26B7A;
  border-radius: 18px;
  padding: 0 28px 26px;
  position: relative;
  box-shadow: 0 0 0 5px rgba(242, 107, 122, 0.12), 8px 8px 0px #0D0714;
  text-align: center;
  overflow: hidden;
}
.franja-peligro {
  height: 8px;
  margin: 0 -28px 22px;
  background: repeating-linear-gradient(
    -45deg, #F26B7A, #F26B7A 10px, #170B1F 10px, #170B1F 20px
  );
}
.icono-alerta {
  width: 60px;
  height: 60px;
  margin: 0 auto 16px;
  border-radius: 50%;
  background: #6B1E2E;
  border: 3px solid #F26B7A;
  color: #F26B7A;
  font-size: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: tambalear 0.5s ease-in-out;
}
@keyframes tambalear {
  0%, 100% { transform: rotate(0deg); }
  20% { transform: rotate(-8deg); }
  40% { transform: rotate(7deg); }
  60% { transform: rotate(-5deg); }
  80% { transform: rotate(3deg); }
}
h3 {
  font-size: 19px;
  font-weight: 800;
  color: #F5EAD3;
  margin-bottom: 10px;
}
p {
  font-size: 13.5px;
  color: #C9B8DE;
  line-height: 1.6;
  margin-bottom: 22px;
}
.acciones {
  display: flex;
  gap: 10px;
}
.acciones button {
  flex: 1;
  padding: 12px;
  border-radius: 11px;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: transform 0.1s, filter 0.15s;
}
.btn-cancelar {
  background: #241633;
  border: 2px solid #4A3468;
  color: #C9B8DE;
}
.btn-cancelar:hover {
  background: #2C1F42;
}
.btn-confirmar {
  background: #F26B7A;
  border: 2px solid #0D0714;
  color: #170B1F;
  box-shadow: 3px 3px 0px #0D0714;
}
.btn-confirmar:hover {
  filter: brightness(1.08);
  transform: translate(-1px, -1px);
}

.modal-alerta-enter-active {
  transition: opacity 0.2s ease;
}
.modal-alerta-leave-active {
  transition: opacity 0.15s ease;
}
.modal-alerta-enter-active .modal {
  animation: entrada-alerta 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
@keyframes entrada-alerta {
  from { transform: scale(0.85) translateY(20px); opacity: 0; }
  to { transform: scale(1) translateY(0); opacity: 1; }
}
.modal-alerta-enter-from, .modal-alerta-leave-to {
  opacity: 0;
}

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
