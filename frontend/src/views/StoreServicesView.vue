<script setup>
// Página "Servicios" de la web pública (site_templates). Implementa el
// embudo de pedido por servicios: el visitante marca los que necesita, ve
// el presupuesto orientativo animado y confirma el pedido por WhatsApp.
// Regla dura del producto: la web NUNCA persiste reservas, pedidos ni
// pagos — el mensaje se arma en el cliente y se abre en wa.me; el pago se
// hace en persona (service_pay_note lo explica en la tarjeta de precio).
// Los ítems llegan en el payload público (store.service_items, solo
// activos); si la página no está en los site_templates efectivos del plan
// la ruta rebota a la página disponible.
import { ref, computed, inject, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { storeHostSlug } from '../config/env.js'
import { buildServiceRequestMessage, servicePriceLabel } from '../api/services.api.js'
import AppIcon from '../components/AppIcon.vue'
import '../assets/store-services.css'

const ctx = inject('storePage')
const router = useRouter()
const { custom, store, status, shopName, location, siteTemplates, showCatalog } = ctx

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

// Tipografía: la página usa las fuentes de la plantilla activa de la
// tienda (las carga el layout según el template elegido) — el diseño se
// adapta por tokens en store-services.css.

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
// Cinta marquee con los nombres de los servicios (duplicada para el loop).
const bandItems = computed(() => {
  const names = items.value.map((it) => it.name)
  return names.length >= 2 ? [...names, ...names] : []
})

// ===== WhatsApp =====
const whatsapp = computed(() => String(custom.value.whatsapp || '').replace(/\D/g, ''))
const waBase = computed(() => (whatsapp.value ? `https://wa.me/${whatsapp.value}` : ''))

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
  if (Object.keys(e).length) { sentOk.value = false; return }
  if (!waBase.value) return
  const message = buildServiceRequestMessage({
    shopName: shopName.value,
    items: chosenItems.value,
    total: total.value,
    visitor: f
  })
  window.open(`${waBase.value}?text=${encodeURIComponent(message)}`, '_blank', 'noopener')
  sentOk.value = true
}

// Scroll interno suave (los ids son locales a la página).
const reduceMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
function scrollTo(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: reduceMotion() ? 'auto' : 'smooth', block: 'start' })
}

// ===== Pulido: entrada al scroll, recorrido del pedido y barra móvil =====
// v-reveal: el elemento aparece con un "rise" escalonado (--i) al entrar
// en pantalla; sin IntersectionObserver o con reduced-motion queda visible.
const vReveal = {
  mounted(el) {
    if (reduceMotion() || !('IntersectionObserver' in window)) return
    el.classList.add('sv-rv')
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return
      el.classList.add('sv-in')
      io.disconnect()
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' })
    io.observe(el)
    el._io = io
  },
  unmounted(el) { el._io?.disconnect() }
}
const stagger = (i) => ({ '--i': Math.min(i, 8) })

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
const showBar = computed(() => chosenItems.value.length > 0 && !formInView.value && !quoteInView.value)
watch(items, () => nextTick(observeTargets), { immediate: false })
onMounted(() => nextTick(observeTargets))
onBeforeUnmount(() => formIO?.disconnect())
const pickError = ref('')
watch(chosenItems, (v) => { if (v.length) pickError.value = '' })
</script>

