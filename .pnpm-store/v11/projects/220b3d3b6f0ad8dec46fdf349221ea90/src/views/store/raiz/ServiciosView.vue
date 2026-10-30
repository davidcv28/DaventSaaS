<script setup>
// Página "Servicios" de la web pública (site_templates), con la dirección de
// arte Raíz v2: numeración editorial, reglas hairline y presupuesto en un
// panel sticky. Implementa el embudo de pedido por servicios: el visitante
// marca los que necesita, ve el presupuesto orientativo animado y confirma el
// pedido por WhatsApp. Regla dura del producto: la web NUNCA persiste
// reservas, pedidos ni pagos — el mensaje se arma en el cliente y se abre en
// wa.me; el pago se hace en persona (service_pay_note lo explica en la
// tarjeta de precio). Los ítems llegan en el payload público
// (store.service_items, solo activos); si la página no está en los
// site_templates efectivos del plan la ruta rebota a la página disponible.
import { ref, computed, inject, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { storeHostSlug } from '../../../config/env.js'
import { buildServiceRequestMessage, servicePriceLabel } from '../../../api/services.api.js'
import { SERVICE_ICONS } from '../../../api/stores.api.js'
import AppIcon from '../../../components/AppIcon.vue'
import { useLayout } from '../../../composables/useLayout.js'
import { resolveSiteTheme } from '../../../studio/contract.js'
import { vReveal } from '../../../directives/reveal.js'

const ctx = inject('storePage')
// Layout de la superficie 'services': el editor (Diseño web → Bloques)
// apaga/ordena las regiones del catálogo cerrado. Raíz v2 compone las
// secciones con una sola retícula editorial: el orden se respeta y las
// variantes de picker del Studio quedan fuera (composición fija, §3 del
// prompt de corrección).
const { on, pos, st } = useLayout('services')
const ord = (id) => { const p = pos(id); return p === 999 ? pos('form') : p }
const blkTitle = (id, fallback) => st(id).props?.title || fallback
const router = useRouter()
const { custom, store, status, shopName, location, siteTemplates } = ctx

// Guard de la página: sin 'services' en el set efectivo la ruta no existe
// (rebota al catálogo si lo hay, si no a la portada — el watch del layout
// se encarga si tampoco hay landing).
const catalogTo = computed(() => ({ path: storeHostSlug ? '/catalogo' : `/${ctx.slug.value}/catalogo` }))
const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${ctx.slug.value}` }))
watch([siteTemplates, status], () => {
  if (status.value !== 'success') return
  if (!siteTemplates.value.includes('services')) {
    router.replace(siteTemplates.value.includes('catalog') ? catalogTo.value : homeTo.value)
  }
}, { immediate: true })

// ===== Ítems y selección =====
const items = computed(() => (status.value === 'success' ? store.value?.service_items || [] : []))
const chosen = ref(new Set()) // ids marcados por el visitante
function toggle(id) {
  const next = new Set(chosen.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  chosen.value = next
}
const chosenItems = computed(() => items.value.filter((it) => chosen.value.has(it.id)))
function clearAll() { chosen.value = new Set() }
// Ícono del catálogo cerrado del panel (SERVICE_ICONS); fallback genérico.
const serviceIcon = (key) => (SERVICE_ICONS[key] ? key : 'wrench')
// Solo los servicios con precio cargado entran al total (null = "a convenir").
const total = computed(() => chosenItems.value.reduce((sum, it) => sum + Number(it.price || 0), 0))
const hasUnpriced = computed(() => chosenItems.value.some((it) => it.price == null))

// Total animado: count-up corto con easing (450ms), salteado con
// prefers-reduced-motion. El número mostrado es shownTotal.
const shownTotal = ref(0)
let raf = null
function tweenTotal(to) {
  cancelAnimationFrame(raf)
  const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
  if (reduce) { shownTotal.value = to; return }
  const from = shownTotal.value
  const t0 = performance.now()
  const dur = 450
  function step(ts) {
    const p = Math.min((ts - t0) / dur, 1)
    const e = 1 - Math.pow(1 - p, 3)
    shownTotal.value = from + (to - from) * e
    if (p < 1) raf = requestAnimationFrame(step)
  }
  raf = requestAnimationFrame(step)
}
watch(total, tweenTotal)
onBeforeUnmount(() => cancelAnimationFrame(raf))
const fmt = (n) => `$ ${Math.round(Number(n) || 0).toLocaleString('es-AR')}`

// ===== Config de la página (customization.service_*) =====
const priceNote = computed(() => custom.value.service_price_note || 'Los precios son orientativos: el valor final se confirma por WhatsApp.')
const payNote = computed(() => custom.value.service_pay_note || 'Se paga en persona, al concretar el servicio. Nada se cobra por la web.')
const askAddress = computed(() => custom.value.service_ask_address !== false)
const steps = computed(() => {
  const saved = Array.isArray(custom.value.service_steps) ? custom.value.service_steps : []
  if (saved.length) return saved
  return [
    { icon: 'message-circle', title: 'Elegís tus servicios', text: 'Marcá lo que necesitás y mirá el presupuesto orientativo al instante.' },
    { icon: 'whatsapp', title: 'Confirmamos por WhatsApp', text: 'Nos llega tu pedido con el detalle y coordinamos día y horario.' },
    { icon: 'wallet', title: 'Pagás en persona', text: 'Nada se cobra por la web: el pago se hace cara a cara al concretar.' }
  ]
})
const days = computed(() => {
  const saved = Array.isArray(custom.value.service_days) ? custom.value.service_days.filter(Boolean) : []
  return saved.length ? saved : ['Hoy', 'Mañana', 'Esta semana', 'Otro día']
})
const slots = computed(() => {
  const saved = Array.isArray(custom.value.service_slots) ? custom.value.service_slots.filter(Boolean) : []
  return saved.length ? saved : ['Mañana (9 a 12 h)', 'Mediodía (12 a 15 h)', 'Tarde (15 a 18 h)']
})
const faqs = computed(() => (custom.value.show_faq !== false && Array.isArray(custom.value.faqs) ? custom.value.faqs : []))
const perks = computed(() => (custom.value.show_benefits !== false && Array.isArray(custom.value.benefits) ? custom.value.benefits : []))
const works = computed(() => (custom.value.show_gallery !== false && Array.isArray(custom.value.gallery) ? custom.value.gallery : []))
const testis = computed(() => (custom.value.show_testimonials !== false && Array.isArray(custom.value.testimonials) ? custom.value.testimonials : []))
const testisTitle = computed(() => custom.value.testimonials_title?.trim() || 'Lo que dicen los clientes')
const contactHours = computed(() => (custom.value.show_hours !== false && Array.isArray(custom.value.hours) ? custom.value.hours : []))
// Cobertura: la zona sale del dato de ubicación; "a domicilio" se infiere
// cuando el pedido pide dirección (service_ask_address).
const showZone = computed(() => Boolean(location.value) || contactHours.value.length > 0 || custom.value.service_ask_address !== false)
const perkIcon = (key) => (SERVICE_ICONS[key] ? key : 'shield-check')
// Cinta marquee con los nombres de los servicios (duplicada para el loop).
const bandItems = computed(() => {
  const names = items.value.map((it) => it.name)
  return names.length >= 2 ? [...names, ...names] : []
})

// ===== WhatsApp =====
const whatsapp = computed(() => String(custom.value.whatsapp || '').replace(/\D/g, ''))
const waBase = computed(() => (whatsapp.value ? `https://wa.me/${whatsapp.value}` : ''))
// Botón flotante de WhatsApp (solo desktop: en móvil ya están el dock y la
// barra de presupuesto). Posición y forma configurables vía
// custom.service_wa_*; con chatbot el default es 'left' para no pisarlo.
const botOn = computed(() => Boolean(store.value?.chatbot))
const waFloat = computed(() => Boolean(waBase.value) && custom.value.service_wa_float !== false)
const waPos = computed(() => (
  ['left', 'right'].includes(custom.value.service_wa_pos) ? custom.value.service_wa_pos : (botOn.value ? 'left' : 'right')
))
const waShape = computed(() => (['pill', 'square'].includes(custom.value.service_wa_shape) ? custom.value.service_wa_shape : 'circle'))

// ===== Formulario de pedido =====
const form = ref({ name: '', phone: '', address: '', day: '', slot: '' })
const errors = ref({})
const sentOk = ref(false)
function submit() {
  const e = {}
  const f = form.value
  if (f.name.trim().length < 2) e.name = 'Escribí tu nombre.'
  if (f.phone.replace(/\D/g, '').length < 8) e.phone = 'Un número de WhatsApp válido, por favor.'
  if (askAddress.value && f.address.trim().length < 6) e.address = 'Necesitamos una dirección para coordinar.'
  if (!f.day) e.day = 'Elegí un día.'
  if (!f.slot) e.slot = 'Elegí una franja.'
  pickError.value = items.value.length && !chosenItems.value.length ? 'Elegí al menos un servicio arriba para armar tu pedido.' : ''
  if (pickError.value) e.pick = pickError.value
  errors.value = e
  if (Object.keys(e).length) {
    sentOk.value = false
    // Sin esto el error queda fuera de pantalla y el botón parece no responder.
    nextTick(() => document.querySelector('.rz-sv-form .bad, .rz-sv-form .rz-sv-sel.bad')?.scrollIntoView({ block: 'center', behavior: reduceMotion() ? 'auto' : 'smooth' }))
    return
  }
  if (!waBase.value) return
  const message = buildServiceRequestMessage({
    shopName: shopName.value,
    items: chosenItems.value,
    total: total.value,
    visitor: f
  })
  const url = `${waBase.value}?text=${encodeURIComponent(message)}`
  // Con 'noopener' window.open devuelve SIEMPRE null aunque la pestaña se
  // abra (spec) — el fallback navegaba la web a wa.me en todos los envíos.
  // Se abre sin noopener y se corta el opener a mano; null real = popup
  // bloqueado → fallback a la misma pestaña (wa.me abre la app).
  const w = window.open(url, '_blank')
  if (!w || w.closed) window.location.href = url
  else { try { w.opener = null } catch { /* cross-origin: no hace falta */ } }
  sentOk.value = true
}

// Scroll interno suave (los ids son locales a la página).
const reduceMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
function scrollTo(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: reduceMotion() ? 'auto' : 'smooth', block: 'start' })
}

