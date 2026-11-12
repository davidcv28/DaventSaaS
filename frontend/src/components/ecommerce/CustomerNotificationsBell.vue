<script setup>
// Campana de notificaciones del comprador en el header de la tienda.
// Badge con los no-leídos + dropdown con los últimos avisos; el click
// marca leído y navega al `target` del aviso (vista de /cuenta o
// catálogo). Estado compartido: useCustomerNotifications (SSE).
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../AppIcon.vue'
import { useCustomerStore } from '../../stores/customer.store.js'
import { useCustomerNotifications } from '../../composables/useCustomerNotifications.js'

const props = defineProps({
  accountTo: { type: Object, required: true },   // {path} de /cuenta
  catalogTo: { type: Object, required: true },   // {path} del catálogo
})

const router = useRouter()
const notif = useCustomerNotifications()
const customerStore = useCustomerStore()
const authed = computed(() => customerStore.isAuthenticated)

const open = ref(false)
const rootRef = ref(null)

const KIND_ICON = { order: 'package', offer: 'tag', support: 'mail', membership: 'crown' }
const kindIcon = (k) => KIND_ICON[k] || 'bell'

const recent = computed(() => notif.items.value.slice(0, 8))
const badge = computed(() => (notif.unread.value > 99 ? '99+' : notif.unread.value))

const fmtWhen = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  const diff = Date.now() - d.getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'ahora'
  if (mins < 60) return `hace ${mins} min`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `hace ${hours} h`
  return d.toLocaleDateString('es-AR', { day: 'numeric', month: 'short' })
}

// Destino del click: vista de /cuenta o el catálogo ('' → solo leído).
function targetTo(n) {
  const t = n?.target || ''
  if (t === 'catalogo') return props.catalogTo
  if (['pedidos', 'suscripciones', 'soporte', 'notificaciones'].includes(t)) {
    return { path: props.accountTo.path, query: { view: t } }
  }
  return null
}

async function openNotification(n) {
  open.value = false
  const to = targetTo(n)
  await notif.markRead(n)
  if (to) router.push(to)
}

const allTo = computed(() => ({ path: props.accountTo.path, query: { view: 'notificaciones' } }))

async function markAll() {
  await notif.markAll()
}

function onDocClick(e) {
  if (open.value && rootRef.value && !rootRef.value.contains(e.target)) open.value = false
}
function onKey(e) {
  if (e.key === 'Escape' && open.value) open.value = false
}

