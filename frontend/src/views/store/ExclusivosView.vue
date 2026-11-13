<script setup>
// Página "Exclusivos" de la web pública: productos is_exclusive de la
// tienda, solo para compradores con membresía vigente que incluya
// acceso exclusivo (memberships: has_exclusive_access). Sin sesión o sin
// beneficio → teaser de membresía + CTA a /suscripciones (el endpoint
// responde 404 y jamás revela el catálogo). La tarjeta no tiene ficha
// pública (is_exclusive sale del catálogo/doc), así que el click agrega
// directo al carrito — el server re-valida el acceso en cart/checkout.
import { computed, inject, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeHostSlug } from '../../config/env.js'
import { membershipPlansApi } from '../../api/membershipPlans.api.js'
import { useCustomerStore } from '../../stores/customer.store.js'
import { useCartStore } from '../../stores/cart.store.js'
import AppIcon from '../../components/AppIcon.vue'
import TplProductCard from '../../components/store/TplProductCard.vue'
import { vReveal } from '../../directives/reveal.js'

const ctx = inject('storePage')
const { status, shopName, siteTemplates } = ctx
const router = useRouter()
const customer = useCustomerStore()
const cart = useCartStore()

const enabled = computed(() => Boolean(ctx.store?.value?.exclusive_enabled ?? ctx.store?.exclusive_enabled))