<template>
  <div class="sv-page">
    <main id="sv-main">
      <div class="sp-container">
        <!-- ===== Hero ===== -->
        <section class="sv-hero">
          <div>
            <span v-if="location" class="sv-pill"><i aria-hidden="true"></i>{{ location }}</span>
            <span v-else class="sv-pill"><i aria-hidden="true"></i>Servicios de {{ shopName }}</span>
            <h1>Servicios de <span class="hl">{{ shopName }}</span>, sin vueltas.</h1>
            <p class="lead">Elegí lo que necesitás, mirá el presupuesto orientativo y confirmamos todo por WhatsApp. Sin pagos online.</p>
            <div class="sv-hero-cta">
              <button type="button" class="sv-btn" @click="scrollTo('sv-servicios')">Ver servicios y precios</button>
              <a v-if="waBase" class="sv-btn sv-btn--ghost" :href="waBase" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="17" /> Escribinos</a>
            </div>
            <ul class="sv-trust" aria-label="Por qué pedir acá">
              <li><AppIcon name="shield-check" :size="16" /> Sin pago online</li>
              <li><AppIcon name="clock" :size="16" /> Respuesta por WhatsApp</li>
              <li v-if="items.length"><AppIcon name="checklist" :size="16" /> {{ items.length }} {{ items.length === 1 ? 'servicio' : 'servicios' }}</li>
            </ul>
            <div class="sv-pay-note"><AppIcon name="wallet" :size="18" /><span>Pagás <b>en persona</b>: la web nunca cobra ni guarda tarjetas.</span></div>
          </div>
          <div class="sv-stage" aria-hidden="true">
            <span class="sv-stage-dots"><i class="d1"></i><i class="d2"></i></span>
            <span class="sv-stage-ring"></span>
            <AppIcon name="wrench" :size="140" :stroke="1.2" class="sv-stage-icon" />
            <div class="sv-stage-badge"><AppIcon name="wallet" :size="16" /> Pagás al final</div>
          </div>
        </section>
      </div>

      <!-- ===== Cinta marquee con los servicios ===== -->
      <div v-if="bandItems.length" class="sv-band" aria-hidden="true">
        <div class="sv-band-track"><span v-for="(n, i) in bandItems" :key="i">{{ n }}</span></div>
      </div>

      <div class="sp-container">
        <!-- ===== Picker + presupuesto ===== -->
        <section id="sv-servicios" aria-labelledby="sv-svc-title">
          <div class="sv-head">
            <span class="sv-eyebrow">Servicios</span>
            <h2 id="sv-svc-title">Elegí lo que necesitás y mirá el total.</h2>
            <p>{{ priceNote }}</p>
          </div>
          <ol class="sv-flow" aria-label="Pasos del pedido">
            <li v-for="s in flow" :key="s.n" :class="`is-${s.state}`" :aria-current="s.state === 'now' ? 'step' : undefined">
              <span class="dot"><AppIcon v-if="s.state === 'done'" name="check" :size="15" :stroke="2.6" /><AppIcon v-else :name="s.icon" :size="15" /></span>
              <span class="lbl">{{ s.label }}</span>
            </li>
          </ol>
          <div v-if="!items.length" class="sv-empty">
            <AppIcon name="wrench" :size="30" class="icon" />
            <p><strong>Todavía no hay servicios publicados.</strong></p>
            <p>Cuando el negocio cargue su lista, acá vas a poder armar tu presupuesto.</p>
          </div>
          <div v-else class="sv-services">
            <div class="sv-list" role="group" aria-label="Servicios disponibles">
              <button
                v-for="(it, i) in items" :key="it.id" v-reveal type="button" class="sv-item" :style="stagger(i)"
                :aria-pressed="chosen.has(it.id)" @click="toggle(it.id)"
              >
                <span class="ico"><AppIcon :name="it.icon || 'wrench'" :size="22" /></span>
                <h3>{{ it.name }}</h3>
                <small v-if="it.description">{{ it.description }}</small>
                <span class="meta">
                  <span v-if="it.duration" class="dur"><AppIcon name="clock" :size="13" /> {{ it.duration }}</span>
                  <span class="price">{{ servicePriceLabel(it) }}</span>
                </span>
                <span class="act" aria-hidden="true">
                  <AppIcon :name="chosen.has(it.id) ? 'check' : 'plus'" :size="14" :stroke="2.4" />
                  {{ chosen.has(it.id) ? 'Agregado' : 'Agregar' }}
                </span>
              </button>
            </div>

            <aside id="sv-quote" class="sv-quote" aria-live="polite" aria-label="Presupuesto orientativo">
              <span class="kicker"><AppIcon name="receipt" :size="15" /> Tu presupuesto</span>
              <div class="total" :class="{ bump }">{{ fmt(shownTotal) }}</div>
              <div class="count">
                {{ chosenItems.length === 0 ? 'Elegí al menos un servicio' : `${chosenItems.length} ${chosenItems.length === 1 ? 'servicio' : 'servicios'} · valor orientativo` }}
              </div>
              <ul>
                <li v-if="!chosenItems.length" class="empty-line">Todavía no elegiste nada.</li>
                <li v-for="it in chosenItems" :key="it.id">
                  <span>{{ it.name }}</span><b>{{ servicePriceLabel(it) }}</b>
                  <button type="button" class="rm" :aria-label="`Quitar ${it.name}`" @click="toggle(it.id)"><AppIcon name="x" :size="13" :stroke="2.4" /></button>
                </li>
              </ul>
              <p v-if="hasUnpriced" class="count" style="font-size:14px">Los ítems "a convenir" se confirman por WhatsApp.</p>
              <div class="pay"><AppIcon name="shield-check" :size="18" /><span>{{ payNote }}</span></div>
              <button type="button" class="sv-btn" :disabled="!chosenItems.length" @click="scrollTo('sv-pedido')">Pedir con este presupuesto <AppIcon name="arrow-right" :size="17" /></button>
            </aside>
          </div>
        </section>

        <!-- ===== Cómo funciona ===== -->
        <section v-if="steps.length" id="sv-proceso" aria-labelledby="sv-proc-title" style="padding-top:0">
          <div class="sv-head">
            <span class="sv-eyebrow">Cómo funciona</span>
            <h2 id="sv-proc-title">Simple, de punta a punta.</h2>
          </div>
          <div class="sv-steps">
            <div v-for="(s, i) in steps" :key="i" v-reveal class="sv-step" :style="stagger(i)">
              <span class="num"><AppIcon v-if="s.icon" :name="s.icon" :size="20" /><template v-else>{{ i + 1 }}</template><em>{{ i + 1 }}</em></span>
              <h3>{{ s.title }}</h3>
              <p>{{ s.text }}</p>
            </div>
          </div>
        </section>

        <!-- ===== Pedido por WhatsApp ===== -->
        <section id="sv-pedido" aria-labelledby="sv-book-title" style="padding-top:0">
          <div class="sv-book">
            <div class="sv-book-info">
              <span class="sv-eyebrow">Hacer el pedido</span>
              <h2 id="sv-book-title" style="font-size:clamp(28px,4vw,48px)">Dejanos tus datos y coordinamos.</h2>
              <p style="color:var(--sv-mute);font-size:18px">El pedido sale por WhatsApp con tu selección. No pedimos tarjeta ni pago por adelantado.</p>
              <ul>
                <li><span class="tick"><AppIcon name="lock" :size="14" /></span>Sin pago online ni datos de tarjeta</li>
                <li><span class="tick"><AppIcon name="whatsapp" :size="14" /></span>Tu pedido llega directo al WhatsApp del negocio</li>
                <li><span class="tick"><AppIcon name="circle-check" :size="14" /></span>El precio final se confirma antes de empezar</li>
              </ul>
            </div>

            <form v-if="waBase" class="sv-form" novalidate @submit.prevent="submit">
              <div class="sv-sel" :class="{ bad: errors.pick }" aria-live="polite">
                <template v-if="chosenItems.length">
                  <span class="sv-sel-lbl">Tu selección</span>
                  <span v-for="it in chosenItems" :key="it.id" class="sv-sel-chip"><AppIcon :name="it.icon || 'wrench'" :size="13" />{{ it.name }}</span>
                  <b class="sv-sel-total">{{ fmt(total) }}</b>
                </template>
                <button v-else type="button" class="sv-sel-empty" @click="scrollTo('sv-servicios')"><AppIcon name="plus" :size="14" /> {{ errors.pick || 'Todavía no elegiste servicios — tocá para elegir' }}</button>
              </div>
              <div class="sv-field" :class="{ bad: errors.name }">
                <label for="sv-name">Nombre</label>
                <input id="sv-name" v-model="form.name" autocomplete="name" placeholder="Ej: Lucía Pérez">
                <span class="err" aria-live="polite">{{ errors.name || '' }}</span>
              </div>
              <div class="sv-field" :class="{ bad: errors.phone }">
                <label for="sv-phone">Tu WhatsApp</label>
                <input id="sv-phone" v-model="form.phone" type="tel" autocomplete="tel" placeholder="11 2345 6789">
                <span class="err" aria-live="polite">{{ errors.phone || '' }}</span>
              </div>
              <div v-if="askAddress" class="sv-field" :class="{ bad: errors.address }">
                <label for="sv-addr">Dirección (si hace falta para el servicio)</label>
                <input id="sv-addr" v-model="form.address" autocomplete="street-address" placeholder="Calle, número y barrio">
                <span class="err" aria-live="polite">{{ errors.address || '' }}</span>
              </div>
              <fieldset class="sv-field">
                <legend>Día preferido</legend>
                <div class="sv-chips">
                  <template v-for="(d, i) in days" :key="d">
                    <input :id="`sv-d${i}`" v-model="form.day" type="radio" name="sv-day" :value="d"><label :for="`sv-d${i}`">{{ d }}</label>
                  </template>
                </div>
                <span class="err" aria-live="polite">{{ errors.day || '' }}</span>
              </fieldset>
              <fieldset class="sv-field">
                <legend>Franja horaria</legend>
                <div class="sv-chips">
                  <template v-for="(s, i) in slots" :key="s">
                    <input :id="`sv-t${i}`" v-model="form.slot" type="radio" name="sv-slot" :value="s"><label :for="`sv-t${i}`">{{ s }}</label>
                  </template>
                </div>
                <span class="err" aria-live="polite">{{ errors.slot || '' }}</span>
              </fieldset>
              <button class="sv-btn" type="submit"><AppIcon name="whatsapp" :size="18" /> Enviar pedido por WhatsApp</button>
              <p v-if="sentOk" class="sv-form-ok" role="status"><AppIcon name="circle-check" :size="18" /> Listo — se abrió WhatsApp con tu pedido.</p>
              <p class="sv-form-note">Te escriben por WhatsApp para confirmar. El pago se hace en persona, nada se cobra por la web.</p>
            </form>

            <div v-else class="sv-form" role="note">
              <p><strong>Este negocio aún no configuró su WhatsApp.</strong></p>
              <p class="sv-form-note">Cuando cargue su número vas a poder enviar el pedido desde acá. Mientras tanto podés contactarlo desde la página principal.</p>
              <RouterLink v-if="siteTemplates.includes('landing')" class="sv-btn sv-btn--ghost" :to="homeTo"><AppIcon name="store" :size="16" /> Ir a la página principal</RouterLink>
            </div>
          </div>
        </section>

        <!-- ===== Preguntas frecuentes (bloque compartido con la portada) ===== -->
        <section v-if="faqs.length" id="sv-preguntas" aria-labelledby="sv-faq-title" style="padding-top:0">
          <div class="sv-head">
            <span class="sv-eyebrow">Preguntas</span>
            <h2 id="sv-faq-title">Lo que más nos preguntan.</h2>
          </div>
          <div class="sv-faq">
            <details v-for="(f, i) in faqs" :key="i" :open="i === 0">
              <summary>{{ f.q }}</summary>
              <p>{{ f.a }}</p>
            </details>
          </div>
        </section>
      </div>
    </main>

    <Transition name="sv-bar">
      <div v-if="showBar" class="sv-bar" role="region" aria-label="Resumen del presupuesto">
        <div class="sv-bar-info">
          <b>{{ fmt(shownTotal) }}</b>
          <small>{{ chosenItems.length }} {{ chosenItems.length === 1 ? 'servicio' : 'servicios' }}</small>
        </div>
        <button type="button" class="sv-btn" @click="scrollTo('sv-pedido')">Pedir <AppIcon name="arrow-right" :size="16" /></button>
      </div>
    </Transition>
  </div>
</template>
