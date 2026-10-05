import { createRouter, createWebHashHistory } from 'vue-router'

// Historial con hash (#/incidentes): funciona en cualquier hosting estático sin configurar redirecciones.
export default createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'panel', component: () => import('./views/PanelView.vue') },
    { path: '/incidentes', name: 'incidentes', component: () => import('./views/IncidentesView.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