const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${ctx.slug.value}` }))
const plansTo = computed(() => ({ path: storeHostSlug ? '/suscripciones' : `/${ctx.slug.value}/suscripciones` }))
const accountTo = computed(() => ({ path: storeHostSlug ? '/cuenta' : `/${ctx.slug.value}/cuenta` }))

// Guard: la tienda sin sección exclusiva no tiene esta página (rebota a
// inicio, mismo criterio que Suscripciones con site_templates).
watch([status, enabled], ([s, on]) => {
  if (s === 'success' && !on) router.replace(homeTo.value)
}, { immediate: true })

const products = ref([])
const state = ref('idle')   // idle | loading | ok | denied | error

async function load() {
  if (!enabled.value || !customer.isAuthenticated) { state.value = 'idle'; return }
  state.value = 'loading'
  try {
    const data = await membershipPlansApi.exclusiveProducts(ctx.slug.value)
    products.value = data?.products || []
    state.value = 'ok'
  } catch (e) {
    if (e?.response?.status === 404) state.value = 'denied'
    else state.value = 'error'
  }
}
watch([status, enabled, () => customer.isAuthenticated], ([s, on, auth]) => {
  if (s === 'success' && on && auth && !products.value.length && state.value !== 'loading') load()
}, { immediate: true })

function login() {
  cart.openAuth('login', { route: { path: router.currentRoute.value.fullPath } })
}

const buyBusy = ref(null)
async function buy(p) {
  if (buyBusy.value) return
  buyBusy.value = p.id
  try { await cart.addToCart(p.id, 1) }
  finally { buyBusy.value = null }
}
</script>

<template>
  <div class="sp-page-root sp-ex-page">
    <main id="ex-main" class="sp-ex-main">
      <header class="sp-container sp-ex-hero" v-reveal>
        <p class="sp-ex-eyebrow"><AppIcon name="percent" :size="14" aria-hidden="true" /> {{ shopName }}</p>
        <h1 class="sp-section-title sp-ex-title">Descuentos exclusivos</h1>
        <p class="sp-ex-sub">Productos y ofertas reservados para miembros de la tienda.</p>
      </header>

      <!-- Invitado: la sección existe pero el contenido es para miembros -->
      <section v-if="!customer.isAuthenticated && state !== 'loading'" class="sp-container sp-ex-lock" v-reveal>
        <AppIcon name="lock" :size="26" aria-hidden="true" />
        <p><strong>Esta sección es para miembros.</strong></p>
        <p>Ingresá con tu cuenta — si ya sos miembro vas a ver acá los productos y descuentos exclusivos; si no, podés suscribirte para desbloquearlos.</p>
        <div class="sp-ex-actions">
          <button type="button" class="sp-plans-btn" @click="login"><AppIcon name="user" :size="16" aria-hidden="true" /> Ingresar</button>
          <RouterLink class="sp-plans-link" :to="plansTo">Ver membresías</RouterLink>
        </div>
      </section>

      <!-- Logueado sin acceso: membresía vigente sin el beneficio o sin plan -->
      <section v-else-if="state === 'denied'" class="sp-container sp-ex-lock" v-reveal>
        <AppIcon name="crown" :size="26" aria-hidden="true" />
        <p><strong>Tu cuenta todavía no tiene acceso exclusivo.</strong></p>
        <p>El acceso viene con las membresías que lo incluyen — revisá los planes de la tienda o el estado de tu suscripción.</p>
        <div class="sp-ex-actions">
          <RouterLink class="sp-plans-btn" :to="plansTo"><AppIcon name="crown" :size="16" aria-hidden="true" /> Ver membresías</RouterLink>
          <RouterLink class="sp-plans-link" :to="accountTo">Mi cuenta</RouterLink>
        </div>
      </section>

      <section v-else-if="state === 'loading'" class="sp-container sp-plans-skel" aria-busy="true" aria-label="Cargando exclusivos">
        <div v-for="n in 4" :key="n" class="sp-plan-skel-card"><span class="sp-sk-line sp-sk-title"></span><span class="sp-sk-line"></span><span class="sp-sk-line short"></span><span class="sp-sk-line sp-sk-btn"></span></div>
      </section>

      <section v-else-if="state === 'error'" class="sp-container sp-plans-empty" role="alert">
        <AppIcon name="circle-alert" :size="26" aria-hidden="true" />
        <p><strong>No pudimos cargar los exclusivos.</strong></p>
        <button type="button" class="sp-plans-btn sp-plans-retry" @click="load">Reintentar</button>
      </section>

      <!-- Catálogo exclusivo del miembro -->
      <section v-else-if="state === 'ok'" class="sp-container">
        <p v-if="!products.length" class="sp-plans-empty" style="width:100%">
          <AppIcon name="package" :size="26" aria-hidden="true" />
          <strong>Todavía no hay productos exclusivos publicados.</strong>
          Cuando la tienda cargue ofertas para miembros aparecen acá.
        </p>
        <template v-else>
          <p class="sp-ex-hint">Tocá un producto para agregarlo al carrito — tu descuento de miembro se aplica en el checkout.</p>
          <ul class="sp-ex-grid">
            <li v-for="(p, i) in products" :key="p.id" v-reveal="(i % 4) * 60">
              <TplProductCard :p="p" :cat="p.category_name || ''" :brand="p.brand_name || ''" @open="buy(p)" />
              <p v-if="buyBusy === p.id" class="sp-ex-busy"><AppIcon name="loader" :size="13" aria-hidden="true" /> Agregando…</p>
            </li>
          </ul>
        </template>
      </section>

      <footer class="sp-container sp-plans-cta" v-reveal>
        <RouterLink class="sp-plans-link" :to="homeTo">Volver al inicio</RouterLink>
      </footer>
    </main>
  </div>
</template>

<style>
.sp-ex-main{ min-height: 40vh; }
.sp-ex-hero{ padding: clamp(40px, 6vw, 72px) 0 8px; display: grid; gap: 10px; }
.sp-ex-eyebrow{ display: inline-flex; align-items: center; gap: 6px; margin: 0; font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--sp-accent-text, var(--sp-ink-2)); }
.sp-ex-title{ margin: 0; }
.sp-ex-sub{ margin: 0; max-width: 60ch; font-size: 15px; line-height: 1.6; color: var(--sp-muted); }
.sp-ex-lock{ margin-top: 28px; display: grid; gap: 8px; justify-items: start; padding: 28px; border: 1px dashed var(--sp-line); border-radius: var(--r-md, 16px); color: var(--sp-muted); }
.sp-ex-lock svg{ color: var(--sp-accent-text, var(--sp-muted)); }
.sp-ex-lock p{ margin: 0; font-size: 14px; line-height: 1.6; }
.sp-ex-actions{ display: flex; align-items: center; flex-wrap: wrap; gap: 12px; margin-top: 8px; }
.sp-ex-hint{ margin: 18px 0 14px; font-size: 13px; color: var(--sp-muted); }
.sp-ex-grid{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 18px; list-style: none; margin: 0 0 24px; padding: 0; }
.sp-ex-grid li{ min-width: 0; }
.sp-ex-busy{ display: inline-flex; align-items: center; gap: 6px; margin: 6px 2px 0; font-size: 12.5px; font-weight: 600; color: var(--sp-muted); }
@media (max-width: 560px){ .sp-ex-grid{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; } }
</style>
