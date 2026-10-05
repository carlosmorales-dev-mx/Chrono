<script setup>
// La última "o" del logotipo es el semáforo general: gris con todo bien,
// ámbar si algo va lento, coral si algo está caído.
defineProps({ estado: { type: String, default: 'up' } })
</script>

<template>
  <span class="wm" aria-label="Chrono">Chron<span id="wm-o" class="o" :class="estado" aria-hidden="true">o</span></span>
</template>
