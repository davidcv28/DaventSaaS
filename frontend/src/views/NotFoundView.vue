<script setup>
// 404 de la plataforma: el catch-all del router la monta para cualquier
// path desconocido (en host de tienda el catch-all sigue redirigiendo a
// la home de la tienda). Mismo chrome que las páginas legales.
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth.store.js'
import LegalLayout from '../components/LegalLayout.vue'
import AppIcon from '../components/AppIcon.vue'

const route = useRoute()
const auth = useAuthStore()

const homeTo = computed(() => (auth.isAuthenticated ? '/dashboard' : '/'))
const homeLabel = computed(() => (auth.isAuthenticated ? 'Ir a mi panel' : 'Volver al inicio'))
</script>

<template>
  <LegalLayout title="Página no encontrada" subtitle="La dirección que buscás no existe o cambió de lugar.">
    <div class="empty nf-empty">
      <span class="empty-icon"><AppIcon name="map-pin" :size="30" /></span>
      <h3>Error 404</h3>
      <p>
        <code class="nf-path">{{ route.path }}</code> no corresponde a ninguna página de DAVENT.
        Revisá el link o volvé al inicio para seguir navegando.
      </p>
      <div class="nf-actions">
        <RouterLink class="btn" :to="homeTo"><AppIcon name="arrow-left" :size="16" /> {{ homeLabel }}</RouterLink>
        <RouterLink v-if="!auth.isAuthenticated" class="btn ghost" to="/login">Iniciar sesión</RouterLink>
      </div>
    </div>
  </LegalLayout>
</template>

<style scoped>
.nf-empty { margin-top: 8px; }
.nf-path {
  display: inline-block; padding: 2px 8px; border-radius: 6px;
  background: var(--surface); border: 1px solid var(--line);
  font-size: 12.5px; color: var(--ink); word-break: break-all;
}
.nf-actions { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }
.nf-actions .btn { width: auto; }
</style>
