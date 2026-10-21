<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { storesApi, normalizeSlug, storeThemeVars, CUSTOMIZATION_DEFAULTS } from '../api/stores.api.js'
import { extractApiError } from '../api/http.js'
import AppIcon from '../components/AppIcon.vue'

// Web pública del cliente (sin auth): identidad del negocio + StoreCustomization.
// Usa su propia paleta (data-store-theme + --store-accent*): no hereda el tema
// claro/oscuro que el visitante haya elegido para el dashboard.
const route = useRoute()
const status = ref('loading') // loading | success | error
const store = ref(null)
const errorMsg = ref('')
const copied = ref(false)

const custom = computed(() => ({ ...CUSTOMIZATION_DEFAULTS, ...(store.value?.customization || {}) }))
const themeVars = computed(() => storeThemeVars(custom.value))
const initial = computed(() => (store.value?.business_name || 'T').slice(0, 1).toUpperCase())
const location = computed(() => [store.value?.city_name, store.value?.province_name].filter(Boolean).join(', '))
const whatsappUrl = computed(() => (custom.value.whatsapp ? `https://wa.me/${custom.value.whatsapp.replace(/\D/g, '')}` : ''))
const instagramUrl = computed(() => (custom.value.instagram ? `https://instagram.com/${custom.value.instagram}` : ''))

async function share() {
  try {
    await navigator.clipboard.writeText(window.location.href)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2500)
  } catch {
    // Sin clipboard disponible: el link ya está en la barra del navegador.
  }
}

onMounted(async () => {
  const slug = normalizeSlug(route.params.slug)
  try {
    store.value = await storesApi.publicStore(slug)
    status.value = 'success'
    document.title = `${store.value.business_name || 'Tienda'} · DAVENT`
  } catch (e) {
    status.value = 'error'
    errorMsg.value = extractApiError(e).nonField || 'Esta tienda no está disponible.'
  }
})
</script>

<template>
  <div class="store-page" :data-store-theme="custom.theme" :style="themeVars">
    <header class="sp-top">
      <div class="sp-top-inner">
        <span class="sp-mono sm" aria-hidden="true">{{ initial }}</span>
        <span class="sp-name">{{ store?.business_name || 'Tienda' }}</span>
      </div>
    </header>

    <div v-if="status === 'loading'" class="sp-state">
      <span class="spinner spinner-brand" aria-hidden="true"></span>
      <p>Cargando la tienda…</p>
    </div>

    <div v-else-if="status === 'error'" class="sp-state">
      <span class="sp-state-icon"><AppIcon name="store" :size="26" /></span>
      <h1>Tienda no disponible</h1>
      <p>{{ errorMsg }}</p>
    </div>

    <template v-else>
      <section class="sp-hero">
        <div class="sp-cover" aria-hidden="true"></div>
        <div class="sp-hero-body">
          <span class="sp-mono lg" aria-hidden="true">{{ initial }}</span>
          <h1>{{ store.business_name || 'Tienda' }}</h1>
          <p v-if="custom.headline" class="sp-headline">{{ custom.headline }}</p>
          <p v-if="location" class="sp-location"><AppIcon name="map-pin" :size="14" /> {{ location }}</p>
          <p v-if="custom.description" class="sp-desc">{{ custom.description }}</p>
          <div class="sp-cta">
            <a v-if="whatsappUrl" class="sp-btn" :href="whatsappUrl" target="_blank" rel="noopener">
              <AppIcon name="message-circle" :size="16" /> WhatsApp
            </a>
            <a v-if="instagramUrl" class="sp-btn ghost" :href="instagramUrl" target="_blank" rel="noopener">
              <AppIcon name="instagram" :size="16" /> Instagram
            </a>
            <button type="button" class="sp-btn ghost" @click="share">
              <AppIcon :name="copied ? 'check' : 'share-2'" :size="16" /> {{ copied ? 'Link copiado' : 'Compartir' }}
            </button>
          </div>
        </div>
      </section>

      <main class="sp-main">
        <h2 class="sp-section-title">Catálogo</h2>
        <div class="sp-empty">
          <span class="sp-empty-icon"><AppIcon name="package" :size="26" /></span>
          <strong>Todavía no hay productos publicados</strong>
          <p>Cuando el comercio cargue su catálogo, vas a poder verlo acá.</p>
        </div>
      </main>
    </template>

    <footer class="sp-foot">
      <span>Publicado con <strong>DAVENT</strong></span>
      <RouterLink to="/register">Creá tu tienda gratis</RouterLink>
    </footer>
  </div>
</template>