// ===== Recorrido del pedido y barra móvil =====
// Recorrido: 1 elegir → 2 pedir → 3 enviado (se marca solo según el estado).
const flow = computed(() => {
  const at = sentOk.value ? 3 : chosenItems.value.length ? 2 : 1
  return [
    { icon: 'checklist', label: 'Elegí servicios' },
    { icon: 'send', label: 'Dejá tus datos' },
    { icon: 'whatsapp', label: 'Confirmá por WhatsApp' }
  ].map((s, i) => ({ ...s, n: i + 1, state: i + 1 < at ? 'done' : i + 1 === at ? 'now' : 'todo' }))
})

// El total "salta" un poco cada vez que cambia el presupuesto.
const bump = ref(false)
let bumpT = null
watch(total, () => {
  bump.value = false
  clearTimeout(bumpT)
  requestAnimationFrame(() => { bump.value = true; bumpT = setTimeout(() => { bump.value = false }, 500) })
})
onBeforeUnmount(() => clearTimeout(bumpT))

// Barra inferior (solo móvil): total + CTA mientras hay selección y el
// formulario de pedido todavía no está a la vista.
const formInView = ref(false)
const quoteInView = ref(false)
let formIO = null
function observeTargets() {
  formIO?.disconnect()
  if (!('IntersectionObserver' in window)) return
  formIO = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.target.id === 'sv-pedido') formInView.value = e.isIntersecting
      else quoteInView.value = e.isIntersecting
    })
  })
  ;['sv-pedido', 'sv-quote'].forEach((id) => { const el = document.getElementById(id); if (el) formIO.observe(el) })
}
// Barra CTA fija en móvil: con selección muestra el presupuesto (abre la
// hoja); sin selección solo persiste si el tema Studio activa
// mobile.stickyCta — el main ya reserva el espacio, no tapa contenido.
const stickyCta = computed(() => resolveSiteTheme(custom.value.site_theme).mobile?.stickyCta === true)
const showBar = computed(() => (chosenItems.value.length > 0
  ? !formInView.value && !quoteInView.value
  : stickyCta.value && items.value.length > 0 && !formInView.value))
