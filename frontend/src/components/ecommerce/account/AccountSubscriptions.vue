<script setup>
// Tab "Suscripciones" del panel de cuenta: suscripción vigente con
// tarjeta digital premium + grilla de planes disponibles (PlanSubscribe).
import { computed } from 'vue'
import { formatARS } from '../../../api/billing.api.js'
import AppIcon from '../../AppIcon.vue'
import PlanSubscribe from '../PlanSubscribe.vue'

const props = defineProps({
  slug: { type: String, required: true },
  shopName: { type: String, default: 'la tienda' },
  data: { type: Object, default: null },        // storePlans del customer
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  payments: { type: Object, default: null },     // config de cobro pública
  card: { type: Object, default: null },         // tarjeta digital cargada
  cardOpen: { type: Boolean, default: false },
  cardLoading: { type: Boolean, default: false },
  cardError: { type: String, default: '' },
})
const emit = defineEmits(['retry', 'load-card', 'hide-card', 'subscribed'])

const money = (v) => (Number(v) > 0 ? formatARS(v, 2) : '$ 0,00')
const fmtDate = (iso) => iso ? new Date(iso).toLocaleDateString('es-AR', { day: 'numeric', month: 'long', year: 'numeric' }) : ''

const BENEFIT_LABELS = {
  digital_card: 'Tarjeta digital', free_shipping: 'Envío gratis',
  exclusive_discounts: 'Descuentos exclusivos', exclusive_access: 'Acceso exclusivo',
}
const benefitLabel = (c) => BENEFIT_LABELS[c] || c
const subStatusLabel = { pending: 'Pago pendiente', active: 'Activa', cancelled: 'Cancelada', expired: 'Vencida' }
const subStatusKey = (s) => ({ pending: 'is-pending', active: 'is-active', cancelled: 'is-cancelled', expired: 'is-expired' }[s] || 'is-pending')