onMounted(() => {
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div ref="rootRef" class="sp-notif">
    <button
      type="button"
      class="sp-icon-btn"
      :aria-label="notif.unread.value ? `Notificaciones, ${notif.unread.value} sin leer` : 'Notificaciones'"
      :aria-expanded="open"
      aria-controls="sp-notif-panel"
      title="Notificaciones"
      @click.stop="open = !open"
    >
      <AppIcon name="bell" :size="17" />
      <span v-if="notif.unread.value" class="ec-badge" aria-hidden="true">{{ badge }}</span>
    </button>

    <Transition name="sp-notif">
      <div v-if="open" id="sp-notif-panel" class="sp-notif-panel" role="dialog" aria-label="Notificaciones">
        <header class="sp-notif-head">
          <strong>Notificaciones</strong>
          <button v-if="notif.unread.value" type="button" class="sp-notif-clear" @click="markAll">
            Marcar todas como leídas
          </button>
        </header>
        <!-- Invitado: el stream no corre sin sesión — el panel ofrece el
             acceso a la cuenta en vez de una lista vacía engañosa. -->
        <div v-if="!authed" class="sp-notif-empty">
          <AppIcon name="bell" :size="18" aria-hidden="true" />
          <p>Ingresá o creá tu cuenta para ver los avisos de la tienda.</p>
          <RouterLink :to="accountTo" class="sp-notif-all" @click="open = false">Ingresar a mi cuenta</RouterLink>
        </div>
        <p v-else-if="!recent.length" class="sp-notif-empty">
          <AppIcon name="bell" :size="18" aria-hidden="true" />
          Todavía no tenés avisos.
        </p>
        <ul v-else class="sp-notif-list">
          <li v-for="n in recent" :key="n.id">
            <button
              type="button"
              class="sp-notif-item"
              :class="{ 'is-unread': !n.read_at }"
              @click="openNotification(n)"
            >
              <span class="sp-notif-ico" aria-hidden="true"><AppIcon :name="kindIcon(n.kind)" :size="15" /></span>
              <span class="sp-notif-txt">
                <span class="sp-notif-title">{{ n.title }}</span>
                <span v-if="n.body" class="sp-notif-body">{{ n.body }}</span>
                <span class="sp-notif-when">{{ fmtWhen(n.created_at) }}</span>
              </span>
              <span v-if="!n.read_at" class="sp-notif-dot" aria-hidden="true"></span>
            </button>
          </li>
        </ul>
        <footer v-if="recent.length" class="sp-notif-foot">
          <RouterLink :to="allTo" class="sp-notif-all" @click="open = false">Ver todas</RouterLink>
        </footer>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
/* Badge y dropdown de la campana: tokens de la piel (--sp-*) como el
   resto del chrome; el panel flota a la derecha del botón y en móvil
   baja a hoja anclada al pie. */
.sp-notif { position: relative; }
.ec-badge {
  position: absolute; top: -5px; right: -5px;
  min-width: 19px; height: 19px; padding: 0 5px;
  display: grid; place-items: center;
  border-radius: 999px; font-size: 10.5px; font-weight: 800;
  background: var(--sp-danger, #dc2626); color: #fff;
  border: 2px solid var(--sp-card, #fff);
  font-variant-numeric: tabular-nums; pointer-events: none;
}
.sp-notif-panel {
  position: absolute; top: calc(100% + 10px); right: 0; z-index: 40;
  width: min(340px, calc(100vw - 24px));
  border: 1px solid var(--sp-line, rgba(0,0,0,.09));
  border-radius: calc(var(--sp-radius, 16px) * .9);
  background: var(--sp-card, #fff); color: var(--sp-ink, inherit);
  box-shadow: var(--sp-shadow-md, 0 18px 46px -20px rgba(15,23,42,.35));
  display: flex; flex-direction: column; overflow: hidden;
}
.sp-notif-head {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 11px 14px; border-bottom: 1px solid var(--sp-line, rgba(0,0,0,.08));
  font-size: 12px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase;
  color: var(--sp-muted, inherit);
}
.sp-notif-clear { border: none; background: none; padding: 2px 4px; font: inherit; font-size: 11.5px; font-weight: 700; letter-spacing: 0; text-transform: none; color: var(--sp-accent-text, var(--store-accent, inherit)); cursor: pointer; border-radius: 6px; }
.sp-notif-clear:hover { text-decoration: underline; text-underline-offset: 2px; }
.sp-notif-empty { display: grid; justify-items: center; gap: 6px; margin: 0; padding: 22px 14px; font-size: 13px; color: var(--sp-muted, inherit); text-align: center; }
.sp-notif-empty p { margin: 0; }
.sp-notif-list { list-style: none; margin: 0; padding: 6px; max-height: 340px; overflow-y: auto; }
.sp-notif-item { display: flex; gap: 10px; align-items: flex-start; width: 100%; padding: 10px; border: none; border-radius: 10px; background: none; font: inherit; color: inherit; text-align: left; cursor: pointer; }
.sp-notif-item:hover { background: color-mix(in srgb, var(--sp-ink, #000) 5%, transparent); }
.sp-notif-item.is-unread { background: color-mix(in srgb, var(--store-accent, #111) 7%, transparent); }
.sp-notif-ico { display: grid; place-items: center; width: 30px; height: 30px; flex: none; border-radius: 50%; background: color-mix(in srgb, var(--store-accent, #111) 11%, transparent); color: var(--sp-accent-text, var(--store-accent, inherit)); }
.sp-notif-txt { flex: 1; min-width: 0; display: grid; gap: 2px; }
.sp-notif-title { font-size: 13px; font-weight: 700; overflow-wrap: anywhere; }
.sp-notif-body { font-size: 12px; line-height: 1.4; color: var(--sp-muted, inherit); overflow-wrap: anywhere; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.sp-notif-when { font-size: 11px; color: var(--sp-muted, inherit); }
.sp-notif-dot { flex: none; width: 8px; height: 8px; margin-top: 5px; border-radius: 50%; background: var(--store-accent, #2563eb); }
.sp-notif-foot { padding: 4px 14px 10px; border-top: 1px solid var(--sp-line, rgba(0,0,0,.08)); }
.sp-notif-all { display: inline-block; padding-top: 8px; font-size: 13px; font-weight: 700; color: var(--sp-accent-text, var(--store-accent, inherit)); text-decoration: none; }
.sp-notif-all:hover { text-decoration: underline; text-underline-offset: 2px; }
.sp-notif-enter-active, .sp-notif-leave-active { transition: opacity .15s ease, transform .15s ease; }
.sp-notif-enter-from, .sp-notif-leave-to { opacity: 0; transform: translateY(-4px); }
@media (prefers-reduced-motion: reduce) {
  .sp-notif-enter-active, .sp-notif-leave-active { transition: none; }
}
@media (max-width: 520px) {
  .sp-notif-panel { position: fixed; top: auto; bottom: 14px; left: 12px; right: 12px; width: auto; max-height: min(64vh, 460px); }
}
</style>
