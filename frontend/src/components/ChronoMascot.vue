<template>
  <div class="mascota-wrapper">
    <span class="glow"></span>
    <svg width="100%" height="100%" viewBox="0 0 100 114" class="mascota">
      
      <defs>
        <!-- Filtro de sombra de calcomanía premium (más suave y orgánico) -->
        <filter id="sticker-shadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="3" stdDeviation="2" flood-color="#1a1525" flood-opacity="0.25" />
        </filter>
        
        <!-- Degradado para la sombra de suelo -->
        <radialGradient id="shadow-grad" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#1a1525" stop-opacity="0.3" />
          <stop offset="100%" stop-color="#1a1525" stop-opacity="0" />
        </radialGradient>
      </defs>

      <!-- Sombra de suelo con degradado -->
      <ellipse cx="50" cy="111.5" rx="26" ry="5" fill="url(#shadow-grad)" stroke="none" />

      <!-- Grupo principal con el estilo de calcomanía -->
      <g stroke="#1a1525" stroke-width="2.8" stroke-linejoin="round" stroke-linecap="round" filter="url(#sticker-shadow)">

        <!-- ============ HOJAS DE LAUREL ESTILIZADAS ============ -->
        <g fill="#F1C40F" stroke-width="2.6">
          <path d="M 22 34 C 12 32, 8 24, 12 16 C 18 20, 22 26, 24 32 Z"/>
          <path d="M 26 26 C 18 20, 16 10, 24 6 C 26 12, 28 18, 30 24 Z"/>
          <path d="M 34 20 C 30 12, 32 4, 40 2 C 39 8, 38 14, 38 19 Z"/>
          <path d="M 78 34 C 88 32, 92 24, 88 16 C 82 20, 78 26, 76 32 Z"/>
          <path d="M 74 26 C 82 20, 84 10, 76 6 C 74 12, 72 18, 70 24 Z"/>
          <path d="M 66 20 C 70 12, 68 4, 60 2 C 61 8, 62 14, 62 19 Z"/>
        </g>

        <!-- ============ PELO BLANCO + RAYA ============ -->
        <path d="M 27 40 C 20 24, 34 10, 50 10 C 66 10, 80 24, 73 40 C 76 48, 74 54, 70 56 L 30 56 C 26 54, 24 48, 27 40 Z" fill="#FFFFFF" stroke-width="2.8"/>
        <!-- Líneas de la raya del pelo -->
        <path d="M 50 11 C 46 15, 45 19, 46 23 M 50 11 C 54 15, 55 19, 54 23" fill="none" stroke-width="1.8" stroke="#D5D8DC"/>

        <!-- ============ ROSTRO ============ -->
        <!-- El rostro no lleva borde negro en la parte inferior para que se fusione con el bigote (más estético) -->
        <ellipse cx="50" cy="44" rx="20" ry="18" fill="#FBE2C4" stroke="none"/>
        <path d="M 30 42 A 20 18 0 0 1 70 42" fill="none" stroke="#1a1525" stroke-width="2.8"/> 

        <!-- ============ DIADEMA DORADA (Estilo griego mejorado) ============ -->
        <path d="M 28 30 C 40 23, 60 23, 72 30 L 71 37 C 60 31, 40 31, 29 37 Z" fill="#F1C40F" stroke-width="2.8"/>
        <g stroke-width="1.8" stroke="#D4AC0D" fill="none">
          <path d="M 35 31 v3 M 40 29.5 v3 M 45 29 v3 M 50 28.5 v3 M 55 29 v3 M 60 29.5 v3 M 65 31 v3"/>
        </g>

        <!-- ============ CEJAS ANGULARES ============ -->
        <path d="M 31 37 L 39 31 L 47 37 L 44 40 L 39 35 L 34 40 Z" fill="#FFFFFF" stroke-width="2.6"/>
        <path d="M 69 37 L 61 31 L 53 37 L 56 40 L 61 35 L 66 40 Z" fill="#FFFFFF" stroke-width="2.6"/>

        <!-- ============ OJOS (animación de parpadeo) ============ -->
        <g class="ojos">
          <!-- Ojos negros en forma de D -->
          <ellipse cx="41" cy="44" rx="4" ry="5.5" fill="#1a1525" stroke="none"/>
          <ellipse cx="59" cy="44" rx="4" ry="5.5" fill="#1a1525" stroke="none"/>
          <!-- Brillos blancos en los ojos -->
          <circle cx="42.5" cy="41.5" r="1.6" fill="#FFFFFF" stroke="none"/>
          <circle cx="60.5" cy="41.5" r="1.6" fill="#FFFFFF" stroke="none"/>
        </g>

        <!-- ============ NARIZ Y BOCA ============ -->
        <path d="M 48 49 Q 50 52 52 49" fill="none" stroke="#D89B6E" stroke-width="2.4" stroke-linecap="round"/>
        <!-- Lengua feliz -->
        <path d="M 44 56 C 46 62, 54 62, 56 56 Z" fill="#1a1525" stroke-width="2.4"/>
        <path d="M 47 58 C 49 56.5, 51 56.5, 53 58 C 52 60.5, 48 60.5, 47 58 Z" fill="#E74C3C" stroke="none"/>

        <!-- ============ BIGOTE IMPONENTE ============ -->
        <path d="M 50 49 C 41 47, 32 51, 28 59 C 35 56, 41 56, 45 53 C 47 55, 49 55.5, 50 55.5 C 51 55.5, 53 55, 55 53 C 59 56, 65 56, 72 59 C 68 51, 59 47, 50 49 Z" fill="#FFFFFF" stroke-width="2.6"/>

        <!-- ============ BARBA FESTONEADA (animada) ============ -->
        <g class="barba">
          <!-- Barba con puntas redondeadas tipo ola -->
          <path d="M 30 48 C 26 60, 26 72, 32 80 Q 34 84, 37 80 Q 38 86, 43 84 Q 45 90, 50 88 Q 55 90, 57 84 Q 62 86, 63 80 Q 66 84, 68 80 C 74 72, 74 60, 70 48 C 64 56, 57 60, 50 60 C 43 60, 36 56, 30 48 Z" fill="#FFFFFF" stroke-width="2.8"/>
          <!-- Sombras internas para dar volumen 3D a la barba -->
          <path d="M 38 62 C 38 70, 43 76, 50 80 C 57 76, 62 70, 62 62" fill="none" stroke="#D5D8DC" stroke-width="2" opacity="0.8" stroke-linecap="round"/>
          <path d="M 42 68 C 44 72, 46 76, 50 78 M 58 68 C 56 72, 54 76, 50 78" fill="none" stroke="#D5D8DC" stroke-width="1.8" opacity="0.5" stroke-linecap="round"/>
        </g>

        <!-- ============ TOGA + CINTURÓN CON MEANDRO ============ -->
        <!-- Toga blanca -->
        <path d="M 38 82 C 35 90, 34 98, 36 104 L 64 104 C 66 98, 65 90, 62 82 Z" fill="#FFFFFF" stroke-width="2.8"/>
        <!-- Pliegue lateral de la toga -->
        <path d="M 47 82 C 47 92, 44 98, 42 104" fill="none" stroke="#D5D8DC" stroke-width="2.5" stroke-linecap="round"/>
        
        <!-- Cinturón Meandro griego mejorado -->
        <rect x="36" y="92" width="28" height="6" fill="#F1C40F" stroke-width="2.6"/>
        <!-- Líneas interiores del meandro -->
        <path d="M 39 95 h3 v-2 h2 v4 h-3 v-2 M 47 95 h3 v-2 h2 v4 h-3 v-2 M 55 95 h3 v-2 h2 v4 h-3 v-2" fill="none" stroke-width="1.8" stroke-linecap="square" stroke="#1a1525"/>
        <!-- Borde inferior dorado de la toga -->
        <path d="M 37 101 L 63 101" fill="none" stroke="#F1C40F" stroke-width="3.5" stroke-linecap="round"/>

        <!-- ============ BRAZO IZQUIERDO (apoyado) ============ -->
        <!-- Bíceps y antebrazo -->
        <path d="M 39 84 C 30 86, 26 92, 27 97" fill="none" stroke="#FBE2C4" stroke-width="9"/>
        <!-- Puño redondeado -->
        <circle cx="27" cy="99" r="4.5" fill="#FBE2C4" stroke-width="2.6"/>
        <!-- Brazalete izquierdo -->
        <path d="M 29 90 L 35 89 M 28 93 L 34 92" fill="none" stroke="#F1C40F" stroke-width="3"/>

        <!-- ============ BRAZO DERECHO (sosteniendo el reloj) ============ -->
        <!-- Bíceps y antebrazo -->
        <path d="M 61 84 C 70 82, 75 78, 76 74" fill="none" stroke="#FBE2C4" stroke-width="9"/>
        <!-- Puño redondeado -->
        <circle cx="77" cy="73" r="4.5" fill="#FBE2C4" stroke-width="2.6"/>
        <!-- Brazalete derecho -->
        <path d="M 67 83 L 72 80 M 68 85 L 73 82" fill="none" stroke="#F1C40F" stroke-width="3"/>

        <!-- ============ RELOJ DE BOLSILLO PREMIUM (Animado) ============ -->
        <g class="reloj-pendulo">
          <!-- Cadena texturizada con eslabones -->
          <path d="M 77 76 C 80 80, 82 84, 81 87" fill="none" stroke="#F1C40F" stroke-width="3" stroke-dasharray="3 2"/>
          <rect x="79.2" y="86" width="3.6" height="3" fill="#F1C40F" stroke-width="2.5"/>
          <circle cx="81" cy="87.5" r="2.5" fill="#F1C40F" stroke-width="2.5"/>
          
          <!-- Cuerpo Dorado del reloj -->
          <circle cx="81" cy="97" r="11.5" fill="#F1C40F" stroke-width="2.8"/>
          <!-- Esfera interior del reloj -->
          <circle cx="81" cy="97" r="9.5" fill="#FCF3CF" stroke-width="2.6"/>

          <!-- Números Romanos legibles -->
          <g font-family="system-ui, sans-serif" font-weight="bold" font-size="4" fill="#1a1525" text-anchor="middle" stroke="none">
            <text x="81" y="91.5">XII</text>
            <text x="81" y="104.5">VI</text>
            <text x="73" y="98.5">IX</text>
            <text x="89" y="98.5">III</text>
          </g>
          
          <!-- Manecillas negras de reloj -->
          <g fill="none" stroke-width="2" stroke-linecap="round">
            <path d="M 81 97 L 81 92" stroke="#1a1525"/>
            <path d="M 81 97 L 86 100.5" stroke="#1a1525"/>
          </g>
          <!-- Taco central del reloj -->
          <circle cx="81" cy="97" r="2.2" fill="#1a1525" stroke="none"/>
        </g>

        <!-- ============ PIES Y SANDALIAS ============ -->
        <!-- Pie Izquierdo -->
        <path d="M 39 104 L 37 110 L 46 110 L 45 104 Z" fill="#FBE2C4" stroke-width="2.6"/>
        <!-- Pie Derecho -->
        <path d="M 55 104 L 53 110 L 62 110 L 61 104 Z" fill="#FBE2C4" stroke-width="2.6"/>
        <!-- Suela de las sandalias -->
        <path d="M 38 110 C 38 112.5, 46 112.5, 46 110 Z" fill="#1a1525" stroke="none"/>
        <path d="M 54 110 C 54 112.5, 62 112.5, 62 110 Z" fill="#1a1525" stroke="none"/>
        <!-- Tiras de la sandalia -->
        <path d="M 39 107 L 45 107 M 55 107 L 61 107" fill="none" stroke-width="2" stroke="#1a1525"/>

      </g>
    </svg>
  </div>