const subscription = computed(() => props.data?.subscription || null)
const plans = computed(() => props.data?.plans || [])
const currentPlanId = computed(() => subscription.value?.plan?.id ?? subscription.value?.plan_id ?? null)
const isCurrentPlan = (p) => currentPlanId.value != null && p?.id === currentPlanId.value
const benefits = computed(() => subscription.value?.benefits || [])
const memberInitials = computed(() => {
  const name = String(props.card?.member_name || '').trim()
  const parts = name.split(/\s+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name ? name.slice(0, 2).toUpperCase() : '·'
})
</script>

<template>
  <section class="acc-panel" aria-label="Mis suscripciones">
    <header class="acc-panel-head">
      <div class="acc-panel-headtxt">
        <h2 class="acc-panel-title">Suscripciones</h2>
        <p class="acc-panel-sub">Planes de miembro y beneficios de {{ shopName }}</p>
      </div>
    </header>

    <div v-if="loading" class="acc-sub-skel" aria-busy="true" aria-label="Cargando suscripciones">
      <span class="acc-sk acc-sk-card"></span>
      <span class="acc-sk acc-sk-line acc-sk-w60"></span>
      <span class="acc-sk acc-sk-line acc-sk-w40"></span>
    </div>

    <div v-else-if="error" class="acc-note acc-note--danger" role="alert">
      <AppIcon name="circle-alert" :size="18" aria-hidden="true" />
      <p>{{ error }}</p>
      <button type="button" class="ec-btn-ghost acc-btn-sm" @click="emit('retry')">Reintentar</button>
    </div>

    <template v-else-if="data">
      <!-- Suscripción vigente / última -->
      <div v-if="subscription" class="acc-sub-now">
        <div class="acc-sub-now-info">
          <span class="acc-sub-now-ico" aria-hidden="true"><AppIcon name="crown" :size="20" /></span>
          <div class="acc-sub-now-txt">
            <strong>{{ subscription.plan?.name || 'Plan de miembro' }}</strong>
            <small>{{ data.store?.name || shopName }}<template v-if="subscription.vigente_hasta"> · vigente hasta el {{ fmtDate(subscription.vigente_hasta) }}</template></small>
            <div v-if="benefits.length" class="acc-chips">
              <span v-for="b in benefits" :key="b" class="acc-chip">{{ benefitLabel(b) }}</span>
            </div>
          </div>
        </div>
        <span class="acc-status" :class="subscription.is_vigente ? 'is-active' : subStatusKey(subscription.status)">
          {{ subscription.is_vigente ? 'Activa' : (subStatusLabel[subscription.status] || subscription.status) }}
        </span>
        <div class="acc-sub-now-actions">
          <button v-if="cardOpen && card" type="button" class="ec-btn-ghost" @click="emit('hide-card')">Ocultar tarjeta</button>
          <button v-else type="button" class="ec-btn-primary" :disabled="cardLoading" @click="emit('load-card')">
            {{ cardLoading ? 'Cargando…' : 'Ver mi tarjeta' }}
          </button>
        </div>
      </div>
      <p v-if="cardError" class="acc-inline-error" role="alert">{{ cardError }}</p>

      <!-- Tarjeta digital premium -->
      <div v-if="cardOpen && card" class="acc-member">
        <div class="acc-member-glow" aria-hidden="true"></div>
        <div class="acc-member-top">
          <span class="acc-member-store">{{ card.store_name || shopName }}</span>
          <span class="acc-member-chip">Miembro</span>
        </div>
        <div class="acc-member-mid">
          <span class="acc-member-avatar" aria-hidden="true">{{ memberInitials }}</span>
          <div class="acc-member-id">
            <small>Nombre del miembro</small>
            <strong>{{ card.member_name }}</strong>
          </div>
          <div class="acc-member-id acc-member-id--plan">
            <small>Plan</small>
            <strong>{{ card.plan_name }}</strong>
          </div>
        </div>
        <div class="acc-member-bottom">
          <div v-if="card.vigente_hasta" class="acc-member-id">
            <small>Vigente hasta</small>
            <strong>{{ fmtDate(card.vigente_hasta) }}</strong>
          </div>
          <ul v-if="card.benefits?.length" class="acc-member-benefits">
            <li v-for="b in card.benefits" :key="b">{{ benefitLabel(b) }}</li>
          </ul>
        </div>
      </div>

      <!-- Planes disponibles -->
      <div v-if="plans.length" class="acc-sub-plans">
        <h3 class="acc-sub-plans-title">{{ subscription ? 'Sumá otro plan o cambiá de nivel' : 'Planes disponibles' }}</h3>
        <ul class="acc-plans">
          <li v-for="p in plans" :key="p.id" class="acc-plan" :class="{ 'is-current': isCurrentPlan(p) }">
            <div class="acc-plan-head">
              <strong class="acc-plan-name">{{ p.name }}</strong>
              <span v-if="isCurrentPlan(p)" class="acc-plan-flag">Tu plan</span>
            </div>
            <PlanSubscribe :slug="slug" :plan="p" :payments="payments" @subscribed="emit('subscribed')" />
          </li>
        </ul>
      </div>
      <p v-else class="acc-muted">Esta tienda no tiene planes de suscripción activos.</p>
    </template>

    <p v-else class="acc-muted">No pudimos cargar la información de suscripciones.</p>
  </section>
</template>

<style scoped>
.acc-panel { display: grid; gap: 16px; padding: 20px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: var(--sp-radius); background: var(--sp-card, transparent); box-shadow: var(--sp-shadow-sm, none); }
.acc-panel-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.acc-panel-headtxt { display: grid; gap: 3px; min-width: 0; }
.acc-panel-title { margin: 0; font-size: 18px; font-weight: 800; letter-spacing: -.01em; }
.acc-panel-sub { margin: 0; font-size: 13px; color: var(--sp-muted, inherit); overflow-wrap: anywhere; }
.acc-muted { margin: 0; font-size: 13px; line-height: 1.5; color: var(--sp-muted, inherit); }

.acc-note { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 12px 14px; border: 1px solid var(--sp-line, rgba(0,0,0,.1)); border-radius: calc(var(--sp-radius) * .7); font-size: 13.5px; }
.acc-note p { margin: 0; flex: 1; min-width: 180px; color: var(--sp-ink-2, inherit); }
.acc-note--danger { border-color: color-mix(in srgb, var(--sp-danger, #dc2626) 30%, transparent); background: color-mix(in srgb, var(--sp-danger, #dc2626) 6%, transparent); color: var(--sp-danger, #dc2626); }

/* Suscripción vigente */
.acc-sub-now { display: grid; grid-template-columns: minmax(0,1fr) auto auto; gap: 12px 16px; align-items: center; padding: 14px 16px; border: 1px solid color-mix(in srgb, var(--store-accent, #111) 30%, var(--sp-line, transparent)); border-radius: calc(var(--sp-radius) * .8); background: color-mix(in srgb, var(--store-accent-soft, var(--sp-soft, transparent)) 55%, transparent); }
.acc-sub-now-info { display: flex; align-items: flex-start; gap: 12px; min-width: 0; }
.acc-sub-now-ico { display: grid; place-items: center; width: 42px; height: 42px; flex: none; border-radius: 12px; background: linear-gradient(135deg, var(--store-accent, #111), var(--store-accent-ink, #111)); color: var(--sp-on-band, #fff); }
.acc-sub-now-txt { display: grid; gap: 4px; min-width: 0; }
.acc-sub-now-txt > strong { font-size: 15px; font-weight: 800; overflow-wrap: anywhere; }
.acc-sub-now-txt > small { font-size: 12.5px; color: var(--sp-muted, inherit); }
.acc-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
.acc-chip { font-size: 11px; font-weight: 700; padding: 4px 9px; border-radius: 999px; background: color-mix(in srgb, var(--store-accent, #111) 10%, transparent); color: var(--sp-accent-text, var(--store-accent, inherit)); }
.acc-sub-now-actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.acc-inline-error { margin: 0; font-size: 13px; color: var(--sp-danger, #dc2626); }

/* Pill de estado (mismos tonos que pedidos) */
.acc-status { --tone: var(--sp-muted, #64748b); display: inline-flex; align-items: center; gap: 5px; font-size: 11.5px; font-weight: 700; line-height: 1; padding: 6px 11px; border-radius: 999px; background: color-mix(in srgb, var(--tone) 14%, transparent); color: var(--tone); white-space: nowrap; }
.acc-status.is-pending { --tone: var(--sp-warning, #B45309); }
.acc-status.is-active { --tone: var(--sp-success, #0E7A55); }
.acc-status.is-cancelled { --tone: var(--sp-danger, #B42318); }
.acc-status.is-expired { --tone: var(--sp-muted, #64748b); }

/* Tarjeta digital premium */
.acc-member { position: relative; overflow: hidden; display: grid; gap: 16px; padding: 20px; border-radius: calc(var(--sp-radius) * 1.1); background: linear-gradient(135deg, var(--store-accent-ink, #111) 0%, color-mix(in srgb, var(--store-accent, #111) 78%, #000) 100%); color: var(--sp-on-band, #fff); box-shadow: var(--sp-shadow-md, none); }
.acc-member-glow { position: absolute; inset: -40% -20% auto auto; width: 280px; height: 280px; border-radius: 50%; background: radial-gradient(circle, color-mix(in srgb, #fff 16%, transparent), transparent 65%); pointer-events: none; }
.acc-member-top { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.acc-member-store { font-size: 11.5px; font-weight: 800; text-transform: uppercase; letter-spacing: .1em; opacity: .78; overflow-wrap: anywhere; }
.acc-member-chip { flex: none; font-size: 10.5px; font-weight: 800; text-transform: uppercase; letter-spacing: .08em; padding: 5px 10px; border-radius: 999px; border: 1px solid color-mix(in srgb, #fff 45%, transparent); background: color-mix(in srgb, #fff 12%, transparent); }
.acc-member-mid { position: relative; display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.acc-member-avatar { display: grid; place-items: center; width: 52px; height: 52px; flex: none; border-radius: 50%; background: color-mix(in srgb, #fff 16%, transparent); border: 1px solid color-mix(in srgb, #fff 35%, transparent); font-size: 17px; font-weight: 800; letter-spacing: .02em; }
.acc-member-id { display: grid; gap: 2px; min-width: 0; }
.acc-member-id small { font-size: 9.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .09em; opacity: .72; }
.acc-member-id strong { font-size: 15px; font-weight: 800; overflow-wrap: anywhere; }
.acc-member-bottom { position: relative; display: flex; align-items: flex-end; justify-content: space-between; gap: 14px; flex-wrap: wrap; border-top: 1px solid color-mix(in srgb, #fff 22%, transparent); padding-top: 14px; }
.acc-member-benefits { margin: 0; padding: 0; list-style: none; display: flex; flex-wrap: wrap; gap: 6px; }
.acc-member-benefits li { font-size: 11.5px; font-weight: 600; padding: 4px 10px; border-radius: 999px; background: color-mix(in srgb, #fff 12%, transparent); border: 1px solid color-mix(in srgb, #fff 20%, transparent); }

/* Planes */
.acc-sub-plans { display: grid; gap: 12px; }
.acc-sub-plans-title { margin: 0; font-size: 14px; font-weight: 800; }
.acc-plans { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
.acc-plan { display: grid; gap: 12px; align-content: start; padding: 15px; border: 1px solid var(--sp-line, rgba(0,0,0,.1)); border-radius: calc(var(--sp-radius) * .8); background: var(--sp-card-solid, var(--sp-card, transparent)); }
.acc-plan.is-current { border-color: color-mix(in srgb, var(--store-accent, #111) 45%, var(--sp-line, transparent)); }
.acc-plan-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.acc-plan-name { font-size: 15px; font-weight: 800; overflow-wrap: anywhere; }
.acc-plan-flag { flex: none; font-size: 10.5px; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; padding: 4px 9px; border-radius: 999px; background: color-mix(in srgb, var(--sp-success, #0E7A55) 14%, transparent); color: var(--sp-success, #0E7A55); }

/* Skeletons */
.acc-sk { display: block; border-radius: 8px; background: color-mix(in srgb, var(--sp-muted, #94a3b8) 16%, transparent); }
.acc-sk-card { height: 96px; border-radius: calc(var(--sp-radius) * .8); }
.acc-sk-line { height: 12px; }
.acc-sk-w60 { width: 60%; }
.acc-sk-w40 { width: 40%; }
.acc-sub-skel { display: grid; gap: 12px; }
@media (prefers-reduced-motion: no-preference) {
  .acc-sk { animation: acc-sub-shimmer 1.4s ease-in-out infinite; }
  .acc-sub-skel > :nth-child(2) .acc-sk { animation-delay: .12s; }
  .acc-sub-skel > :nth-child(3) .acc-sk { animation-delay: .24s; }
  @keyframes acc-sub-shimmer { 0%, 100% { opacity: 1; } 50% { opacity: .45; } }
}

.ec-btn-primary { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 12px 18px; border: none; border-radius: calc(var(--sp-radius) * .75); background: var(--store-accent-ink, #111); color: var(--sp-on-band, #fff); font-size: 14px; font-weight: 700; cursor: pointer; text-decoration: none; }
.ec-btn-primary:hover { filter: brightness(1.06); }
.ec-btn-primary:disabled { opacity: .55; cursor: default; }
.ec-btn-ghost { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 10px 14px; border: 1px solid var(--sp-line, currentColor); border-radius: calc(var(--sp-radius) * .7); background: transparent; color: inherit; font-size: 13px; font-weight: 600; cursor: pointer; }
.acc-btn-sm { padding: 8px 13px; font-size: 12.5px; }

.acc-sub-now :focus-visible, .acc-plan :focus-visible, .ec-btn-primary:focus-visible, .ec-btn-ghost:focus-visible {
  outline: 2px solid var(--store-accent, #111); outline-offset: 2px;
}
@media (max-width: 720px) {
  .acc-sub-now { grid-template-columns: 1fr; justify-items: start; }
  .acc-sub-now-actions { justify-content: stretch; width: 100%; }
  .acc-sub-now-actions .ec-btn-primary, .acc-sub-now-actions .ec-btn-ghost { flex: 1; }
}
@media (max-width: 560px) {
  .acc-panel { padding: 16px; }
}
</style>
