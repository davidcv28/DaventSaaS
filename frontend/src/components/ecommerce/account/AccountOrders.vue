<script setup>
// Tab "Mis pedidos" del panel de cuenta: cards por pedido con pill de
// estado semántico, total y accesos a seguimiento/comprobante.
import { computed, inject } from 'vue'
import { formatARS } from '../../../api/billing.api.js'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../AppIcon.vue'

defineProps({
  orders: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  shopName: { type: String, default: 'la tienda' },
})
const emit = defineEmits(['retry'])

const ctx = inject('storePage')
const slug = computed(() => ctx?.slug?.value || ctx?.slug || '')

const money = (v) => (Number(v) > 0 ? formatARS(v, 2) : '$ 0,00')
const fmtDate = (iso) => iso ? new Date(iso).toLocaleDateString('es-AR', { day: 'numeric', month: 'long', year: 'numeric' }) : ''
const catalogoTo = computed(() => ({ path: storeHostSlug ? '/catalogo' : `/${slug.value}/catalogo` }))
const seguimientoTo = (token) => ({
  path: storeHostSlug ? '/seguimiento' : `/${slug.value}/seguimiento`,
  query: { token }
})
const comprobanteTo = (token) => ({
  path: storeHostSlug ? `/pedido/${token}/comprobante` : `/${slug.value}/pedido/${token}/comprobante`
})

const STATUS_LABELS = {
  PENDING_PAYMENT: 'Pendiente de pago', PAID: 'Pagado', PACKING: 'Preparando',
  SHIPPED: 'Enviado', DELIVERED: 'Entregado', EXPIRED: 'Vencido',
  CANCELLED: 'Cancelado', REFUNDED: 'Reembolsado',
}
const statusKey = (s) => String(s || '').toLowerCase()
const itemCount = (o) => o?.items_count ?? o?.items?.length ?? 0
const itemNoun = (n) => (n === 1 ? 'producto' : 'productos')
</script>

<template>
  <section class="acc-panel" aria-label="Mis pedidos">
    <header class="acc-panel-head">
      <div class="acc-panel-headtxt">
        <span class="acc-panel-kicker" aria-hidden="true">01 · Pedidos</span>
        <h2 class="acc-panel-title">Mis pedidos</h2>
        <p class="acc-panel-sub">
          <template v-if="orders.length">{{ orders.length }} {{ orders.length === 1 ? 'pedido' : 'pedidos' }} en {{ shopName }}</template>
          <template v-else>Tus compras en {{ shopName }}</template>
        </p>
      </div>
    </header>

    <!-- Skeleton discreto mientras carga -->
    <div v-if="loading" class="acc-orders" aria-busy="true" aria-label="Cargando tus pedidos">
      <div v-for="n in 3" :key="n" class="acc-order acc-order--skel">
        <span class="acc-sk acc-sk-line acc-sk-title"></span>
        <span class="acc-sk acc-sk-line acc-sk-meta"></span>
        <span class="acc-sk acc-sk-pill"></span>
      </div>
    </div>

    <div v-else-if="error" class="acc-note acc-note--danger" role="alert">
      <AppIcon name="circle-alert" :size="18" aria-hidden="true" />
      <p>{{ error }}</p>
      <button type="button" class="ec-btn-ghost acc-btn-sm" @click="emit('retry')">Reintentar</button>
    </div>

    <div v-else-if="!orders.length" class="acc-empty">
      <div class="acc-empty-art" aria-hidden="true">
        <svg viewBox="0 0 240 150" role="presentation" focusable="false">
          <path class="a-line a-dash" d="M34 132h172" />
          <path class="a-line" d="M120 92c0-13-1-21-2-28" />
          <path class="a-leaf a-leaf--l" d="M118 66c-13-2-20-10-21-22 12 2 20 10 21 22Z" />
          <path class="a-leaf a-leaf--r" d="M122 60c11-3 18-11 18-21-11 2-17 10-18 21Z" />
          <path class="a-line" d="M92 96h56v30H92z" />
          <path class="a-line" d="M86 96h68" />
          <path class="a-line a-dash" d="M120 96v30" />
          <path class="a-line" d="M101 106h10" />
          <path class="a-line" d="M101 113h10" />
          <circle class="a-dot" cx="120" cy="40" r="2.6" />
          <path class="a-line a-dash" d="M64 122c8-5 16-6 24-3" />
        </svg>
      </div>
      <span class="acc-empty-ico" aria-hidden="true"><AppIcon name="package" :size="30" /></span>
      <h3 class="acc-empty-title">Todavía no hiciste pedidos</h3>
      <p class="acc-empty-sub">Cuando compres en {{ shopName }}, tus pedidos van a aparecer acá con su estado y comprobante.</p>
      <RouterLink :to="catalogoTo" class="ec-btn-primary">Ver catálogo</RouterLink>
    </div>

    <ul v-else class="acc-orders">
      <li v-for="(o, i) in orders" :key="o.tracking_token || o.id" class="acc-order">
        <div class="acc-order-top">
          <div class="acc-order-id">
            <span class="acc-order-idx" aria-hidden="true">N.º {{ String(i + 1).padStart(2, '0') }}</span>
            <strong class="acc-order-code">{{ o.code || `#${o.id}` }}</strong>
            <small class="acc-order-meta">
              {{ fmtDate(o.created_at) }}<template v-if="fmtDate(o.created_at) && itemCount(o)"> · </template>{{ itemCount(o) }} {{ itemNoun(itemCount(o)) }}
            </small>
          </div>
          <span class="acc-status" :class="`is-${statusKey(o.status)}`">
            <AppIcon v-if="o.status === 'SHIPPED'" name="truck" :size="12" aria-hidden="true" />
            {{ STATUS_LABELS[o.status] || o.status }}
          </span>
        </div>
        <div class="acc-order-foot">
          <strong class="acc-order-total">{{ money(o.total) }}</strong>
          <span class="acc-order-actions">
            <RouterLink :to="seguimientoTo(o.tracking_token)" class="acc-order-link">
              Seguir <AppIcon name="arrow-right" :size="13" aria-hidden="true" />
            </RouterLink>
            <RouterLink v-if="o.tracking_token" :to="comprobanteTo(o.tracking_token)" class="acc-order-link" target="_blank">
              <AppIcon name="receipt" :size="13" aria-hidden="true" /> Comprobante
            </RouterLink>
          </span>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
