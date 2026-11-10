<script setup>
// Página "Suscripciones" de la web pública (site_templates 'plans'):
// membresías, clubs o packs por suscripción que el negocio ofrece a SUS
// clientes. Es vista genérica compartida por todos los diseños — reusa la
// anatomía .sp-aipricing* (la misma del bloque 'plans' de la portada) y se
// esquina sola con los tokens de la piel activa. Solo publicidad: el alta
// se coordina por WhatsApp, la web nunca cobra.
// Si la página no está en los site_templates efectivos del plan la ruta
// rebota a la página disponible.
import { computed, inject, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeHostSlug } from '../../config/env.js'
import { storeContactLink, hasContactChannel } from '../../api/stores.api.js'
import { membershipPlansApi } from '../../api/membershipPlans.api.js'
import { formatARS } from '../../api/billing.api.js'
import { useCustomerStore } from '../../stores/customer.store.js'
import AppIcon from '../../components/AppIcon.vue'
import PlanSubscribe from '../../components/ecommerce/PlanSubscribe.vue'
import { vReveal } from '../../directives/reveal.js'

const ctx = inject('storePage')
const { custom, status, shopName, siteTemplates } = ctx
const router = useRouter()
const customer = useCustomerStore()

// Venta online efectiva (ecommerce_enabled + fiscal, calculada por el
// backend): solo con orders_enabled se muestran los StorePlan REALES —
// sin planes reales se conserva el contenido publicitario de siempre.
const ordersEnabled = computed(() => Boolean(ctx.ordersEnabled?.value ?? ctx.ordersEnabled))

