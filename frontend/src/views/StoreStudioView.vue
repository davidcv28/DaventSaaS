<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useStorePage } from '../composables/useStorePage.js'
import { servicePriceLabel, buildServiceRequestMessage } from '../api/services.api.js'
import AppIcon from '../components/AppIcon.vue'
import StTag from '../components/store/StTag.vue'
import StepRail from '../components/store/StepRail.vue'
import TrustBar from '../components/store/TrustBar.vue'
import ScheduleCard from '../components/store/ScheduleCard.vue'
import { vReveal } from '../directives/reveal.js'
import '../assets/store-studio.css'
import { useLayout } from '../composables/useLayout.js'

// Familia SERVICIOS — "Studio". Reducir la duda: prueba social arriba,
// contacto a un toque. Hero conversacional con tarjeta flotante de
// reseñas (rating real del catálogo), lista de servicios con precio,
// método en pasos, testimonios, FAQ y formulario corto que arma el
// WhatsApp. 'proceso' invierte la jerarquía: el método ES la portada.
const p = useStorePage()
const { on, pos } = useLayout('landing')
const { custom, shopName, location, pageTemplate, hasAbout, showContact, showServices, heroTitle } = p
const variant = computed(() => (pageTemplate.value === 'proceso' ? 'proceso' : 'studio'))

// Titular de máx. 12 palabras / subtítulo de máx. 140 (regla de la spec).
const headline = computed(() => heroTitle.value.split(/\s+/).slice(0, 12).join(' '))
const subtitle = computed(() => {
  const d = (custom.value.description || '').trim()
  return d.length > 140 ? `${d.slice(0, 137)}…` : d
})

// Tarjeta flotante: rating real agregado de los productos/ítems con
// valoraciones; sin datos reales no se muestra.
const rating = computed(() => {
  const rated = p.products.value.filter((x) => x.rating_count)
  const votes = rated.reduce((a, x) => a + x.rating_count, 0)
  if (!votes) return null
  const avg = rated.reduce((a, x) => a + x.rating_avg * x.rating_count, 0) / votes
  return { avg: avg.toFixed(1), count: votes + p.testimonials.value.length }
})

const trustItems = computed(() => {
  const out = []
  if (custom.value.about_years) out.push({ icon: 'award', value: `+${custom.value.about_years}`, label: 'años de trayectoria' })
  if (rating.value) out.push({ icon: 'star', value: rating.value.avg, label: `${rating.value.count} ${rating.value.count === 1 ? 'reseña' : 'reseñas'}` })
  if (location.value) out.push({ icon: 'map-pin', value: 'Aquí', label: location.value })
  if (p.serviceItems.value.length) out.push({ icon: 'checklist', value: String(p.serviceItems.value.length), label: p.serviceItems.value.length === 1 ? 'servicio' : 'servicios' })
  return out.slice(0, 3)
})

// CTAs: presupuesto por WhatsApp + llamada directa (mismo número real).
const phone = computed(() => (p.waNumber.value ? `tel:+${p.waNumber.value}` : ''))
const waBudget = (item) => {
  const lines = [`quiero pedir un presupuesto${item ? ` de "${item.name}"` : ''}.`]
  return p.waLink(lines)
}

// Servicios como cards horizontales. Modalidad derivada de la config real
// (service_ask_address) y duración del ítem — no se inventan datos.
const modalities = computed(() => (custom.value.service_ask_address !== false ? ['A domicilio', 'Presencial'] : ['Presencial']))
const svcTags = (it) => {
  const tags = [...modalities.value]
  if (it.duration) tags.unshift(it.duration)
  return tags.slice(0, 2).map((t, i) => ({ label: t, icon: i === 0 && it.duration ? 'clock' : (t === 'A domicilio' ? 'truck' : 'map-pin') }))
}
const svcIcon = (it) => (it.icon && it.icon !== 'store' ? it.icon : 'wrench')