/* Nodos de la piel "esencial" (ocultos por defecto, ver skin CSS). */
.acc-panel-kicker, .acc-empty-art { display: none; }
.acc-panel { display: grid; gap: 16px; padding: 20px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: var(--sp-radius); background: var(--sp-card, transparent); box-shadow: var(--sp-shadow-sm, none); }
.acc-panel-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.acc-panel-headtxt { display: grid; gap: 3px; min-width: 0; }
.acc-panel-title { margin: 0; font-size: 18px; font-weight: 800; letter-spacing: -.01em; }
.acc-panel-sub { margin: 0; font-size: 13px; color: var(--sp-muted, inherit); overflow-wrap: anywhere; }

.acc-note { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 12px 14px; border: 1px solid var(--sp-line, rgba(0,0,0,.1)); border-radius: calc(var(--sp-radius) * .7); font-size: 13.5px; }
.acc-note p { margin: 0; flex: 1; min-width: 180px; color: var(--sp-ink-2, inherit); }
.acc-note--danger { border-color: color-mix(in srgb, var(--sp-danger, #dc2626) 30%, transparent); background: color-mix(in srgb, var(--sp-danger, #dc2626) 6%, transparent); color: var(--sp-danger, #dc2626); }

.acc-empty { display: grid; justify-items: center; gap: 8px; padding: 36px 16px; text-align: center; }
.acc-empty-ico { display: grid; place-items: center; width: 64px; height: 64px; border-radius: 50%; background: color-mix(in srgb, var(--store-accent, #111) 10%, transparent); color: var(--sp-accent-text, var(--store-accent, inherit)); margin-bottom: 4px; }
.acc-empty-title { margin: 0; font-size: 16px; font-weight: 800; color: var(--sp-ink, inherit); }
.acc-empty-sub { margin: 0 0 8px; max-width: 380px; font-size: 13.5px; line-height: 1.5; color: var(--sp-muted, inherit); }

.acc-orders { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.acc-order { display: grid; gap: 12px; padding: 14px 16px; border: 1px solid var(--sp-line, rgba(0,0,0,.1)); border-radius: calc(var(--sp-radius) * .75); background: var(--sp-card-solid, var(--sp-card, transparent)); transition: border-color .15s, box-shadow .15s; }
.acc-order:hover { border-color: color-mix(in srgb, var(--store-accent, #111) 35%, var(--sp-line, transparent)); box-shadow: var(--sp-shadow-sm, none); }
.acc-order-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.acc-order-id { display: grid; gap: 3px; min-width: 0; }
.acc-order-code { font-size: 15px; font-weight: 800; letter-spacing: -.01em; overflow-wrap: anywhere; }
.acc-order-meta { font-size: 12.5px; color: var(--sp-muted, inherit); }
.acc-order-foot { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; border-top: 1px dashed var(--sp-line, rgba(0,0,0,.12)); padding-top: 12px; }
.acc-order-total { font-size: 16px; font-weight: 800; font-variant-numeric: tabular-nums; }
.acc-order-actions { display: inline-flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.acc-order-link { display: inline-flex; align-items: center; gap: 5px; font-size: 13px; font-weight: 700; color: var(--sp-accent-text, var(--store-accent, inherit)); text-decoration: none; }
.acc-order-link:hover { text-decoration: underline; text-underline-offset: 3px; }

/* Pill de estado: tono semántico por token (--tone la fija cada estado) */
.acc-status { --tone: var(--sp-muted, #64748b); display: inline-flex; align-items: center; gap: 5px; font-size: 11.5px; font-weight: 700; line-height: 1; padding: 6px 11px; border-radius: 999px; background: color-mix(in srgb, var(--tone) 14%, transparent); color: var(--tone); white-space: nowrap; }
.acc-status.is-pending_payment, .acc-status.is-pending { --tone: var(--sp-warning, #B45309); }
.acc-status.is-paid, .acc-status.is-shipped { --tone: var(--sp-accent-text, var(--store-accent, #111)); }
.acc-status.is-packing { --tone: var(--sp-ink-2, #334155); }
.acc-status.is-delivered, .acc-status.is-active { --tone: var(--sp-success, #0E7A55); }
.acc-status.is-expired { --tone: var(--sp-muted, #64748b); }
.acc-status.is-cancelled { --tone: var(--sp-danger, #B42318); }
.acc-status.is-refunded { --tone: color-mix(in srgb, var(--sp-danger, #B42318) 55%, var(--sp-warning, #B45309)); }

/* Skeletons (mismo lenguaje que el carrito) */
.acc-sk { display: block; border-radius: 8px; background: color-mix(in srgb, var(--sp-muted, #94a3b8) 16%, transparent); }
.acc-sk-line { height: 12px; }
.acc-sk-title { width: 30%; height: 16px; }
.acc-sk-meta { width: 46%; }
.acc-sk-pill { width: 96px; height: 26px; border-radius: 999px; justify-self: end; }
.acc-order--skel { display: grid; gap: 10px; }
@media (prefers-reduced-motion: no-preference) {
  .acc-sk { animation: acc-shimmer 1.4s ease-in-out infinite; }
  .acc-order--skel:nth-child(2) .acc-sk { animation-delay: .12s; }
  .acc-order--skel:nth-child(3) .acc-sk { animation-delay: .24s; }
  @keyframes acc-shimmer { 0%, 100% { opacity: 1; } 50% { opacity: .45; } }
}

.ec-btn-primary { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 12px 18px; border: none; border-radius: calc(var(--sp-radius) * .75); background: var(--store-accent-ink, #111); color: var(--sp-on-band, #fff); font-size: 14px; font-weight: 700; cursor: pointer; text-decoration: none; }
.ec-btn-primary:hover { filter: brightness(1.06); }
.ec-btn-ghost { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 10px 14px; border: 1px solid var(--sp-line, currentColor); border-radius: calc(var(--sp-radius) * .7); background: transparent; color: inherit; font-size: 13px; font-weight: 600; cursor: pointer; }
.acc-btn-sm { padding: 8px 13px; font-size: 12.5px; }

.acc-order :focus-visible, .ec-btn-primary:focus-visible, .ec-btn-ghost:focus-visible {
  outline: 2px solid var(--store-accent, #111); outline-offset: 2px;
}
@media (max-width: 560px) {
  .acc-panel { padding: 16px; }
  .acc-order-foot { align-items: flex-start; flex-direction: column; }
}
</style>