watch(items, () => nextTick(observeTargets), { immediate: false })
onMounted(() => nextTick(observeTargets))
onBeforeUnmount(() => formIO?.disconnect())

// Hoja de detalle del presupuesto (bottom-sheet móvil): la barra la abre;
// foco atrapado dentro, cierre con Esc o tocando el fondo.
const sheetOpen = ref(false)
const sheetEl = ref(null)
let sheetPrevFocus = null
function openSheet() {
  sheetPrevFocus = document.activeElement
  sheetOpen.value = true
  document.documentElement.classList.add('sp-lock')
  nextTick(() => (sheetEl.value?.querySelector('button:not([disabled])') || sheetEl.value)?.focus())
}
function closeSheet() {
  sheetOpen.value = false
  document.documentElement.classList.remove('sp-lock')
  sheetPrevFocus?.focus?.()
  sheetPrevFocus = null
}
function onSheetKeydown(e) {
  if (e.key === 'Escape') { closeSheet(); return }
  if (e.key !== 'Tab') return
  const list = sheetEl.value?.querySelectorAll('button:not([disabled]), a[href], input, [tabindex]:not([tabindex="-1"])')
  if (!list?.length) return
  const first = list[0]
  const last = list[list.length - 1]
  if (e.shiftKey ? document.activeElement === first : document.activeElement === last) {
    (e.shiftKey ? last : first).focus()
    e.preventDefault()
  }
}
watch(showBar, (v) => { if (!v && sheetOpen.value) closeSheet() })
onBeforeUnmount(() => { if (sheetOpen.value) document.documentElement.classList.remove('sp-lock') })

const pickError = ref('')
watch(chosenItems, (v) => { if (v.length) pickError.value = '' })
</script>

