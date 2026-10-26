<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import BrandLogo from './BrandLogo.vue'
import AppIcon from './AppIcon.vue'
import { useThemeStore } from '../stores/theme.store.js'
import '../assets/dashboard.css'

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
const navEl = ref(null)
const btnEls = new Map()
const indicator = ref({ y: 0, h: 0, ready: false })

const current = computed(() => props.items.find((i) => i.id === props.active))
const todayLabel = new Date().toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' })

const setBtn = (id) => (el) => { if (el) btnEls.set(id, el); else btnEls.delete(id) }
const close = () => { open.value = false }
const go = (id) => { close(); emit('navigate', id) }
const onKey = (e) => { if (e.key === 'Escape') close() }
const setHeaderVar = () => {
  if (sidebarEl.value) document.documentElement.style.setProperty('--header-h', `${sidebarEl.value.offsetHeight}px`)
}
const onResize = () => { if (window.innerWidth > 860) close(); moveIndicator() }

// Píldora activa: se mueve con transform (compositor), sin layout por frame.
function moveIndicator() {
  const el = btnEls.get(props.active)
  if (!el || !navEl.value) { indicator.value = { ...indicator.value, ready: false }; return }
  indicator.value = { y: el.offsetTop - navEl.value.scrollTop, h: el.offsetHeight, ready: true }
}

watch(open, (v) => { document.body.style.overflow = v ? 'hidden' : '' })
watch(() => props.active, async () => {
  await nextTick()
  moveIndicator()
  window.scrollTo({ top: 0, behavior: 'smooth' })
})
watch(() => props.items, async () => { await nextTick(); moveIndicator() })

let headerObserver
onMounted(() => {
  // El panel es siempre oscuro (sin toggle): se restaura el tema global al salir.
  theme.forceDark()
  setHeaderVar()
  moveIndicator()
  if (sidebarEl.value) { headerObserver = new ResizeObserver(() => { setHeaderVar(); moveIndicator() }); headerObserver.observe(sidebarEl.value) }
  window.addEventListener('keydown', onKey)
  window.addEventListener('resize', onResize, { passive: true })
})
onBeforeUnmount(() => {
  theme.releaseTheme()
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
        class="menu-toggle"
        :class="{ open }"
        type="button"
        :aria-label="open ? 'Cerrar menú' : 'Abrir menú'"
        :aria-expanded="open"
        aria-controls="side-panel"
        @click="open = !open"
      >
        <span class="burger" aria-hidden="true"><i></i><i></i><i></i></span>
      </button>
      <div id="side-panel" class="side-panel" :class="{ open }">
        <nav ref="navEl" aria-label="Principal">
          <span
            class="nav-indicator"
            :class="{ ready: indicator.ready }"
            :style="{ transform: `translateY(${indicator.y}px)`, height: indicator.h + 'px' }"
            aria-hidden="true"
          ></span>
          <template v-for="(i, idx) in items" :key="i.id || i.heading || idx">
            <p v-if="i.heading" class="nav-heading" aria-hidden="true">{{ i.heading }}</p>
            <button
              v-else
              :ref="setBtn(i.id)"
              :class="{ active: active === i.id }"
              :style="{ '--i': idx }"
              :aria-current="active === i.id ? 'page' : undefined"
              @click="go(i.id)"
            >
              <AppIcon :name="i.icon" :size="18" /> <span>{{ i.label }}</span>
            </button>
          </template>
        </nav>
        <div class="side-foot">
          <RouterLink class="link" to="/terminos" @click="close"><AppIcon name="file-text" :size="16" /> <span>Términos y condiciones</span></RouterLink>
          <RouterLink class="link" to="/denuncias" @click="close"><AppIcon name="flag" :size="16" /> <span>Denunciar contenido</span></RouterLink>
          <div class="who"><span class="avatar sm">{{ initial }}</span> <span class="who-name">{{ userName }}</span></div>
          <button class="link" @click="close(); emit('logout')"><AppIcon name="logout" :size="16" /> <span>Cerrar sesión</span></button>
        </div>
      </div>
    </aside>
    <div class="main">
      <header class="topbar">
        <div class="topbar-title">
          <AppIcon v-if="current?.icon" :name="current.icon" :size="18" />
          <Transition name="tb-swap" mode="out-in"><strong :key="active">{{ current?.label || 'Resumen' }}</strong></Transition>
        </div>
        <span class="topbar-date">{{ todayLabel }}</span>
        <span class="avatar sm" :title="userName">{{ initial }}</span>
      </header>
      <slot />
    </div>
  </div>
</template>
