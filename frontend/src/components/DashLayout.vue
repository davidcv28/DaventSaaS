<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import BrandLogo from './BrandLogo.vue'
import AppIcon from './AppIcon.vue'
import { useThemeStore } from '../stores/theme.store.js'

const theme = useThemeStore()

const props = defineProps({
  active: { type: String, default: 'overview' },
  planName: { type: String, default: '' },
  userName: { type: String, default: '' },
  initial: { type: String, default: 'U' },
  // Ítems de navegación. Acepta entradas {heading} como separador de grupo.
  items: {
    type: Array,
    default: () => [
      { id: 'overview', label: 'Resumen', icon: 'dashboard' },
      { id: 'catalogs', label: 'Mis catálogos', icon: 'library' },
      { id: 'plans', label: 'Planes', icon: 'credit-card' },
      { id: 'payments', label: 'Pagos', icon: 'receipt' },
      { id: 'settings', label: 'Cuenta', icon: 'user' }
    ]
  }
})
const emit = defineEmits(['navigate', 'logout'])

const open = ref(false)
const sidebarEl = ref(null)
const close = () => { open.value = false }
const go = (id) => { close(); emit('navigate', id) }
const onKey = (e) => { if (e.key === 'Escape') close() }
const setHeaderVar = () => {
  if (sidebarEl.value) document.documentElement.style.setProperty('--header-h', `${sidebarEl.value.offsetHeight}px`)
}
const onResize = () => { if (window.innerWidth > 860) close() }
watch(open, (v) => { document.body.style.overflow = v ? 'hidden' : '' })

let headerObserver
onMounted(() => {
  setHeaderVar()
  if (sidebarEl.value) { headerObserver = new ResizeObserver(setHeaderVar); headerObserver.observe(sidebarEl.value) }
  window.addEventListener('keydown', onKey)
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  headerObserver?.disconnect()
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('resize', onResize)
  document.body.style.overflow = ''
})
</script>

<template>
  <div class="app">
    <aside ref="sidebarEl" class="sidebar">
      <div class="brand"><BrandLogo :size="34" /> <span>DAVENT</span></div>
      <div v-if="planName" class="plan-badge"><AppIcon name="dot" :size="12" /> {{ planName }}</div>
      <button
        class="theme-icon"
        type="button"
        :aria-label="theme.isDark ? 'Cambiar a modo claro' : 'Cambiar a modo nocturno'"
        :aria-pressed="theme.isDark"
        @click="theme.toggleTheme()"
      >
        <AppIcon :name="theme.isDark ? 'sun' : 'moon'" :size="20" />
      </button>
      <button
        class="menu-toggle"
        type="button"
        :aria-label="open ? 'Cerrar menú' : 'Abrir menú'"
        :aria-expanded="open"
        aria-controls="side-panel"
        @click="open = !open"
      >
        <AppIcon :name="open ? 'x' : 'menu'" :size="22" />
      </button>
      <div id="side-panel" class="side-panel" :class="{ open }">
        <nav aria-label="Principal">
          <template v-for="(i, idx) in items" :key="i.id || i.heading || idx">
            <p v-if="i.heading" class="nav-heading" aria-hidden="true">{{ i.heading }}</p>
            <button
              v-else
              :class="{ active: active === i.id }"
              :aria-current="active === i.id ? 'page' : undefined"
              @click="go(i.id)"
            >
              <AppIcon :name="i.icon" :size="18" /> <span>{{ i.label }}</span>
            </button>
          </template>
        </nav>
        <div class="side-foot">
          <button class="link theme-btn" type="button" :aria-pressed="theme.isDark" @click="theme.toggleTheme()">
            <AppIcon :name="theme.isDark ? 'sun' : 'moon'" :size="16" />
            <span>{{ theme.isDark ? 'Modo claro' : 'Modo nocturno' }}</span>
          </button>
          <RouterLink class="link" to="/terminos" @click="close"><AppIcon name="file-text" :size="16" /> <span>Términos y condiciones</span></RouterLink>
          <RouterLink class="link" to="/denuncias" @click="close"><AppIcon name="flag" :size="16" /> <span>Denunciar contenido</span></RouterLink>
          <div class="who"><span class="avatar sm">{{ initial }}</span> <span class="who-name">{{ userName }}</span></div>
          <button class="link" @click="close(); emit('logout')"><AppIcon name="logout" :size="16" /> <span>Cerrar sesión</span></button>
        </div>
      </div>
    </aside>
    <div class="main">
      <slot />
    </div>
  </div>
</template>
