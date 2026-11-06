<script setup>
// Shell de la app nativa (APK): interfaz propia, distinta del panel web.
// Solo administración de la tienda: productos, visitas, opiniones, datos
// del negocio y diseño. Navegación por tab bar inferior; el contenido es
// un <router-view> con una pantalla por sección.
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Capacitor } from '@capacitor/core'
import { env } from '../../config/env.js'
import { publicStoreUrl } from '../../api/stores.api.js'
import { useAuthStore } from '../../stores/auth.store.js'
import { useStoreStore } from '../../stores/store.store.js'
import AppIcon from '../../components/AppIcon.vue'
import BrandLogo from '../../components/BrandLogo.vue'

const router = useRouter()
const auth = useAuthStore()
const stores = useStoreStore()
const isNative = Capacitor.isNativePlatform()

onMounted(() => {
  if (stores.status === 'idle') stores.loadMine()
})

const shopName = computed(() => (
  stores.customization.display_name
  || auth.user?.profile?.business_name
  || stores.store?.slug
  || 'Mi tienda'
))
const webUrl = computed(() => (stores.store?.slug ? publicStoreUrl(stores.store.slug) : ''))
const openWeb = () => { if (webUrl.value) window.open(webUrl.value) }

const TABS = [
  { name: 'app-products', label: 'Productos', icon: 'package' },
  { name: 'app-visits', label: 'Visitas', icon: 'trending-up' },
  { name: 'app-reviews', label: 'Opiniones', icon: 'message-circle' },
  { name: 'app-business', label: 'Negocio', icon: 'store' },
  { name: 'app-design', label: 'Diseño', icon: 'palette' }
]

async function logout() {
  await auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="appshell">
    <header class="app-top">
      <div class="app-top-id">
        <BrandLogo :size="30" />
        <div class="app-top-txt">
          <strong class="app-shop">{{ shopName }}</strong>
          <button v-if="webUrl" type="button" class="app-weblink" @click="openWeb">
            Ver mi web <AppIcon name="external-link" :size="12" />
          </button>
        </div>
      </div>
      <button type="button" class="app-iconbtn" aria-label="Cerrar sesión" @click="logout">
        <AppIcon name="logout" :size="18" />
      </button>
    </header>

    <main class="app-main">
      <router-view v-slot="{ Component }">
        <component :is="Component" />
      </router-view>
    </main>

    <nav class="app-tabs" aria-label="Secciones">
      <router-link
        v-for="t in TABS"
        :key="t.name"
        :to="{ name: t.name }"
        class="app-tab"
        :class="{ 'app-tab-web': !isNative }"
      >
        <AppIcon :name="t.icon" :size="20" />
        <span>{{ t.label }}</span>
      </router-link>
    </nav>
  </div>
</template>

<style scoped>
.appshell {
  display: flex;
  flex-direction: column;
  min-height: 100dvh;
  background: var(--bg, #f6f6fb);
}
.app-top {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 14px;
  padding-top: calc(10px + env(safe-area-inset-top, 0px));
  background: var(--card, #fff);
  border-bottom: 1px solid var(--line, #e5e5ef);
}
.app-top-id { display: flex; align-items: center; gap: 10px; min-width: 0; }
.app-top-id :deep(.brand-logo) { flex: none; }
.app-top-txt { display: flex; flex-direction: column; min-width: 0; }
.app-shop {
  font-size: 15px; font-weight: 800; color: var(--ink, #17141f);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.app-weblink {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 0; border: 0; background: none; cursor: pointer;
  font-size: 12px; color: var(--brand-500, #4f46e5); font-weight: 600;
  text-align: left;
}
.app-iconbtn {
  display: grid; place-items: center; flex: none;
  width: 38px; height: 38px; border-radius: 10px;
  border: 1px solid var(--line, #e5e5ef); background: var(--card, #fff);
  color: var(--muted, #6b6478); cursor: pointer;
}
.app-main { flex: 1; padding: 14px; padding-bottom: 92px; max-width: 720px; width: 100%; margin: 0 auto; }
.app-tabs {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  z-index: 30;
  display: flex;
  background: var(--card, #fff);
  border-top: 1px solid var(--line, #e5e5ef);
  padding-bottom: env(safe-area-inset-bottom, 0px);
}
.app-tab {
  flex: 1;
  display: flex; flex-direction: column; align-items: center; gap: 3px;
  padding: 9px 2px 8px;
  font-size: 10.5px; font-weight: 600;
  color: var(--muted, #6b6478);
  text-decoration: none;
}
.app-tab.router-link-active { color: var(--brand-500, #4f46e5); }
</style>