const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${ctx.slug.value}` }))
const catalogTo = computed(() => ({ path: storeHostSlug ? '/catalogo' : `/${ctx.slug.value}/catalogo` }))
const servicesTo = computed(() => ({ path: storeHostSlug ? '/servicios' : `/${ctx.slug.value}/servicios` }))
const contactTo = computed(() => ({ path: homeTo.value.path, hash: '#contacto' }))

// Guard de la página: sin 'plans' en el set efectivo la ruta no existe
// (rebota a la primera página disponible, mismo criterio que Servicios).
watch([siteTemplates, status], () => {
  if (status.value !== 'success') return
  if (siteTemplates.value.includes('plans')) return
  const fallback = siteTemplates.value.includes('landing') ? homeTo.value
    : siteTemplates.value.includes('catalog') ? catalogTo.value
    : servicesTo.value
  router.replace(fallback)
}, { immediate: true })

const items = computed(() => (Array.isArray(custom.value.plans) ? custom.value.plans : []))
const title = computed(() => custom.value.plans_title?.trim() || 'Suscripciones y membresías')
const whatsappUrl = computed(() => (hasContactChannel(custom.value, 'whatsapp') ? storeContactLink(ctx.slug.value, 'whatsapp') : ''))
const hasLanding = computed(() => siteTemplates.value.includes('landing'))

// ---- Planes REALES (StorePlan) — solo si la tienda vende online ----
const realPlans = ref([])
const realPayments = ref(null)
const plansLoading = ref(false)
const plansError = ref('')
// Suscripción del comprador logueado en ESTA tienda (customer JWT) —
// solo para marcar el plan vigente/pendiente; nunca para calcular nada.
const mySub = ref(null)
const money = (v) => (Number(v) > 0 ? formatARS(v, 2) : 'Gratis')
const PERIOD_LABELS = { monthly: 'por mes', yearly: 'por año', custom: '' }
const periodLabel = (p) => PERIOD_LABELS[p?.period] || ''
// Códigos de beneficio del contrato (memberships/benefits.py) → label ES.
const BENEFIT_LABELS = {
  digital_card: 'Tarjeta digital de miembro',
  free_shipping: 'Envío gratis',
  exclusive_discounts: 'Descuentos exclusivos',
  exclusive_access: 'Acceso a contenido exclusivo',
}
const benefitLabel = (code) => BENEFIT_LABELS[code] || code

async function loadRealPlans() {
  if (!ordersEnabled.value) return
  plansLoading.value = true
  plansError.value = ''
  try {
    const data = await membershipPlansApi.publicPlans(ctx.slug.value)
    realPlans.value = data?.plans || []
    realPayments.value = data?.payments || null
  } catch {
    realPlans.value = []
    plansError.value = 'No pudimos cargar los planes.'
  } finally {
    plansLoading.value = false
  }
}

// GET /api/customer/subscriptions/<slug>/ devuelve {subscription} con
// is_vigente/plan/status — endpoint del COMPRADOR (customer JWT), no la
// sesión DAVENT. Sin sesión no se llama: la página sigue pública.
async function loadMySub() {
  if (!customer.isAuthenticated || !ordersEnabled.value) { mySub.value = null; return }
  try {
    const data = await membershipPlansApi.storePlans(ctx.slug.value)
    mySub.value = data?.subscription || null
  } catch { mySub.value = null }
}

function subFor(plan) {
  const s = mySub.value
  if (!s || !plan?.id || s.plan?.id !== plan.id) return null
  return s
}
// Badge honesto según el estado real de la suscripción del servidor.
function subBadge(plan) {
  const s = subFor(plan)
  if (!s) return null
  if (s.is_vigente) return { label: 'Plan vigente', icon: 'badge-check', cls: 'is-vigente' }
  if (s.status === 'pending') return { label: 'Pago pendiente', icon: 'clock', cls: 'is-pending' }
  if (s.status === 'past_due') return { label: 'Pago vencido', icon: 'circle-alert', cls: 'is-pending' }
  return null
}

watch([status, ordersEnabled, () => customer.isAuthenticated], ([s, on]) => {
  if (s === 'success' && on && !realPlans.value.length && !plansLoading.value) loadRealPlans()
  if (s === 'success' && on) loadMySub()
}, { immediate: true })
</script>

<template>
  <div class="sp-page-root sp-plans-page">
    <main id="plans-main" class="sp-plans-main">
      <header class="sp-container sp-plans-hero" v-reveal>
        <p class="sp-plans-eyebrow"><AppIcon name="crown" :size="14" aria-hidden="true" /> {{ shopName }}</p>
        <h1 class="sp-section-title sp-plans-title">{{ title }}</h1>
        <p class="sp-plans-sub">{{ realPlans.length ? 'Elegí tu plan y suscribite online — los beneficios se activan al acreditarse el pago.' : 'Elegí el plan que mejor te quede y escribinos para sumarte. La suscripción se coordina directo con el negocio — no se cobra por la web.' }}</p>
      </header>

      <!-- Planes reales con venta online (StorePlan) -->
      <section v-if="ordersEnabled && realPlans.length" class="sp-aipricing" aria-label="Planes disponibles">
        <div class="sp-container sp-aipricing-inner">
          <ul class="sp-aipricing-list">
            <li v-for="(plan, i) in realPlans" :key="plan.id" v-reveal="(i % 4) * 70" class="sp-aipricing-card sp-plan-real">
              <span v-if="subBadge(plan)" class="sp-plan-badge" :class="subBadge(plan).cls">
                <AppIcon :name="subBadge(plan).icon" :size="12" aria-hidden="true" /> {{ subBadge(plan).label }}
              </span>
              <h2 class="sp-aipricing-name">{{ plan.name }}</h2>
              <span class="sp-aipricing-amount">{{ money(plan.price) }}<small v-if="plan.period_days" class="sp-plan-period"> / {{ plan.period_days }} días{{ periodLabel(plan) ? ` · ${periodLabel(plan)}` : '' }}</small></span>
              <ul v-if="plan.benefits?.length || plan.discount_percent" class="sp-aipricing-feats">
                <li v-for="b in plan.benefits || []" :key="b">
                  <AppIcon name="check" :size="14" :stroke="2.6" />
                  <span>{{ benefitLabel(b) }}</span>
                </li>
                <li v-if="plan.discount_percent">
                  <AppIcon name="check" :size="14" :stroke="2.6" />
                  <span>{{ plan.discount_percent }}% de descuento de miembro</span>
                </li>
              </ul>
              <PlanSubscribe :slug="ctx.slug.value" :plan="plan" :payments="realPayments" :subscription="subFor(plan)" @subscribed="loadMySub" />
            </li>
          </ul>
        </div>
      </section>
      <section v-else-if="ordersEnabled && plansLoading" class="sp-container sp-plans-skel" aria-busy="true" aria-label="Cargando planes">
        <div v-for="n in 3" :key="n" class="sp-plan-skel-card">
          <span class="sp-sk-line sp-sk-title"></span>
          <span class="sp-sk-line"></span>
          <span class="sp-sk-line short"></span>
          <span class="sp-sk-line"></span>
          <span class="sp-sk-line sp-sk-btn"></span>
        </div>
      </section>
      <section v-else-if="ordersEnabled && plansError" class="sp-container sp-plans-empty" role="alert">
        <AppIcon name="circle-alert" :size="26" aria-hidden="true" />
        <p><strong>{{ plansError }}</strong></p>
        <p>Revisá tu conexión y probá de nuevo.</p>
        <button type="button" class="sp-plans-btn sp-plans-retry" @click="loadRealPlans">Reintentar</button>
      </section>

      <section v-if="!realPlans.length && items.length" class="sp-aipricing" aria-label="Planes disponibles">
        <div class="sp-container sp-aipricing-inner">
          <ul class="sp-aipricing-list">
            <li v-for="(plan, i) in items" :key="`${i}-${plan.name}`" v-reveal="(i % 4) * 70" class="sp-aipricing-card">
              <h2 class="sp-aipricing-name">{{ plan.name }}</h2>
              <span v-if="plan.price" class="sp-aipricing-amount">{{ plan.price }}</span>
              <p v-if="plan.note" class="sp-aipricing-note">{{ plan.note }}</p>
              <ul v-if="plan.items?.length" class="sp-aipricing-feats">
                <li v-for="(f, fi) in plan.items" :key="`${fi}-${f}`">
                  <AppIcon name="check" :size="14" :stroke="2.6" />
                  <span>{{ f }}</span>
                </li>
              </ul>
            </li>
          </ul>
        </div>
      </section>

      <section v-if="!realPlans.length && !items.length && !(ordersEnabled && plansLoading)" class="sp-container sp-plans-empty" v-reveal>
        <AppIcon name="crown" :size="26" aria-hidden="true" />
        <p><strong>Todavía no hay suscripciones publicadas.</strong></p>
        <p>Cuando el negocio cargue sus planes van a aparecer acá. Mientras tanto podés contactarlo desde la página principal.</p>
      </section>

      <footer class="sp-container sp-plans-cta" v-reveal>
        <a v-if="whatsappUrl" class="sp-plans-btn is-wa" :href="whatsappUrl" target="_blank" rel="noopener">
          <AppIcon name="whatsapp" :size="17" aria-hidden="true" /> Consultar por WhatsApp
        </a>
        <RouterLink v-else-if="hasLanding" class="sp-plans-btn" :to="contactTo">
          <AppIcon name="message-circle" :size="17" aria-hidden="true" /> Contactanos
        </RouterLink>
        <RouterLink v-if="hasLanding" class="sp-plans-link" :to="homeTo">Volver al inicio</RouterLink>
      </footer>
    </main>
  </div>
</template>

<style>
/* Página genérica "Suscripciones": se esquina con los tokens de la piel
   (--sp-*, --st-*) igual que el bloque 'plans' de la portada — no lleva
   piel propia, así que todos los diseños la heredan coherentes. */
.sp-plans-main{ min-height: 40vh; }
.sp-plans-hero{ padding: clamp(40px, 6vw, 72px) 0 8px; display: grid; gap: 10px; }
.sp-plans-eyebrow{ display: inline-flex; align-items: center; gap: 6px; margin: 0; font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--sp-accent-text, var(--sp-ink-2)); }
.sp-plans-title{ margin: 0; }
.sp-plans-sub{ margin: 0; max-width: 60ch; font-size: 15px; line-height: 1.6; color: var(--sp-muted); }
.sp-plans-page .sp-aipricing{ padding-top: 28px; }
.sp-plans-empty{ margin-top: 28px; display: grid; gap: 8px; justify-items: start; padding: 28px; border: 1px dashed var(--sp-line); border-radius: var(--r-md, 16px); color: var(--sp-muted); }
.sp-plans-empty svg{ color: var(--sp-accent-text, var(--sp-muted)); }
.sp-plans-empty p{ margin: 0; font-size: 14px; line-height: 1.6; }
.sp-plans-cta{ display: flex; align-items: center; flex-wrap: wrap; gap: 12px; padding: 32px 0 72px; }
.sp-plans-btn{ display: inline-flex; align-items: center; gap: 8px; padding: 11px 18px; border-radius: var(--r-sm, 10px); font-size: 14px; font-weight: 700; text-decoration: none; background: var(--sp-accent, var(--sp-ink)); color: var(--sp-accent-ink, var(--sp-bg)); border: 1px solid transparent; }
.sp-plans-btn.is-wa{ background: #25d366; color: #0b3d22; }
.sp-plans-link{ font-size: 14px; font-weight: 600; color: var(--sp-muted); text-decoration: none; }
.sp-plans-link:hover{ color: var(--sp-ink); }
.sp-plan-real{ display: grid; gap: 12px; align-content: start; position: relative; }
.sp-plan-period{ font-size: .55em; font-weight: 600; opacity: .75; }
/* Badge de suscripción del comprador (estado real del servidor) */
.sp-plans-page .sp-plan-badge{ display: inline-flex; align-items: center; gap: 5px; justify-self: start; padding: 4px 10px; border-radius: 999px; font-size: 11.5px; font-weight: 800; letter-spacing: .02em; }
.sp-plans-page .sp-plan-badge.is-vigente{ background: color-mix(in srgb, var(--sp-success, #0E7A55) 15%, transparent); color: var(--sp-success, #0E7A55); }
.sp-plans-page .sp-plan-badge.is-pending{ background: color-mix(in srgb, var(--sp-warning, #B45309) 14%, transparent); color: var(--sp-warning, #B45309); }
/* Skeleton de carga de planes */
.sp-plans-page .sp-plans-skel{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 18px; margin-top: 28px; }
.sp-plans-page .sp-plan-skel-card{ display: grid; gap: 12px; align-content: start; padding: 22px; border: 1px solid var(--sp-line); border-radius: var(--r-md, 16px); }
.sp-plans-page .sp-sk-line{ display: block; height: 12px; border-radius: 8px; background: color-mix(in srgb, var(--sp-muted) 16%, transparent); }
.sp-plans-page .sp-sk-title{ width: 55%; height: 18px; }
.sp-plans-page .sp-sk-line.short{ width: 60%; }
.sp-plans-page .sp-sk-btn{ width: 100%; height: 42px; border-radius: var(--r-sm, 10px); margin-top: 8px; }
@media (prefers-reduced-motion: no-preference){
  .sp-plans-page .sp-sk-line{ animation: sp-plans-shimmer 1.4s ease-in-out infinite; }
  .sp-plans-page .sp-plan-skel-card:nth-child(2) .sp-sk-line{ animation-delay: .12s; }
  .sp-plans-page .sp-plan-skel-card:nth-child(3) .sp-sk-line{ animation-delay: .24s; }
  @keyframes sp-plans-shimmer{ 0%,100%{ opacity: 1; } 50%{ opacity: .45; } }
}
.sp-plans-retry{ border: 1px solid var(--sp-line); background: transparent; color: var(--sp-ink); cursor: pointer; font: inherit; }
@media (max-width: 560px){ .sp-plans-page .sp-plans-skel{ grid-template-columns: 1fr; } }
</style>
