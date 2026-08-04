<script setup>
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
</script>

<template>
  <div class="vacio">
    <div class="icono">
      <svg width="30" height="30" viewBox="0 0 24 24"><path d="M12 2l2.6 5.4 5.9.9-4.3 4.1 1 5.9L12 15.4 6.8 18.3l1-5.9L3.5 8.3l5.9-.9z" fill="#0D0714"/></svg>
    </div>
    <h3>{{ t('empty.title') }}</h3>
    <p>{{ t('empty.subtitle') }}</p>
  </div>
</template>

<style scoped>
.vacio {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  background: #241633;
  border: 2.5px dashed #3A2C52;
  border-radius: 14px;
  text-align: center;
}
.icono {
  width: 60px;
  height: 60px;
  border-radius: 16px;
  background: #E8A93E;
  border: 2.5px solid #0D0714;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  transform: rotate(-4deg);
  box-shadow: 3px 3px 0px #0D0714;
  animation: flotar 3s ease-in-out infinite;
}
@keyframes flotar {
  0%, 100% { transform: rotate(-4deg) translateY(0); }
  50% { transform: rotate(-4deg) translateY(-6px); }
}
h3 {
  font-size: 18px;
  font-weight: 800;
  color: #F5EAD3;
  margin-bottom: 6px;
}
p {
  font-size: 13px;
  color: #8A7AA8;
  max-width: 280px;
  line-height: 1.6;
}
</style>