<template>
  <div class="sp-page-root rz-sv-page">
    <main id="sv-main">
      <!-- ===== Hero editorial ===== -->
      <div v-if="on('hero')" data-blk="hero" class="rz-sv-block rz-sv-hero" :style="{ order: pos('hero') }">
        <div class="rz-sv-wrap">
          <nav class="rz-sv-crumbs" aria-label="Ruta">
            <RouterLink :to="homeTo">Inicio</RouterLink>
            <span aria-hidden="true">/</span>
            <span aria-current="page">Servicios</span>
          </nav>
          <div class="rz-sv-hero-grid">
            <div class="rz-sv-hero-copy">
              <p class="rz-eyebrow"><span class="rz-eyebrow-num">01</span> Servicios</p>
              <h1 class="rz-sv-title">Servicios de <span class="rz-sv-mark">{{ shopName }}</span>, sin vueltas.</h1>
              <p class="rz-sv-lead">Elegí lo que necesitás, mirá el presupuesto orientativo y confirmamos todo por WhatsApp. Sin pagos online.</p>
              <div class="rz-sv-hero-cta">
                <button type="button" class="rz-btn" @click="scrollTo('sv-servicios')">
                  Ver servicios y precios <AppIcon name="arrow-right" :size="16" aria-hidden="true" />
                </button>
                <a v-if="waBase" class="rz-btn rz-btn--ghost" :href="waBase" target="_blank" rel="noopener">
                  <AppIcon name="whatsapp" :size="17" aria-hidden="true" /> Escribinos
                </a>
              </div>
              <ul class="rz-sv-trust" aria-label="Por qué pedir acá">
                <li><AppIcon name="shield-check" :size="16" aria-hidden="true" /> Sin pago online</li>
                <li><AppIcon name="clock" :size="16" aria-hidden="true" /> Respuesta por WhatsApp</li>
                <li v-if="items.length"><AppIcon name="checklist" :size="16" aria-hidden="true" /> {{ items.length }} {{ items.length === 1 ? 'servicio' : 'servicios' }}</li>
              </ul>
            </div>
            <aside class="rz-sv-hero-side">
              <span class="rz-plate rz-sv-plate">Pagás en persona</span>
              <div class="rz-sv-hero-card">
                <p class="rz-sv-hero-kicker">Servicios publicados</p>
                <p class="rz-sv-hero-num">{{ items.length }}</p>
                <p v-if="location" class="rz-sv-hero-loc"><AppIcon name="map-pin" :size="14" aria-hidden="true" /> {{ location }}</p>
                <p class="rz-sv-hero-note">Presupuesto orientativo · la web nunca cobra ni guarda tarjetas.</p>
              </div>
            </aside>
          </div>
        </div>
      </div>

      <!-- ===== Cinta marquee con los servicios ===== -->
      <div v-if="bandItems.length && on('band')" data-blk="band" class="rz-sv-band" :style="{ order: pos('band') }" aria-hidden="true">
        <div class="rz-sv-band-track">
          <span v-for="(n, i) in bandItems" :key="i">{{ n }} <i aria-hidden="true">·</i></span>
        </div>
      </div>

      <!-- ===== Picker + presupuesto (bloque 'picker', estructural) ===== -->
      <div class="rz-sv-block" data-blk="picker" :style="{ order: pos('picker') }">
        <section id="sv-servicios" class="rz-sv-wrap rz-sv-section" aria-labelledby="sv-svc-title">
          <header class="rz-sv-head">
            <p class="rz-eyebrow"><span class="rz-eyebrow-num">02</span> Elegí y sumá</p>
            <div class="rz-sv-head-row">
              <h2 id="sv-svc-title">{{ blkTitle('picker', 'Elegí lo que necesitás y mirá el total.') }}</h2>
              <p class="rz-sv-head-note">{{ priceNote }}</p>
            </div>
          </header>

          <ol class="rz-sv-flow" aria-label="Pasos del pedido">
            <li v-for="s in flow" :key="s.n" :class="`is-${s.state}`" :aria-current="s.state === 'now' ? 'step' : undefined">
              <span class="rz-sv-flow-num" aria-hidden="true">
                <AppIcon v-if="s.state === 'done'" name="check" :size="14" :stroke="2.6" />
                <template v-else>{{ s.n }}</template>
              </span>
              <span class="rz-sv-flow-lbl">{{ s.label }}</span>
            </li>
          </ol>

          <div v-if="!items.length" class="rz-sv-empty">
            <span class="rz-sv-empty-ico" aria-hidden="true"><AppIcon name="wrench" :size="28" /></span>
            <strong>Todavía no hay servicios publicados.</strong>
            <p>Cuando el negocio cargue su lista, acá vas a poder armar tu presupuesto.</p>
          </div>

          <div v-else class="rz-sv-picker">
            <div class="rz-sv-choices">
              <div class="rz-sv-pickbar">
                <span class="rz-sv-pickcount" aria-live="polite">
                  <AppIcon name="checklist" :size="16" aria-hidden="true" />
                  <template v-if="chosenItems.length"><b>{{ chosenItems.length }}</b>&nbsp;de {{ items.length }} elegidos</template>
                  <template v-else>{{ items.length }} {{ items.length === 1 ? 'servicio disponible' : 'servicios disponibles' }} — tocá para elegir</template>
                </span>
                <button v-if="chosenItems.length" type="button" class="rz-sv-pickclear" @click="clearAll">
                  <AppIcon name="x" :size="13" :stroke="2.4" aria-hidden="true" /> Limpiar
                </button>
              </div>

              <ol class="rz-sv-items" aria-label="Servicios disponibles">
                <li v-for="(it, i) in items" :key="it.id">
                  <button
                    type="button" class="rz-sv-item" v-reveal="Math.min(i, 8) * 40"
                    :aria-pressed="chosen.has(it.id)" @click="toggle(it.id)"
                  >
                    <span class="rz-sv-item-num" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
                    <span class="rz-sv-item-ico" aria-hidden="true"><AppIcon :name="serviceIcon(it.icon)" :size="20" /></span>
                    <span class="rz-sv-item-txt">
                      <strong>{{ it.name }}</strong>
                      <small v-if="it.description">{{ it.description }}</small>
                      <span v-if="it.duration" class="rz-sv-item-dur"><AppIcon name="clock" :size="12" aria-hidden="true" /> {{ it.duration }}</span>
                    </span>
                    <span class="rz-sv-item-price">{{ servicePriceLabel(it) }}</span>
                    <span class="rz-sv-item-act" aria-hidden="true">
                      <AppIcon :name="chosen.has(it.id) ? 'check' : 'plus'" :size="15" :stroke="2.4" />
                      {{ chosen.has(it.id) ? 'Elegido' : 'Sumar' }}
                    </span>
                  </button>
                </li>
              </ol>
            </div>

            <aside id="sv-quote" class="rz-sv-quote" aria-live="polite" aria-label="Presupuesto orientativo">
              <p class="rz-eyebrow">Presupuesto</p>
              <p class="rz-sv-total" :class="{ bump }">{{ fmt(shownTotal) }}</p>
              <p class="rz-sv-quote-count">
                {{ chosenItems.length === 0 ? 'Elegí al menos un servicio' : `${chosenItems.length} ${chosenItems.length === 1 ? 'servicio' : 'servicios'} · valor orientativo` }}
              </p>
              <ul class="rz-sv-quote-list">
                <li v-if="!chosenItems.length" class="rz-sv-quote-empty">Todavía no elegiste nada.</li>
                <li v-for="it in chosenItems" :key="it.id">
                  <span class="rz-sv-quote-ico" aria-hidden="true"><AppIcon :name="serviceIcon(it.icon)" :size="13" /></span>
                  <span class="rz-sv-quote-name">{{ it.name }}</span>
                  <b>{{ servicePriceLabel(it) }}</b>
                  <button type="button" class="rz-sv-quote-rm" :aria-label="`Quitar ${it.name}`" @click="toggle(it.id)">
                    <AppIcon name="x" :size="13" :stroke="2.4" aria-hidden="true" />
                  </button>
                </li>
              </ul>
              <p v-if="hasUnpriced" class="rz-sv-quote-note">Los ítems "a convenir" se confirman por WhatsApp.</p>
              <p class="rz-sv-quote-pay"><AppIcon name="shield-check" :size="16" aria-hidden="true" /><span>{{ payNote }}</span></p>
              <button type="button" class="rz-btn rz-sv-quote-btn" :disabled="!chosenItems.length" @click="scrollTo('sv-pedido')">
                Pedir con este presupuesto <AppIcon name="arrow-right" :size="16" aria-hidden="true" />
              </button>
            </aside>
          </div>
        </section>
      </div>

      <!-- ===== Cómo funciona (bloque 'steps') ===== -->
      <div v-if="steps.length && on('steps')" data-blk="steps" class="rz-sv-block" :style="{ order: pos('steps') }">
        <section id="sv-proceso" class="rz-sv-wrap rz-sv-section" aria-labelledby="sv-proc-title">
          <header class="rz-sv-head">
            <p class="rz-eyebrow"><span class="rz-eyebrow-num">03</span> Cómo funciona</p>
            <h2 id="sv-proc-title">{{ blkTitle('steps', 'Simple, de punta a punta.') }}</h2>
          </header>
          <ol class="rz-sv-steps">
            <li v-for="(s, i) in steps" :key="i" class="rz-sv-step" v-reveal="i * 70">
              <span class="rz-sv-step-num" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
              <span class="rz-sv-step-ico" aria-hidden="true"><AppIcon :name="s.icon || 'check'" :size="18" /></span>
              <h3>{{ s.title }}</h3>
              <p>{{ s.text }}</p>
            </li>
          </ol>
        </section>
      </div>

      <!-- ===== Garantías (bloque 'benefits', custom.benefits) ===== -->
      <div v-if="perks.length && on('benefits')" data-blk="benefits" class="rz-sv-block" :style="{ order: ord('benefits') }">
        <section id="sv-garantias" class="rz-sv-wrap rz-sv-section" aria-labelledby="sv-perk-title">
          <header class="rz-sv-head">
            <p class="rz-eyebrow"><span class="rz-eyebrow-num">04</span> Garantías</p>
            <h2 id="sv-perk-title">{{ blkTitle('benefits', 'Tranquilidad de punta a punta.') }}</h2>
          </header>
          <ul class="rz-sv-perks">
            <li v-for="(b, i) in perks" :key="i" v-reveal="i * 60" class="rz-sv-perk">
              <span class="rz-sv-perk-ico" aria-hidden="true"><AppIcon :name="perkIcon(b.icon)" :size="20" /></span>
              <strong>{{ b.title }}</strong>
              <span v-if="b.text">{{ b.text }}</span>
            </li>
          </ul>
        </section>
      </div>

      <!-- ===== Galería de trabajos (bloque 'gallery', custom.gallery) ===== -->
      <div v-if="works.length && on('gallery')" data-blk="gallery" class="rz-sv-block" :style="{ order: ord('gallery') }">
        <section id="sv-trabajos" class="rz-sv-wrap rz-sv-section" aria-labelledby="sv-works-title">
          <header class="rz-sv-head">
            <p class="rz-eyebrow"><span class="rz-eyebrow-num">05</span> Trabajos</p>
            <h2 id="sv-works-title">{{ blkTitle('gallery', 'Algunos trabajos recientes.') }}</h2>
          </header>
          <div class="rz-sv-works">
            <figure v-for="(img, i) in works" :key="img.id || i" v-reveal="(i % 3) * 60" class="rz-sv-work">
              <img :src="img.url" :alt="img.alt || `Trabajo ${i + 1} de ${shopName}`" loading="lazy" decoding="async" />
            </figure>
          </div>
        </section>
      </div>

      <!-- ===== Testimonios (bloque 'testimonials', custom.testimonials) ===== -->
      <div v-if="testis.length && on('testimonials')" data-blk="testimonials" class="rz-sv-block" :style="{ order: ord('testimonials') }">
        <section id="sv-opiniones" class="rz-sv-wrap rz-sv-section" aria-labelledby="sv-testi-title">
          <header class="rz-sv-head">
            <p class="rz-eyebrow"><span class="rz-eyebrow-num">06</span> Clientes</p>
            <h2 id="sv-testi-title">{{ blkTitle('testimonials', testisTitle) }}</h2>
          </header>
          <div class="rz-sv-testis">
            <figure v-for="(t, i) in testis" :key="i" v-reveal="i * 70" class="rz-sv-testi">
              <blockquote>{{ t.text }}</blockquote>
              <figcaption>
                <strong>{{ t.name }}</strong>
                <span v-if="t.detail">{{ t.detail }}</span>
              </figcaption>
            </figure>
          </div>
        </section>
      </div>

      <!-- ===== Zona de cobertura y horarios (bloque 'zone') ===== -->
      <div v-if="showZone && on('zone')" data-blk="zone" class="rz-sv-block" :style="{ order: ord('zone') }">
        <section id="sv-zona" class="rz-sv-wrap rz-sv-section" aria-labelledby="sv-zone-title">
          <header class="rz-sv-head">
            <p class="rz-eyebrow"><span class="rz-eyebrow-num">07</span> Cobertura</p>
            <h2 id="sv-zone-title">{{ blkTitle('zone', 'Zona y horarios de atención.') }}</h2>
          </header>
          <div class="rz-sv-zone">
            <div class="rz-sv-zone-card">
              <span class="rz-sv-zone-ico" aria-hidden="true"><AppIcon name="map-pin" :size="20" /></span>
              <div>
                <strong>{{ location || 'Consultanos la zona de cobertura' }}</strong>
                <p v-if="custom.service_ask_address !== false">También trabajamos a domicilio: indicanos tu dirección en el pedido.</p>
              </div>
            </div>
            <ul v-if="contactHours.length" class="rz-sv-zone-hours">
              <li v-for="(h, i) in contactHours" :key="i">
                <span>{{ h.label }}</span>
                <strong>{{ h.value }}</strong>
              </li>
            </ul>
          </div>
        </section>
      </div>

      <!-- ===== Pedido por WhatsApp (bloque 'form') ===== -->
      <div v-if="on('form')" data-blk="form" class="rz-sv-block" :style="{ order: pos('form') }">
        <section id="sv-pedido" class="rz-sv-wrap rz-sv-section" aria-labelledby="sv-book-title">
          <div class="rz-sv-book">
            <div class="rz-sv-book-info">
              <p class="rz-eyebrow"><span class="rz-eyebrow-num">08</span> Hacer el pedido</p>
              <h2 id="sv-book-title">{{ blkTitle('form', 'Dejanos tus datos y coordinamos.') }}</h2>
              <p class="rz-sv-book-lead">El pedido sale por WhatsApp con tu selección. No pedimos tarjeta ni pago por adelantado.</p>
              <ul class="rz-sv-book-notes">
                <li><AppIcon name="lock" :size="15" aria-hidden="true" />Sin pago online ni datos de tarjeta</li>
                <li><AppIcon name="whatsapp" :size="15" aria-hidden="true" />Tu pedido llega directo al WhatsApp del negocio</li>
                <li><AppIcon name="circle-check" :size="15" aria-hidden="true" />El precio final se confirma antes de empezar</li>
              </ul>
            </div>

            <form v-if="waBase" class="rz-sv-form" novalidate @submit.prevent="submit">
              <div class="rz-sv-sel" :class="{ bad: errors.pick }" aria-live="polite">
                <template v-if="chosenItems.length">
                  <span class="rz-sv-sel-lbl">Tu selección</span>
                  <span v-for="it in chosenItems" :key="it.id" class="rz-sv-sel-chip">
                    <AppIcon :name="serviceIcon(it.icon)" :size="12" aria-hidden="true" />{{ it.name }}
                  </span>
                  <b class="rz-sv-sel-total">{{ fmt(total) }}</b>
                </template>
                <button v-else type="button" class="rz-sv-sel-empty" @click="scrollTo('sv-servicios')">
                  <AppIcon name="plus" :size="14" aria-hidden="true" /> {{ errors.pick || 'Todavía no elegiste servicios — tocá para elegir' }}
                </button>
              </div>
              <div class="rz-sv-field" :class="{ bad: errors.name }">
                <label class="rz-label" for="sv-name">Nombre</label>
                <input id="sv-name" class="rz-field" v-model="form.name" autocomplete="name" placeholder="Ej: Lucía Pérez" />
                <span class="rz-field-error" aria-live="polite">{{ errors.name || '' }}</span>
              </div>
              <div class="rz-sv-field" :class="{ bad: errors.phone }">
                <label class="rz-label" for="sv-phone">Tu WhatsApp</label>
                <input id="sv-phone" class="rz-field" v-model="form.phone" type="tel" autocomplete="tel" placeholder="11 2345 6789" />
                <span class="rz-field-error" aria-live="polite">{{ errors.phone || '' }}</span>
              </div>
              <div v-if="askAddress" class="rz-sv-field" :class="{ bad: errors.address }">
                <label class="rz-label" for="sv-addr">Dirección (si hace falta para el servicio)</label>
                <input id="sv-addr" class="rz-field" v-model="form.address" autocomplete="street-address" placeholder="Calle, número y barrio" />
                <span class="rz-field-error" aria-live="polite">{{ errors.address || '' }}</span>
              </div>
              <fieldset class="rz-sv-field" :class="{ bad: errors.day }">
                <legend class="rz-label">Día preferido</legend>
                <div class="rz-sv-chips">
                  <template v-for="(d, i) in days" :key="d">
                    <input :id="`sv-d${i}`" v-model="form.day" type="radio" name="sv-day" :value="d" />
                    <label :for="`sv-d${i}`">{{ d }}</label>
                  </template>
                </div>
                <span class="rz-field-error" aria-live="polite">{{ errors.day || '' }}</span>
              </fieldset>
              <fieldset class="rz-sv-field" :class="{ bad: errors.slot }">
                <legend class="rz-label">Franja horaria</legend>
                <div class="rz-sv-chips">
                  <template v-for="(s, i) in slots" :key="s">
                    <input :id="`sv-t${i}`" v-model="form.slot" type="radio" name="sv-slot" :value="s" />
                    <label :for="`sv-t${i}`">{{ s }}</label>
                  </template>
                </div>
                <span class="rz-field-error" aria-live="polite">{{ errors.slot || '' }}</span>
              </fieldset>
              <button class="rz-btn rz-sv-submit" type="submit">
                <AppIcon name="whatsapp" :size="18" aria-hidden="true" /> Enviar pedido por WhatsApp
              </button>
              <p v-if="sentOk" class="rz-sv-form-ok" role="status"><AppIcon name="circle-check" :size="17" aria-hidden="true" /> Listo — se abrió WhatsApp con tu pedido.</p>
              <p class="rz-sv-form-note">Te escriben por WhatsApp para confirmar. El pago se hace en persona, nada se cobra por la web.</p>
            </form>

            <div v-else class="rz-sv-form" role="note">
              <p><strong>Este negocio aún no configuró su WhatsApp.</strong></p>
              <p class="rz-sv-form-note">Cuando cargue su número vas a poder enviar el pedido desde acá. Mientras tanto podés contactarlo desde la página principal.</p>
              <RouterLink v-if="siteTemplates.includes('landing')" class="rz-btn rz-btn--ghost" :to="homeTo">
                <AppIcon name="store" :size="16" aria-hidden="true" /> Ir a la página principal
              </RouterLink>
            </div>
          </div>
        </section>
      </div>

      <!-- ===== Preguntas frecuentes (bloque 'faq') ===== -->
      <div v-if="faqs.length && on('faq')" data-blk="faq" class="rz-sv-block" :style="{ order: pos('faq') }">
        <section id="sv-preguntas" class="rz-sv-wrap rz-sv-section" aria-labelledby="sv-faq-title">
          <div class="rz-sv-faq-wrap">
            <header class="rz-sv-head rz-sv-faq-head">
              <p class="rz-eyebrow"><span class="rz-eyebrow-num">09</span> Preguntas</p>
              <h2 id="sv-faq-title">{{ blkTitle('faq', 'Lo que más nos preguntan.') }}</h2>
            </header>
            <div class="rz-sv-faq">
              <details v-for="(f, i) in faqs" :key="i" :open="i === 0">
                <summary>{{ f.q }}</summary>
                <p>{{ f.a }}</p>
              </details>
            </div>
          </div>
        </section>
      </div>
    </main>

    <Transition name="rz-sv-bar">
      <div v-if="showBar" class="rz-sv-bar" role="region" aria-label="Resumen del presupuesto">
        <button v-if="chosenItems.length" type="button" class="rz-sv-bar-main" aria-haspopup="dialog" :aria-expanded="sheetOpen" aria-controls="sv-sheet" @click="openSheet">
          <span class="rz-sv-bar-info">
            <b>{{ fmt(shownTotal) }}</b>
            <small>{{ chosenItems.length }} {{ chosenItems.length === 1 ? 'servicio' : 'servicios' }} · ver detalle</small>
          </span>
          <span class="rz-sv-bar-cta" aria-hidden="true"><AppIcon name="chevron-up" :size="18" /></span>
        </button>
        <button v-else type="button" class="rz-sv-bar-main" @click="scrollTo('sv-servicios')">
          <span class="rz-sv-bar-info">
            <b>Pedí tu servicio</b>
            <small>{{ items.length }} {{ items.length === 1 ? 'disponible' : 'disponibles' }} · confirmamos por WhatsApp</small>
          </span>
          <span class="rz-sv-bar-cta" aria-hidden="true"><AppIcon name="arrow-right" :size="18" /></span>
        </button>
      </div>
    </Transition>
    <Transition name="rz-sv-fade">
      <div v-if="sheetOpen" class="rz-sv-sheet-backdrop" aria-hidden="true" @click="closeSheet"></div>
    </Transition>
    <Transition name="rz-sv-sheet">
      <div v-if="sheetOpen" id="sv-sheet" ref="sheetEl" class="rz-sv-sheet" role="dialog" aria-modal="true" aria-labelledby="sv-sheet-title" tabindex="-1" @keydown="onSheetKeydown">
        <span class="rz-sv-sheet-handle" aria-hidden="true"></span>
        <div class="rz-sv-sheet-head">
          <b id="sv-sheet-title">Tu presupuesto</b>
          <button type="button" class="rz-sv-sheet-close" aria-label="Cerrar detalle del presupuesto" @click="closeSheet">
            <AppIcon name="x" :size="18" />
          </button>
        </div>
        <div class="rz-sv-sheet-total">
          <b>{{ fmt(shownTotal) }}</b>
          <span>{{ chosenItems.length }} {{ chosenItems.length === 1 ? 'servicio' : 'servicios' }} · valor orientativo</span>
        </div>
        <ul class="rz-sv-sheet-items">
          <li v-for="it in chosenItems" :key="it.id">
            <span class="rz-sv-quote-ico" aria-hidden="true"><AppIcon :name="serviceIcon(it.icon)" :size="13" /></span>
            <span class="rz-sv-quote-name">{{ it.name }}</span><b>{{ servicePriceLabel(it) }}</b>
            <button type="button" class="rz-sv-quote-rm" :aria-label="`Quitar ${it.name}`" @click="toggle(it.id)">
              <AppIcon name="x" :size="13" :stroke="2.4" aria-hidden="true" />
            </button>
          </li>
        </ul>
        <p v-if="hasUnpriced" class="rz-sv-sheet-note">Los ítems "a convenir" se confirman por WhatsApp.</p>
        <button type="button" class="rz-btn" @click="closeSheet(); scrollTo('sv-pedido')">
          Pedir con este presupuesto <AppIcon name="arrow-right" :size="16" aria-hidden="true" />
        </button>
      </div>
    </Transition>

    <!-- Botón flotante de WhatsApp (desktop; posición y forma por
         custom.service_wa_*). En móvil el contacto ya vive en el dock. -->
    <a
      v-if="waFloat" class="rz-sv-wa" :class="`rz-sv-wa--${waShape}`" :data-pos="waPos"
      :href="waBase" target="_blank" rel="noopener" aria-label="Escribinos por WhatsApp"
    ><AppIcon name="whatsapp" :size="26" /><span v-if="waShape === 'pill'">Escribinos</span></a>
  </div>
</template>