</template>

<style scoped>
.mascota-wrapper {
  position: relative;
  width: 74px;
  height: 84px;
  flex-shrink: 0;
  display: flex;
  justify-content: center;
  align-items: center;
}

/* 1. Resplandor Dorado (Glow divino) */
.glow {
  position: absolute;
  inset: -12px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(241, 196, 15, 0.5) 0%, transparent 70%);
  animation: pulso-glow 3.5s ease-in-out infinite;
  z-index: 0;
}
@keyframes pulso-glow {
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.18); }
}

/* 2. Animación de Flotar (Levitación divina) */
.mascota {
  position: relative;
  z-index: 1;
  display: block;
  animation: flotar 3.5s ease-in-out infinite;
}
@keyframes flotar {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-4px) rotate(0.5deg); }
}

/* 3. Parpadeo Rápido y Natural */
.ojos {
  animation: parpadear 4.2s ease-in-out infinite;
  transform-origin: 50px 44px;
}
@keyframes parpadear {
  0%, 92%, 100% { transform: scaleY(1); }
  95% { transform: scaleY(0.1); }
}

/* 4. Mecer de la Barba (Viento divino) */
.barba {
  animation: mecer-barba 3.5s ease-in-out infinite;
  transform-origin: 50px 50px;
}
@keyframes mecer-barba {
  0%, 100% { transform: rotate(0deg); }
  50% { transform: rotate(-0.8deg); }
}

/* 5. Balanceo del Reloj (Efecto Péndulo hipnótico) */
.reloj-pendulo {
  animation: balancear 3.5s ease-in-out infinite;
  transform-origin: 77px 73px;
}
@keyframes balancear {
  0%, 100% { transform: rotate(6deg); }
  50% { transform: rotate(-6deg); }
}
</style>