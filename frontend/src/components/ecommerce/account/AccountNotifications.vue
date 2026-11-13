<script setup>
// Tab "Notificaciones" del panel de cuenta del comprador: historial de
// avisos de ESTA tienda (estado del pedido, ofertas, respuestas del
// comercio y suscripción). Estado compartido con la campana del header
// (useCustomerNotifications — SSE ya corre desde el layout).
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { storeHostSlug } from '../../../config/env.js'
import { useCustomerNotifications } from '../../../composables/useCustomerNotifications.js'
import AppIcon from '../../AppIcon.vue'

const props = defineProps({
  slug: { type: String, required: true },
  shopName: { type: String, default: 'la tienda' },
})

const router = useRouter()
const notif = useCustomerNotifications()

const KIND_ICON = { order: 'package', offer: 'tag', support: 'mail', membership: 'crown', feed: 'lucide:newspaper' }
const KIND_LABEL = { order: 'Pedido', offer: 'Oferta', support: 'Soporte', membership: 'Suscripción', feed: 'Novedad' }
const kindIcon = (k) => KIND_ICON[k] || 'bell'
const kindLabel = (k) => KIND_LABEL[k] || 'Aviso'

const fmtWhen = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('es-AR', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const accountPath = computed(() => (storeHostSlug ? '/cuenta' : `/${props.slug}/cuenta`))
const catalogTo = computed(() => ({ path: storeHostSlug ? '/catalogo' : `/${props.slug}/catalogo` }))

function targetTo(n) {
  const t = n?.target || ''
  if (t === 'catalogo') return catalogTo.value
  //'novedades' = feed público (publicación nueva del dueño).
  if (t === 'novedades') return { path: storeHostSlug ? '/novedades' : `/${props.slug}/novedades` }
  if (['pedidos', 'suscripciones', 'soporte', 'notificaciones'].includes(t)) {
    return { path: accountPath.value, query: { view: t } }
  }
  return null
}

async function openNotification(n) {
  const to = targetTo(n)
  await notif.markRead(n)
  if (to && to.path !== accountPath.value) router.push(to)
  else if (to) router.replace(to)
}
</script>

<template>
  <section class="acc-panel" aria-label="Notificaciones">
    <header class="acc-panel-head">
      <div class="acc-panel-headtxt">
        <span class="acc-panel-kicker" aria-hidden="true">05 · Avisos</span>
        <h2 class="acc-panel-title">Notificaciones</h2>
        <p class="acc-panel-sub">Estado de tus pedidos, ofertas y mensajes de {{ shopName }}</p>
      </div>
      <button v-if="notif.unread.value" type="button" class="ec-btn-ghost" @click="notif.markAll()">
        Marcar todas como leídas
      </button>
    </header>

    <div v-if="notif.loading.value" class="acc-sub-skel" aria-busy="true" aria-label="Cargando notificaciones">
      <span class="acc-sk acc-sk-card"></span>
      <span class="acc-sk acc-sk-line acc-sk-w60"></span>
      <span class="acc-sk acc-sk-line acc-sk-w40"></span>
    </div>
    <p v-else-if="notif.error.value" class="sp-form-error" role="alert">{{ notif.error.value }}</p>
    <p v-else-if="!notif.items.value.length" class="acc-empty">
      <AppIcon name="bell" :size="22" aria-hidden="true" />
      Todavía no tenés avisos de esta tienda.
    </p>

    <ul v-else class="acc-notif-list">
      <li v-for="n in notif.items.value" :key="n.id">
        <button
          type="button"
          class="acc-notif-item"
          :class="{ 'is-unread': !n.read_at }"
          @click="openNotification(n)"
        >
          <span class="acc-notif-ico" :data-kind="n.kind" aria-hidden="true"><AppIcon :name="kindIcon(n.kind)" :size="17" /></span>
          <span class="acc-notif-txt">
            <span class="acc-notif-top">
              <span class="acc-notif-kind">{{ kindLabel(n.kind) }}</span>
              <span class="acc-notif-when">{{ fmtWhen(n.created_at) }}</span>
            </span>
            <span class="acc-notif-title">{{ n.title }}</span>
            <span v-if="n.body" class="acc-notif-body">{{ n.body }}</span>
          </span>
          <span v-if="!n.read_at" class="acc-notif-dot" aria-label="Sin leer"></span>
        </button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.acc-panel { display: grid; gap: 16px; padding: 20px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: var(--sp-radius); background: var(--sp-card, transparent); box-shadow: var(--sp-shadow-sm, none); }
.acc-panel-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.acc-panel-headtxt { display: grid; gap: 3px; min-width: 0; }
.acc-panel-title { margin: 0; font-size: 18px; font-weight: 800; letter-spacing: -.01em; }
.acc-panel-sub { margin: 0; font-size: 13px; color: var(--sp-muted, inherit); overflow-wrap: anywhere; }
.acc-panel-kicker { display: none; }
.ec-btn-ghost { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 10px 14px; border: 1px solid var(--sp-line, currentColor); border-radius: calc(var(--sp-radius) * .7); background: transparent; color: inherit; font-size: 13px; font-weight: 600; cursor: pointer; }
.acc-notif-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.acc-notif-item { display: flex; align-items: flex-start; gap: 12px; width: 100%; padding: 13px 14px; border: 1px solid var(--sp-line, rgba(0,0,0,.08)); border-radius: calc(var(--sp-radius, 14px) * .75); background: var(--sp-card, transparent); color: inherit; font: inherit; text-align: left; cursor: pointer; transition: border-color .15s, background .15s; }
.acc-notif-item:hover { border-color: var(--store-accent, currentColor); }
.acc-notif-item.is-unread { background: color-mix(in srgb, var(--store-accent, #111) 5%, transparent); border-color: color-mix(in srgb, var(--store-accent, #111) 30%, transparent); }
.acc-notif-ico { display: grid; place-items: center; width: 36px; height: 36px; flex: none; border-radius: 50%; background: color-mix(in srgb, var(--store-accent, #111) 10%, transparent); color: var(--sp-accent-text, var(--store-accent, inherit)); }
.acc-notif-txt { flex: 1; min-width: 0; display: grid; gap: 3px; }
.acc-notif-top { display: flex; align-items: baseline; gap: 8px; }
.acc-notif-kind { font-size: 10.5px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; color: var(--sp-accent-text, var(--store-accent, inherit)); }
.acc-notif-when { margin-left: auto; font-size: 11px; color: var(--sp-muted, inherit); white-space: nowrap; }
.acc-notif-title { font-size: 13.5px; font-weight: 700; overflow-wrap: anywhere; }
.acc-notif-body { font-size: 12.5px; line-height: 1.45; color: var(--sp-muted, inherit); overflow-wrap: anywhere; }
.acc-notif-dot { flex: none; width: 9px; height: 9px; margin-top: 4px; border-radius: 50%; background: var(--store-accent, #2563eb); }
.acc-empty { display: grid; justify-items: center; gap: 8px; padding: 30px 16px; text-align: center; font-size: 14px; color: var(--sp-muted, inherit); }
.acc-sub-skel { display: grid; gap: 12px; }
.acc-sk { display: block; border-radius: 8px; background: color-mix(in srgb, var(--sp-muted, #94a3b8) 16%, transparent); }
.acc-sk-card { height: 90px; }
.acc-sk-line { height: 13px; }
.acc-sk-w60 { width: 60%; }
.acc-sk-w40 { width: 40%; }
@media (prefers-reduced-motion: no-preference) {
  .acc-sub-skel .acc-sk { animation: acc-notif-shimmer 1.4s ease-in-out infinite; }
  @keyframes acc-notif-shimmer { 0%, 100% { opacity: 1; } 50% { opacity: .45; } }
}
</style>
