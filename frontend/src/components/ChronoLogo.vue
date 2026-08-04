<template>
  <div class="logo-wrapper">
    <span class="anillo-respiracion"></span>
    <div class="logo">
      <svg width="20" height="20" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="8" fill="none" stroke="#0D0714" stroke-width="2.2" />
        <circle cx="12" cy="12" r="2" fill="#0D0714" />
        <g class="orbita">
          <circle cx="12" cy="4" r="2.3" fill="#0D0714" />
        </g>
      </svg>
    </div>
  </div>
</template>

<style scoped>
/* El punto orbita el centro sin parar -- representa literalmente el
   ciclo de chequeo del worker cada 30s, no es decoracion aleatoria. */
.logo-wrapper {
  position: relative;
  width: 42px;
  height: 42px;
  flex-shrink: 0;
}
.anillo-respiracion {
  position: absolute;
  inset: -6px;
  border-radius: 16px;
  border: 2px solid #E8A93E;
  opacity: 0;
  animation: respirar 3s ease-out infinite;
}
@keyframes respirar {
  0% { transform: scale(0.85); opacity: 0.5; }
  100% { transform: scale(1.25); opacity: 0; }
}
.logo {
  position: relative;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: #E8A93E;
  border: 3px solid #0D0714;
  display: flex;
  align-items: center;
  justify-content: center;
  transform: rotate(-4deg);
  box-shadow: 3px 3px 0px #0D0714;
  transition: transform 0.2s ease;
  overflow: hidden;
}
.logo-wrapper:hover .logo {
  transform: rotate(4deg) scale(1.05);
}
.orbita {
  transform-origin: 12px 12px;
  animation: orbitar 2.4s linear infinite;
}
@keyframes orbitar {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
