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
  // Ítems de navegación. Acepta entradas {heading} como separador de grupo,
  // {hint} como microdescripción bajo el label y {locked} para el candado.
  items: {
    type: Array,
    default: () => [
      { id: 'overview', label: 'Resumen', icon: 'dashboard' },
      { id: 'catalogs', label: 'Mis catálogos', icon: 'library' },
      { id: 'plans', label: 'Planes', icon: 'credit-card' },
      { id: 'payments', label: 'Pagos', icon: 'receipt' },
      { id: 'settings', label: 'Cuenta', icon: 'user' }
    ]
  },
  // 4 destinos fijos de la tab bar móvil ({id,label,icon,badge?}). Vacío =
  // comportamiento clásico (barra superior con hamburguesa, para el admin).
  tabs: { type: Array, default: () => [] },
  // Sección padre del apartado actual: habilita el botón "volver" y la
  // miga de pan en la barra superior (p.ej. Diseño -> Mi página).
  parent: { type: Object, default: null },
  // Título de la sección actual (un apartado sin entrada propia en el menú).
  title: { type: String, default: '' },
  // 'dark' fuerza el tema oscuro mientras el layout está montado (admin).
  forceTheme: { type: String, default: '' }
})
const emit = defineEmits(['navigate', 'logout', 'locked', 'search', 'messages', 'tour'])

const open = ref(false)
const sidebarEl = ref(null)
const navEl = ref(null)
const btnEls = new Map()
const indicator = ref({ y: 0, h: 0, ready: false })

const hasTabs = computed(() => props.tabs.length > 0)
const current = computed(() => props.items.find((i) => i.id === props.active))
const currentLabel = computed(() => props.title || current.value?.label || 'Resumen')
const todayLabel = new Date().toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' })