// Método: pasos reales del dueño (service_steps) o los 3 del flujo por
// defecto — mismo fallback que la página de servicios existente.
const steps = computed(() => {
  const saved = Array.isArray(custom.value.service_steps) ? custom.value.service_steps.filter((s) => s?.title) : []
  if (saved.length) return saved.slice(0, 4)
  return [
    { icon: 'message-circle', title: 'Nos contás qué necesitás', text: 'Elegís el servicio y nos llega tu consulta armada por WhatsApp.' },
    { icon: 'calendar', title: 'Coordinamos día y hora', text: 'Te confirmamos presupuesto y turno en el chat.' },
    { icon: 'check', title: 'Trabajamos y pagás al final', text: 'Nada se cobra por la web: se arregla en persona al concretar.' }
  ]
})
// Línea de progreso del rail que se llena con el scroll.
const railWrap = ref(null)
const railProgress = ref(0)
// Línea de tiempo del relato (proceso): progreso real de .sd-main.
const mainEl = ref(null)
const spineProgress = ref(0)
let scrollRaf = null
function onScroll() {
  if (scrollRaf) return
  scrollRaf = requestAnimationFrame(() => {
    scrollRaf = null
    const vh = window.innerHeight
    const r = railWrap.value?.getBoundingClientRect()
    if (r) railProgress.value = Math.min(1, Math.max(0, (vh * 0.75 - r.top) / (r.height || 1)))
    const m = mainEl.value?.getBoundingClientRect()
    if (m) spineProgress.value = Math.min(1, Math.max(0, (-m.top) / ((m.height - vh * 0.6) || 1)))
  })
}

// Testimonios en carrusel snap (card 280px, comillas grandes).
const faqOpen = ref(0)
const faqsTop = computed(() => p.faqs.value.slice(0, 5))

// Galería de trabajos: mosaico del pool de imágenes reales.
const works = computed(() => p.imagePool.value.slice(1, 7))

// Formulario corto -> mensaje de WhatsApp.
const form = ref({ name: '', service: '', message: '' })
const formErr = ref('')
// Meter de completitud del pedido (firma "barras" de studio): 3 segmentos
// reales — nombre, servicio elegido y mensaje.
const formMeter = computed(() => [
  form.value.name.trim().length >= 2,
  Boolean(form.value.service),
  form.value.message.trim().length > 0
])
const waForm = computed(() => {
  const f = form.value
  if (f.name.trim().length < 2) return ''
  const lines = [`soy ${f.name.trim()}.`]
  if (f.service) lines.push(`Me interesa: ${f.service}.`)
  if (f.message.trim()) lines.push(f.message.trim())
  return p.waLink(lines)
})
const submit = () => {
  formErr.value = form.value.name.trim().length < 2 ? 'Decinos tu nombre así te respondemos bien.' : ''
  if (!formErr.value && waForm.value) window.open(waForm.value, '_blank', 'noopener')
}

// Stats del dueño (si los cargó).
const stats = computed(() => p.stats.value.slice(0, 4))

onMounted(() => {
  p.loadCatalog()
  window.addEventListener('scroll', onScroll, { passive: true })
  onScroll()
})
onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  if (scrollRaf) cancelAnimationFrame(scrollRaf)
})
</script>

<template>
<div class="sp-page-root sd" :data-var="variant" :style="{ '--sd-spine': spineProgress }">
  <!-- ===== Hero conversacional + tarjeta flotante de reseñas ===== -->
  <header v-if="on('hero')" class="sd-hero" :style="{ order: pos('hero') }">
    <div class="sd-hero-in">
      <div class="sd-hero-copy">
        <h1 class="sd-title">{{ headline }}</h1>
        <p v-if="subtitle" class="sd-lede">{{ subtitle }}</p>
        <div class="sd-hero-ctas">
          <a v-if="p.waBase.value" class="sd-cta" :href="waBudget()" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="17" /> Pedir presupuesto</a>
          <a v-if="phone" class="sd-cta ghost" :href="phone"><AppIcon name="phone" :size="16" /> Llamar</a>
        </div>
        <ul class="sd-hero-meta">
          <li v-if="location"><AppIcon name="map-pin" :size="13" /> {{ location }}</li>
          <li v-if="p.openNow.value" :data-state="p.openNow.value.state"><AppIcon name="clock" :size="13" /> {{ p.openNow.value.text }}</li>
        </ul>
        <ol v-if="variant === 'studio' && steps.length" class="sd-hero-meter" aria-hidden="true">
          <li v-for="(s, i) in steps.slice(0, 3)" :key="i" class="seg" :style="{ '--seg': i }">
            <i /><span>{{ s.title }}</span>
          </li>
        </ol>
      </div>
      <figure v-if="p.heroImage.value && variant === 'studio'" class="sd-hero-photo">
        <img :src="p.heroImage.value" :alt="`Trabajo de ${shopName}`" fetchpriority="high" decoding="async" />
        <figcaption v-if="rating" class="sd-hero-rating">
          <strong><AppIcon name="star" :size="15" /> {{ rating.avg }}</strong>
          <span>{{ rating.count }} {{ rating.count === 1 ? 'reseña' : 'reseñas' }}</span>
        </figcaption>
      </figure>
      <!-- Proceso: el método es el protagonista del hero -->
      <div v-if="variant === 'proceso'" ref="railWrap" class="sd-hero-steps">
        <StepRail :steps="steps" :progress="railProgress" />
      </div>
    </div>
    <TrustBar v-if="trustItems.length" class="sd-trust" :items="trustItems" />
  </header>

  <main ref="mainEl" class="sd-main">
    <!-- ===== Stats reales del dueño ===== -->
    <section v-if="stats.length && on('stats')" v-reveal class="sd-stats" :style="{ order: pos('stats') }" aria-label="Números">
      <div v-for="(s, i) in stats" :key="i" class="sd-stat"><strong>{{ s.value }}</strong><span>{{ s.label }}</span></div>
    </section>

    <!-- ===== Lista de servicios ===== -->
    <section v-if="p.serviceItems.value.length && on('services')" class="sd-services" :style="{ order: pos('services') }" aria-labelledby="sd-svc-t">
      <header class="sd-sec-h"><p class="sd-eyebrow">Servicios</p><h2 id="sd-svc-t">Qué hacemos</h2></header>
      <ul class="sd-svc-list">
        <li v-for="it in p.serviceItems.value" :key="it.id">
          <a class="sd-svc" :href="p.waBase.value ? waBudget(it) : undefined" target="_blank" rel="noopener">
            <span class="sd-svc-icon"><AppIcon :name="svcIcon(it)" :size="22" /></span>
            <span class="sd-svc-body">
              <strong>{{ it.name }}</strong>
              <span v-if="it.description" class="sd-svc-desc">{{ it.description }}</span>
              <span class="sd-svc-tags"><StTag v-for="t in svcTags(it)" :key="t.label" kind="modalidad" :label="t.label" :icon="t.icon" /></span>
            </span>
            <span class="sd-svc-price">{{ it.price != null ? `Desde ${servicePriceLabel(it)}` : 'A convenir' }}</span>
          </a>
        </li>
      </ul>
      <p v-if="custom.service_price_note" class="sd-svc-note">{{ custom.service_price_note }}</p>
    </section>

    <!-- ===== Cómo trabajamos (studio: debajo; proceso ya lo mostró) ===== -->
    <section v-if="variant === 'studio' && on('steps')" ref="railWrap" class="sd-steps" :style="{ order: pos('steps') }" aria-labelledby="sd-steps-t">
      <header class="sd-sec-h"><p class="sd-eyebrow">Método</p><h2 id="sd-steps-t">Cómo trabajamos</h2></header>
      <StepRail :steps="steps" :progress="railProgress" />
    </section>

    <!-- ===== Trabajos: mosaico real ===== -->
    <section v-if="works.length && on('gallery')" v-reveal class="sd-works" :style="{ order: pos('gallery') }" aria-labelledby="sd-works-t">
      <header class="sd-sec-h"><p class="sd-eyebrow">Portfolio</p><h2 id="sd-works-t">Trabajos recientes</h2></header>
      <div class="sd-works-grid">
        <figure v-for="(u, i) in works" :key="i">
          <img :src="u" :alt="`Trabajo ${i + 1} de ${shopName}`" loading="lazy" decoding="async" width="400" height="400" />
          <figcaption v-if="variant === 'proceso'">FIG. {{ String(i + 1).padStart(2, '0') }}</figcaption>
        </figure>
      </div>
    </section>

    <!-- ===== Testimonios ===== -->
    <section v-if="p.testimonials.value.length && on('testimonials')" v-reveal class="sd-testi" :style="{ order: pos('testimonials') }" aria-labelledby="sd-testi-t">
      <header class="sd-sec-h"><p class="sd-eyebrow">{{ custom.testimonials_title || 'Clientes' }}</p><h2 id="sd-testi-t">Lo que dicen</h2></header>
      <div class="sd-testi-track">
        <figure v-for="(t, i) in p.testimonials.value" :key="i" class="sd-testi-card">
          <span class="sd-testi-quote" aria-hidden="true">“</span>
          <blockquote>{{ t.text }}</blockquote>
          <figcaption><strong>{{ t.name }}</strong><span v-if="t.detail">{{ t.detail }}</span></figcaption>
        </figure>
      </div>
    </section>

    <!-- ===== FAQ ===== -->
    <section v-if="faqsTop.length && on('faq')" v-reveal class="sd-faq" :style="{ order: pos('faq') }" aria-labelledby="sd-faq-t">
      <header class="sd-sec-h"><p class="sd-eyebrow">Dudas</p><h2 id="sd-faq-t">{{ custom.faqs_title || 'Preguntas frecuentes' }}</h2></header>
      <ul class="sd-faq-list">
        <li v-for="(f, i) in faqsTop" :key="i" class="sd-faq-item" :class="{ on: faqOpen === i }">
          <button type="button" class="sd-faq-q" :aria-expanded="faqOpen === i" @click="faqOpen = faqOpen === i ? -1 : i">
            {{ f.q }} <AppIcon name="chevron-down" :size="16" />
          </button>
          <p v-show="faqOpen === i" class="sd-faq-a">{{ f.a }}</p>
        </li>
      </ul>
    </section>

    <!-- ===== Contacto: formulario corto + horarios ===== -->
    <section v-if="(showContact || p.waBase.value) && on('contact')" v-reveal id="contacto" class="sd-contact" :style="{ order: pos('contact') }" aria-labelledby="sd-contact-t">
      <header class="sd-sec-h"><p class="sd-eyebrow">Contacto</p><h2 id="sd-contact-t">Contanos qué necesitás</h2></header>
      <div class="sd-contact-grid">
        <form v-if="p.waBase.value" class="sd-form" novalidate @submit.prevent="submit">
          <div class="sd-form-meter" aria-hidden="true">
            <span class="seg" :class="{ done: formMeter[0] }" /><span class="seg" :class="{ done: formMeter[1] }" /><span class="seg" :class="{ done: formMeter[2] }" />
            <span class="lbl">tu pedido</span>
          </div>
          <label>Tu nombre<input v-model="form.name" type="text" autocomplete="name" maxlength="60" placeholder="María Pérez" /></label>
          <label v-if="p.serviceItems.value.length">Servicio
            <select v-model="form.service">
              <option value="">Consulta general</option>
              <option v-for="it in p.serviceItems.value" :key="it.id" :value="it.name">{{ it.name }}</option>
            </select>
          </label>
          <label>Mensaje <em>(opcional)</em><textarea v-model="form.message" rows="3" maxlength="400" placeholder="Contame un poco más…"></textarea></label>
          <p v-if="formErr" class="sd-form-err" role="alert">{{ formErr }}</p>
          <button type="submit" class="sd-cta"><AppIcon name="whatsapp" :size="16" /> Enviar por WhatsApp</button>
        </form>
        <div class="sd-contact-side">
          <ScheduleCard v-if="p.hours.value.length" :hours="p.hours.value" title="Horarios de atención" />
          <ul class="sd-contact-meta">
            <li v-if="location"><AppIcon name="map-pin" :size="15" /> {{ location }}</li>
            <li v-if="p.store.value?.location_address"><AppIcon name="store" :size="15" /> {{ p.store.value.location_address }}</li>
            <li v-for="s in p.socials.value" :key="s.key"><a :href="s.url" target="_blank" rel="noopener"><AppIcon :name="s.key" :size="15" /> {{ s.label }}</a></li>
          </ul>
        </div>
      </div>
    </section>
  </main>
</div>
</template>