const setBtn = (id) => (el) => { if (el) btnEls.set(id, el); else btnEls.delete(id) }
const close = () => { open.value = false }
const go = (i) => {
  close()
  if (i.locked) { emit('locked', i); return }
  if (i.id === 'chat') { emit('messages'); return }
  emit('navigate', i.id)
}
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
  // forceTheme 'dark' mantiene paneles siempre oscuros (admin); sin el prop
  // el tema sigue al usuario (claro/oscuro con toggle y persistencia).
  if (props.forceTheme) theme.forceDark()
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
  <div class="app" :class="{ 'app--tabs': hasTabs }">
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
              :class="{ active: active === i.id, locked: i.locked }"
              :style="{ '--i': idx }"
              :aria-current="active === i.id ? 'page' : undefined"
              :data-tour="`nav-${i.id}`"
              @click="go(i)"
            >
              <AppIcon :name="i.icon" :size="18" />
              <span class="nav-label"><span>{{ i.label }}</span><small v-if="i.hint">{{ i.hint }}</small></span>
              <AppIcon v-if="i.locked" name="lock" :size="13" class="nav-lock" />
            </button>
          </template>
        </nav>
        <div class="side-foot">
          <RouterLink class="link" to="/terminos" @click="close"><AppIcon name="file-text" :size="16" /> <span>Términos y condiciones</span></RouterLink>
          <RouterLink class="link" to="/denuncias" @click="close"><AppIcon name="flag" :size="16" /> <span>Denunciar contenido</span></RouterLink>
          <button class="link" @click="close(); emit('tour')"><AppIcon name="graduation-cap" :size="16" /> <span>Repetir la guía</span></button>
          <button class="link" @click="theme.toggleTheme()"><AppIcon :name="theme.isDark ? 'sun' : 'moon'" :size="16" /> <span>{{ theme.isDark ? 'Modo claro' : 'Modo oscuro' }}</span></button>
          <div class="who"><span class="avatar sm">{{ initial }}</span> <span class="who-name">{{ userName }}</span></div>
          <button class="link" @click="close(); emit('logout')"><AppIcon name="logout" :size="16" /> <span>Cerrar sesión</span></button>
        </div>
      </div>
    </aside>
    <div class="main">
      <header class="topbar">
        <button
          v-if="parent"
          type="button"
          class="top-back"
          :aria-label="`Volver a ${parent.label}`"
          @click="emit('navigate', parent.id)"
        >
          <AppIcon name="chevron-left" :size="18" />
        </button>
        <div class="topbar-title">
          <AppIcon v-if="current?.icon" :name="current.icon" :size="18" class="topbar-icon" />
          <Transition name="tb-swap" mode="out-in">
            <span :key="currentLabel" class="crumbs">
              <small v-if="parent" class="crumb-parent">{{ parent.label }}</small>
              <strong>{{ currentLabel }}</strong>
            </span>
          </Transition>
        </div>
        <button type="button" class="top-search" aria-label="Buscar en el panel" @click="emit('search')">
          <AppIcon name="search" :size="16" />
          <span class="top-search-label">Buscar</span>
          <kbd class="kbd" aria-hidden="true">Ctrl K</kbd>
        </button>
        <span class="topbar-date">{{ todayLabel }}</span>
        <slot name="topbar-actions" />
        <span class="avatar sm" :title="userName">{{ initial }}</span>
      </header>
      <slot />
    </div>

    <!-- Tab bar móvil: 4 destinos + "Más" (abre el sheet con todo el menú) -->
    <nav v-if="hasTabs" class="tabbar" aria-label="Secciones principales">
      <button
        v-for="t in tabs"
        :key="t.id"
        type="button"
        :class="{ active: active === t.id, locked: t.locked }"
        :aria-current="active === t.id ? 'page' : undefined"
        :data-tour="`tab-${t.id}`"
        @click="go(t)"
      >
        <AppIcon :name="t.icon" :size="20" />
        <span>{{ t.label }}</span>
        <span v-if="t.badge" class="chat-badge tab-badge">{{ t.badge > 99 ? '99+' : t.badge }}</span>
      </button>
      <button type="button" :class="{ active: open }" :aria-expanded="open" aria-controls="more-sheet" @click="open = !open">
        <AppIcon name="menu" :size="20" />
        <span>Más</span>
      </button>
    </nav>

    <!-- Sheet "Más": menú completo en móvil -->
    <template v-if="hasTabs">
      <div v-if="open" class="sheet-scrim" @click="close" aria-hidden="true"></div>
      <div id="more-sheet" class="more-sheet" :class="{ open }" role="dialog" aria-modal="true" aria-label="Todas las secciones">
        <div class="sheet-head">
          <span class="sheet-grab" aria-hidden="true"></span>
          <div class="sheet-brand"><BrandLogo :size="26" /> <strong>DAVENT</strong><span v-if="planName" class="sheet-plan">{{ planName }}</span></div>
          <button type="button" class="sheet-x" aria-label="Cerrar menú" @click="close"><AppIcon name="x" :size="17" /></button>
        </div>
        <nav class="sheet-nav" aria-label="Todas las secciones">
          <template v-for="(i, idx) in items" :key="i.id || i.heading || idx">
            <p v-if="i.heading" class="nav-heading" aria-hidden="true">{{ i.heading }}</p>
            <button
              v-else
              :class="{ active: active === i.id, locked: i.locked }"
              :aria-current="active === i.id ? 'page' : undefined"
              @click="go(i)"
            >
              <AppIcon :name="i.icon" :size="18" />
              <span class="nav-label"><span>{{ i.label }}</span><small v-if="i.hint">{{ i.hint }}</small></span>
              <AppIcon v-if="i.locked" name="lock" :size="13" class="nav-lock" />
              <AppIcon v-else name="chevron-right" :size="15" class="sheet-go" />
            </button>
          </template>
        </nav>
        <div class="sheet-foot">
          <RouterLink class="link" to="/terminos" @click="close"><AppIcon name="file-text" :size="16" /> <span>Términos y condiciones</span></RouterLink>
          <RouterLink class="link" to="/denuncias" @click="close"><AppIcon name="flag" :size="16" /> <span>Denunciar contenido</span></RouterLink>
          <button class="link" @click="close(); emit('tour')"><AppIcon name="graduation-cap" :size="16" /> <span>Repetir la guía</span></button>
          <button class="link" @click="theme.toggleTheme()"><AppIcon :name="theme.isDark ? 'sun' : 'moon'" :size="16" /> <span>{{ theme.isDark ? 'Modo claro' : 'Modo oscuro' }}</span></button>
          <div class="who"><span class="avatar sm">{{ initial }}</span> <span class="who-name">{{ userName }}</span></div>
          <button class="link" @click="close(); emit('logout')"><AppIcon name="logout" :size="16" /> <span>Cerrar sesión</span></button>
        </div>
      </div>
    </template>
  </div>
</template>
