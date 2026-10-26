<script setup>
import { ref, reactive, computed, inject, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { storesApi, SERVICE_ICONS } from '../api/stores.api.js'
import { extractApiError } from '../api/http.js'
import { formatARS } from '../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct } from '../api/catalog.api.js'
import { storeHostSlug } from '../config/env.js'
import AppIcon from '../components/AppIcon.vue'
import { vReveal } from '../directives/reveal.js'
import { openStatus } from '../utils/storeHours.js'
import '../assets/store-page-v2.css'

// Diseño "Dúo" (antes prototipo "Opción 2"): la misma información de la
// portada actual con los elementos acomodados distinto — hero sobre fondo
// claro con la imagen a la izquierda y el copy a la derecha, números
// pegados al hero, destacados como tira, productos en riel horizontal,
// servicios numerados, Nosotros espejado (foto a la izquierda), galería en
// tira horizontal, FAQ en dos columnas y Contáctanos con el formulario a la
// izquierda. Es la portada real cuando la tienda elige el diseño 'duo'
// (StoreHomeView la monta) y sigue abierta como vista previa en /<slug>/v2
// (ruta store-alt): solo en ese caso se muestra la barra .sp2-preview.
const ctx = inject('storePage')
const { slug, custom, shopName, nameFont, initial, location, hasAbout, showContact, showCatalog, hasDesignAdvanced, loadPublicCatalog } = ctx

const router = useRouter()
const route = useRoute()
const isPreview = computed(() => route.name === 'store-alt')
const homeTo = computed(() => ({ name: 'store-public', params: storeHostSlug ? {} : { slug: slug.value } }))
const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
// Página de servicios (site_templates): acceso desde la portada además del
// catálogo.
const servicesPage = ctx.showServices
const servicesTo = computed(() => ({ name: 'store-services', params: storeHostSlug ? {} : { slug: slug.value } }))
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })
const openProduct = (p) => router.push(productTo(p))

// --- Presentación: hero partido sobre fondo claro (placa de imagen a la
// izquierda, identidad a la derecha — espejo del hero clásico de la opción 1).
const heroTitleIsName = computed(() => !custom.value.headline?.trim())
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value)
const titleSplit = computed(() => {
  const words = heroTitle.value.split(/\s+/)
  return words.length > 1 ? { head: words.slice(0, -1).join(' '), last: words[words.length - 1] } : { head: '', last: heroTitle.value }
})
const heroBadge = computed(() => (heroTitleIsName.value ? (location.value || (showCatalog.value ? 'Catálogo online' : 'Sitio oficial')) : shopName.value))
const heroBadgeIcon = computed(() => (heroTitleIsName.value ? (location.value ? 'map-pin' : 'store') : ''))

// "Abierto ahora / Cerrado": sale de los horarios cargados (texto libre);
// si no se pueden interpretar no se muestra nada. Se recalcula cada minuto.
const now = ref(new Date())
let clock = null
const openNow = computed(() => (custom.value.show_hours !== false ? openStatus(custom.value.hours, now.value) : null))
const heroMeta = computed(() => {
  const items = []
  if (!heroTitleIsName.value && location.value) items.push({ key: 'loc', icon: 'map-pin', text: location.value })
  if (openNow.value) items.push({ key: 'open', state: openNow.value.state, text: openNow.value.text })
  if (custom.value.about_years) items.push({ key: 'years', icon: 'clock', text: `+${custom.value.about_years} años de trayectoria` })
  return items
})

// Imágenes del collage: portada propia (premium), carrusel y primeras fotos
// de producto, sin repetir. Sin imágenes la placa cae al logo/inicial.
const cover = computed(() => (hasDesignAdvanced.value ? custom.value.cover || '' : ''))
const catalog = ref({ categories: [], brands: [], products: [] })
const railProducts = computed(() => catalog.value.products.slice(0, 10))
const catOf = (p) => catalog.value.categories.find((c) => c.id === p.category)?.name || ''
const brandOf = (p) => catalog.value.brands.find((b) => b.id === p.brand)?.name || ''
const heroImgPool = computed(() => [...new Set([
  cover.value,
  ...(custom.value.carousel || []).map((i) => i.url),
  ...catalog.value.products.map((p) => p.image)
].filter(Boolean))])
const heroImgA = computed(() => heroImgPool.value[0] || '')
const heroImgB = computed(() => heroImgPool.value[1] || '')
const heroChip = computed(() => (openNow.value
  ? { icon: 'clock', text: openNow.value.text }
  : { icon: location.value ? 'map-pin' : 'shield-check', text: location.value || 'Atención personalizada' }))

async function loadCatalog() {
  if (!showCatalog.value) return
  try {
    catalog.value = await loadPublicCatalog({ sort: 'recent' })
  } catch {
    catalog.value = { categories: [], brands: [], products: [] }
  }
}

// --- Destacados como tira compacta (los mismos datos que las tarjetas de
// la opción 1: se arman con lo que el negocio realmente tiene cargado). ---
const highlights = computed(() => {
  const list = []
  if (showCatalog.value) list.push({ icon: 'package', title: 'Catálogo online', text: 'Productos y precios actualizados.', to: catalogTo.value })
  if (servicesPage.value) list.push({ icon: 'wrench', title: 'Servicios', text: 'Presupuesto y pedido por WhatsApp.', to: servicesTo.value })
  if (showContact.value) list.push({ icon: 'message-circle', title: 'Consultas directas', text: 'Te respondemos a la brevedad.', href: '#contacto' })
  if (location.value) list.push({ icon: 'map-pin', title: 'Dónde estamos', text: location.value })
  if (custom.value.about_years) list.push({ icon: 'clock', title: `+${custom.value.about_years} años`, text: 'De trayectoria y experiencia.' })
  list.push(
    { icon: 'users', title: 'Atención personalizada', text: 'Te acompañamos en tu compra.' },
    { icon: 'shield-check', title: 'Información clara', text: 'Precios claros, sin sorpresas.' }
  )
  return list.slice(0, 4)
})

// --- Tus números: en esta opción la banda va pegada al hero (en la
// portada actual viaja a media página según el orden de secciones). ---
const listOf = (value) => (Array.isArray(value) ? value : [])
const stats = computed(() => listOf(custom.value.stats))
const showStats = computed(() => custom.value.show_stats !== false && stats.value.length > 0)

// --- Nosotros espejado: la foto va a la izquierda y el contenido a la
// derecha (la opción 1 lo hace al revés). La tarjeta de trayectoria/misión
// viaja dentro de la columna de texto en vez de en una banda aparte. ---
const aboutSpecialties = computed(() => String(custom.value.about_specialties || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean)
  .slice(0, 12))
const hasAboutCard = computed(() => Boolean(custom.value.about_years || custom.value.about_mission?.trim()))
const aboutTitle = computed(() => custom.value.about_title?.trim() || 'Sobre nosotros')
const decor = computed(() => (hasDesignAdvanced.value ? (custom.value.decor || []).slice(0, 3) : []))
const decorAbout = computed(() => (hasAbout.value ? decor.value[0] || null : null))
const decorPool = computed(() => decor.value.slice(decorAbout.value ? 1 : 0))
const decorBand = computed(() => decorPool.value[0] || null)
const decorContact = computed(() => (showContact.value ? decorPool.value[decorBand.value ? 1 : 0] || null : null))
const showcaseTitle = computed(() => (showContact.value ? 'Hablemos de lo que buscás' : `Conocé ${shopName.value}`))
const showcaseText = computed(() => custom.value.about_mission?.trim() || '')

// --- Qué ofrecemos: filas numeradas en vez de grilla de tarjetas. ---
const services = computed(() => listOf(custom.value.services))
const showServices = computed(() => custom.value.show_services !== false && services.value.length > 0)
const servicesTitle = computed(() => custom.value.services_title?.trim() || 'Qué ofrecemos')
const serviceIcon = (key) => (SERVICE_ICONS[key] ? key : 'package')
const eyebrowUnless = (label, title) => (String(title || '').trim().toLowerCase() === label.toLowerCase() ? '' : label)
const servicesEyebrow = computed(() => eyebrowUnless('Servicios', servicesTitle.value))

// --- Testimonios: la primera cita protagoniza y el resto baja en lista. ---
const testimonials = computed(() => listOf(custom.value.testimonials))
const showTestimonials = computed(() => custom.value.show_testimonials !== false && testimonials.value.length > 0)
const testimonialsTitle = computed(() => custom.value.testimonials_title?.trim() || 'Lo que dicen nuestros clientes')
const testimonialsEyebrow = computed(() => eyebrowUnless('Clientes', testimonialsTitle.value))
// Citas de testimonios 100% iguales: se mide la más alta y se iguala el
// resto con min-height; se recalcula al cambiar el tamaño o la lista.
const testiList = ref(null)
let testiRO = null
function equalizeTestimonials() {
  const list = testiList.value
  if (!list) return
  const cards = list.querySelectorAll('.sp2-quote')
  cards.forEach((c) => { c.style.minHeight = '' })
  const max = Math.ceil(Math.max(0, ...[...cards].map((c) => c.offsetHeight)))
  if (max) cards.forEach((c) => { c.style.minHeight = `${max}px` })
}
watch(testiList, (el) => {
  testiRO?.disconnect()
  testiRO = null
  if (el && 'ResizeObserver' in window) { testiRO = new ResizeObserver(equalizeTestimonials); testiRO.observe(el) }
  nextTick(equalizeTestimonials)
})
watch(testimonials, () => nextTick(equalizeTestimonials))

// --- Galería en tira horizontal (misma fuente que la grilla de la opción 1).
const gallery = computed(() => custom.value.gallery || [])
const showGallery = computed(() => ctx.showGallery.value)
const lightboxIndex = ref(-1)
const lightboxImage = computed(() => (lightboxIndex.value >= 0 ? gallery.value[lightboxIndex.value] || null : null))
const openLightbox = (index) => { lightboxIndex.value = index }
const closeLightbox = () => { lightboxIndex.value = -1 }
function stepLightbox(direction) {
  const total = gallery.value.length
  if (total < 2) return
  lightboxIndex.value = ((lightboxIndex.value + direction) % total + total) % total
}

// --- Preguntas frecuentes: encabezado centrado y respuestas en dos columnas.
const faqs = computed(() => listOf(custom.value.faqs))
const showFaqs = computed(() => custom.value.show_faq !== false && faqs.value.length > 0)
const faqsTitle = computed(() => custom.value.faqs_title?.trim() || 'Preguntas frecuentes')
const faqEyebrow = computed(() => eyebrowUnless('Dudas frecuentes', faqsTitle.value))

// --- Llamado a la acción: tarjeta de acento contenida (la opción 1 usa
// una banda a todo lo ancho). ---
const whatsappUrl = computed(() => (custom.value.whatsapp ? `https://wa.me/${custom.value.whatsapp.replace(/\D/g, '')}` : ''))
const showCta = computed(() => custom.value.show_cta !== false
  && Boolean(custom.value.cta_title?.trim() || custom.value.cta_text?.trim()))
const ctaTitle = computed(() => custom.value.cta_title?.trim() || '¿Hablamos?')
const ctaLink = computed(() => {
  if (whatsappUrl.value) return { href: whatsappUrl.value, external: true }
  if (showContact.value) return { href: '#contacto', external: false }
  if (showCatalog.value) return { to: catalogTo.value, external: false }
  if (servicesPage.value) return { to: servicesTo.value, external: false }
  return null
})
const ctaLabel = computed(() => custom.value.cta_label?.trim()
  || (ctaLink.value?.external ? 'Escribinos por WhatsApp' : ctaLink.value?.href === '#contacto' ? 'Contáctanos' : ctaLink.value?.to === servicesTo.value ? 'Ver servicios' : 'Ver catálogo'))

// --- Contáctanos: espejado (formulario a la izquierda, info a la derecha);
// el mapa sigue debajo de las dos columnas. ---
const contactForm = reactive({ name: '', email: '', message: '', website: '', captcha_answer: '' })
const captcha = ref(null)
const captchaLoading = ref(false)
const contactStatus = ref('idle') // idle | loading | success | error
const contactError = ref('')
const instagramUrl = computed(() => (custom.value.instagram ? `https://instagram.com/${custom.value.instagram}` : ''))
const tiktokUrl = computed(() => (custom.value.tiktok ? `https://tiktok.com/@${custom.value.tiktok}` : ''))
const facebookUrl = computed(() => (custom.value.facebook ? `https://facebook.com/${custom.value.facebook}` : ''))
const socials = computed(() => [
  { key: 'instagram', label: 'Instagram', url: instagramUrl.value },
  { key: 'tiktok', label: 'TikTok', url: tiktokUrl.value },
  { key: 'facebook', label: 'Facebook', url: facebookUrl.value }
].filter((s) => s.url))
const hasContactChannels = computed(() => Boolean(whatsappUrl.value || socials.value.length))
const contactHours = computed(() => listOf(custom.value.hours))
const showHours = computed(() => custom.value.show_hours !== false && contactHours.value.length > 0)
// Cinta de anuncios y sección Video (URL de embed ya normalizada en el backend).
const announcements = computed(() => listOf(custom.value.announcements))
const showAnn = computed(() => custom.value.show_announcements !== false && announcements.value.length > 0)
const annLoop = computed(() => [...announcements.value, ...announcements.value, ...announcements.value])
const videoEmbed = computed(() => (custom.value.video_url || '').trim())
const showVideo = computed(() => custom.value.show_video !== false && Boolean(videoEmbed.value))
const videoTitle = computed(() => custom.value.video_title?.trim() || 'Mirá nuestro video')
const mapAddress = computed(() => ctx.store.value?.location_address || '')
const mapUrl = computed(() => (
  mapAddress.value
    ? `https://maps.google.com/maps?q=${encodeURIComponent(mapAddress.value)}&output=embed&z=16`
    : ''
))
const mapLink = computed(() => (mapAddress.value ? `https://maps.google.com/?q=${encodeURIComponent(mapAddress.value)}` : ''))

async function loadCaptcha() {
  captchaLoading.value = true
  try {
    captcha.value = await storesApi.contactCaptcha(slug.value)
    contactForm.captcha_answer = ''
  } catch {
    captcha.value = null
  } finally {
    captchaLoading.value = false
  }
}

async function submitContact() {
  if (contactStatus.value === 'loading') return
  contactError.value = ''
  contactStatus.value = 'loading'
  try {
    await storesApi.sendContact(slug.value, {
      name: contactForm.name.trim(),
      email: contactForm.email.trim(),
      message: contactForm.message.trim(),
      website: contactForm.website,
      challenge_id: captcha.value?.challenge_id || '',
      captcha_answer: contactForm.captcha_answer.trim()
    })
    contactStatus.value = 'success'
    contactForm.name = contactForm.email = contactForm.message = contactForm.website = ''
    loadCaptcha()
  } catch (e) {
    contactStatus.value = 'error'
    const parsed = extractApiError(e)
    contactError.value = parsed.captcha_answer || parsed.name || parsed.email || parsed.message
      || parsed.detail || parsed.nonField || 'No se pudo enviar el mensaje. Intentá de nuevo.'
    loadCaptcha()
  }
}

const copied = ref(false)
async function share() {
  const data = { title: shopName.value, text: custom.value.description?.trim() || `Mirá ${shopName.value}`, url: window.location.href }
  if (navigator.share) {
    try {
      await navigator.share(data)
      return
    } catch (e) {
      if (e?.name === 'AbortError') return
    }
  }
  try {
    await navigator.clipboard.writeText(window.location.href)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2500)
  } catch {
    // Sin clipboard disponible: el link ya está en la barra del navegador.
  }
}

const onKey = (e) => {
  if (e.key === 'Escape') closeLightbox()
  else if (lightboxIndex.value >= 0 && e.key === 'ArrowLeft') stepLightbox(-1)
  else if (lightboxIndex.value >= 0 && e.key === 'ArrowRight') stepLightbox(1)
}

onMounted(() => {
  if (showContact.value) loadCaptcha()
  loadCatalog()
  window.addEventListener('keydown', onKey)
  clock = setInterval(() => { now.value = new Date() }, 60000)
})

onBeforeUnmount(() => {
  clearInterval(clock)
  testiRO?.disconnect()
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
<div class="sp-page-root sp2">
  <!-- ===== Barra de vista previa: solo en /<slug>/v2 (ruta store-alt);
       cuando 'duo' es el diseño elegido esta composición ES la portada ===== -->
  <div v-if="isPreview" class="sp2-preview">
    <div class="sp-container sp2-preview-inner">
      <span class="sp2-preview-badge"><AppIcon name="eye" :size="13" /> Vista previa · Diseño Dúo</span>
      <span class="sp2-preview-note">Así se vería tu portada con el diseño Dúo: tu web actual no cambia.</span>
      <RouterLink class="sp2-preview-link" :to="homeTo">Ver versión actual <AppIcon name="arrow-right" :size="13" /></RouterLink>
    </div>
  </div>

  <!-- ===== Presentación: hero partido sobre fondo claro — placa de imagen
       a la izquierda, identidad a la derecha (espejo de la opción 1) ===== -->
  <section class="sp2-hero">
    <div class="sp2-hero-decor" aria-hidden="true">
      <span class="sp2-blob"></span>
      <span class="sp2-ring"></span>
      <span class="sp2-plus p1"></span>
      <span class="sp2-plus p2"></span>
    </div>
    <div class="sp-container sp2-hero-grid">
      <div v-reveal class="sp2-hero-art">
        <figure class="sp2-hero-plate" :class="{ 'is-logo': !heroImgA }">
          <img v-if="heroImgA" :src="heroImgA" alt="" fetchpriority="high" />
          <img v-else-if="custom.logo" :src="custom.logo" :alt="`Logo de ${shopName}`" />
          <span v-else class="sp2-hero-initial" aria-hidden="true">{{ initial }}</span>
        </figure>
        <figure v-if="heroImgB" class="sp2-hero-plate small" aria-hidden="true">
          <img :src="heroImgB" alt="" loading="lazy" />
        </figure>
        <span class="sp2-hero-chip"><AppIcon :name="heroChip.icon" :size="14" /> {{ heroChip.text }}</span>
      </div>
      <div class="sp2-hero-copy">
        <p v-reveal class="sp2-badge">
          <AppIcon v-if="heroBadgeIcon" :name="heroBadgeIcon" :size="13" />
          {{ heroBadge }}
        </p>
        <h1 v-reveal="120" class="sp2-hero-title" :class="{ 'is-name': heroTitleIsName }" :style="heroTitleIsName ? nameFont : null">{{ titleSplit.head }} <span class="sp2-mark">{{ titleSplit.last }}</span></h1>
        <p v-if="custom.description" v-reveal="200" class="sp2-hero-sub">{{ custom.description }}</p>
        <div v-reveal="280" class="sp2-hero-ctas">
          <RouterLink v-if="showCatalog" class="sp-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
          <RouterLink v-else-if="servicesPage" class="sp-btn" :to="servicesTo">Ver servicios <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
          <RouterLink v-if="servicesPage && showCatalog" class="sp-btn ghost" :to="servicesTo"><AppIcon name="wrench" :size="16" /> Servicios</RouterLink>
          <a v-if="showContact" class="sp-btn ghost" href="#contacto"><AppIcon name="message-circle" :size="16" /> Contáctanos</a>
          <button type="button" class="sp-icon-btn" :aria-label="copied ? 'Link copiado' : 'Compartir tienda'" :title="copied ? 'Link copiado' : 'Compartir'" @click="share">
            <AppIcon :name="copied ? 'check' : 'share-2'" :size="17" />
          </button>
        </div>
        <ul v-if="heroMeta.length" v-reveal="360" class="sp2-hero-meta">
          <li v-for="m in heroMeta" :key="m.key" :class="m.state ? `sp-open is-${m.state}` : null"><span v-if="m.state" class="sp-live-dot" aria-hidden="true"></span><AppIcon v-else :name="m.icon" :size="14" /> {{ m.text }}</li>
        </ul>
      </div>
    </div>
  </section>

  <!-- ===== Cinta de anuncios: marquee en bucle bajo la portada ===== -->
  <div v-if="showAnn" class="sp-ann" role="note" aria-label="Anuncios de la tienda">
    <div class="sp-ann-track">
      <span v-for="(a, i) in annLoop" :key="i" class="sp-ann-item" :aria-hidden="i >= announcements.length"><AppIcon :name="serviceIcon(a.icon)" :size="14" />{{ a.text }}</span>
    </div>
  </div>

  <!-- ===== Tus números: banda de acento pegada al hero (prueba social
       inmediata; en la opción 1 viaja a media página) ===== -->
  <section v-if="showStats" class="sp2-stats" aria-label="Cifras del negocio">
    <div class="sp-container sp2-stats-row">
      <div v-for="(s, i) in stats" :key="i" v-reveal="i * 80" class="sp2-stat">
        <strong>{{ s.value }}</strong>
        <span>{{ s.label }}</span>
      </div>
    </div>
  </section>

  <!-- ===== Destacados: tira compacta dividida en columnas (en la opción 1
       son tarjetas sueltas sobre fondo) ===== -->
  <section v-if="custom.show_highlights !== false" class="sp2-strip">
    <div class="sp-container sp2-strip-row">
      <component
        :is="h.to ? 'RouterLink' : h.href ? 'a' : 'div'" v-for="h in highlights" :key="h.title"
        class="sp2-strip-item" :to="h.to" :href="h.href"
      >
        <span class="sp2-strip-icon" aria-hidden="true"><AppIcon :name="h.icon" :size="19" /></span>
        <span class="sp2-strip-copy"><strong>{{ h.title }}</strong>{{ h.text }}</span>
      </component>
    </div>
  </section>

  <!-- ===== Productos destacados: riel horizontal (en la opción 1 es una
       grilla) — la tarjeta entera abre la ficha ===== -->
  <section v-if="railProducts.length" class="sp2-rail" aria-labelledby="sp2-rail-title">
    <div class="sp-container">
      <div v-reveal class="sp2-sec-head">
        <div>
          <p class="sp2-eyebrow">Recién llegados</p>
          <h2 id="sp2-rail-title" class="sp2-title">Productos destacados</h2>
        </div>
        <RouterLink class="sp2-viewall" :to="catalogTo">Ver todo el catálogo <AppIcon name="arrow-right" :size="14" class="sp-arrow" /></RouterLink>
      </div>
      <div class="sp2-rail-track">
        <article
          v-for="(p, i) in railProducts" :key="p.id" v-reveal="(i % 4) * 80"
          class="sp2-card" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
          @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
        >
          <div class="sp2-card-img">
            <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
            <span v-else class="sp2-card-placeholder"><AppIcon name="package" :size="28" /></span>
            <span v-if="isNewProduct(p)" class="sp2-card-flag">Nuevo</span>
            <span v-if="productOffer(p) != null" class="sp2-card-flag offer">-{{ offerPct(p) }}%</span>
          </div>
          <div class="sp2-card-body">
            <p v-if="catOf(p) || brandOf(p)" class="sp2-card-cat">{{ [catOf(p), brandOf(p)].filter(Boolean).join(' · ') }}</p>
            <h3 class="sp2-card-name">{{ p.name }}</h3>
            <span class="sp2-card-price"><s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>{{ formatARS(effectivePrice(p)) }}</span>
          </div>
        </article>
      </div>
    </div>
  </section>

  <!-- ===== Nosotros espejado: foto a la izquierda, texto a la derecha y la
       tarjeta de trayectoria/misión dentro de la columna ===== -->
  <section v-if="hasAbout" id="nosotros" class="sp2-about" aria-labelledby="sp2-about-title">
    <div class="sp-container sp2-about-grid" :class="{ 'no-photo': !decorAbout }">
      <figure v-if="decorAbout" v-reveal class="sp2-about-photo">
        <img :src="decorAbout.url" :alt="`Imagen de ${shopName}`" loading="lazy" />
      </figure>
      <div class="sp2-about-body">
        <div v-reveal="100" class="sp2-about-info">
          <p class="sp2-eyebrow">Conócenos</p>
          <h2 id="sp2-about-title" class="sp2-title">{{ aboutTitle }}</h2>
          <p v-if="custom.about_text" class="sp2-about-text">{{ custom.about_text }}</p>
          <ul v-if="aboutSpecialties.length" class="sp2-about-list">
            <li v-for="s in aboutSpecialties" :key="s"><AppIcon name="check" :size="16" /> <span>{{ s }}</span></li>
          </ul>
        </div>
        <div v-if="hasAboutCard" v-reveal="160" class="sp2-about-card">
          <p v-if="custom.about_years" class="sp2-about-years">
            <strong>+{{ custom.about_years }}</strong>
            <span>años de trayectoria</span>
          </p>
          <blockquote v-if="custom.about_mission" class="sp2-about-mission">
            <span class="sp2-about-mission-label">Nuestra misión</span>
            {{ custom.about_mission }}
          </blockquote>
        </div>
      </div>
    </div>
  </section>

  <!-- ===== Qué ofrecemos: filas numeradas en vez de tarjetas ===== -->
  <section v-if="showServices" class="sp2-services" aria-labelledby="sp2-services-title">
    <div class="sp-container">
      <p v-if="servicesEyebrow" v-reveal class="sp2-eyebrow">{{ servicesEyebrow }}</p>
      <h2 id="sp2-services-title" v-reveal class="sp2-title">{{ servicesTitle }}</h2>
      <ol class="sp2-services-list">
        <li v-for="(s, i) in services" :key="i" v-reveal="(i % 3) * 70">
          <span class="sp2-services-num" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
          <span class="sp2-services-icon" aria-hidden="true"><AppIcon :name="serviceIcon(s.icon)" :size="19" /></span>
          <div class="sp2-services-copy">
            <strong>{{ s.title }}</strong>
            <p v-if="s.text">{{ s.text }}</p>
          </div>
        </li>
      </ol>
      <div v-if="servicesPage" class="sp-more">
        <RouterLink class="sp-btn" :to="servicesTo">Ver precios y pedir por WhatsApp <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
      </div>
    </div>
  </section>

  <!-- ===== Testimonios: columna de encabezado a la izquierda y citas
       apiladas a la derecha (la opción 1 es una grilla uniforme) ===== -->
  <section v-if="showTestimonials" class="sp2-testimonials" aria-labelledby="sp2-testimonials-title">
    <div class="sp-container sp2-testimonials-grid">
      <div v-reveal class="sp2-testimonials-head">
        <p v-if="testimonialsEyebrow" class="sp2-eyebrow">{{ testimonialsEyebrow }}</p>
        <h2 id="sp2-testimonials-title" class="sp2-title">{{ testimonialsTitle }}</h2>
      </div>
      <div ref="testiList" class="sp2-testimonials-list">
        <figure v-for="(t, i) in testimonials" :key="i" v-reveal="i * 80" class="sp2-quote" :class="{ featured: i === 0 }">
          <blockquote class="sp2-quote-text">{{ t.text }}</blockquote>
          <figcaption class="sp2-quote-by">
            <strong>{{ t.name }}</strong>
            <span v-if="t.detail">{{ t.detail }}</span>
          </figcaption>
        </figure>
      </div>
    </div>
  </section>

  <!-- ===== Banda decorativa espejada: texto a la izquierda, imagen a la
       derecha (la opción 1 la pone al revés) ===== -->
  <section v-if="decorBand" class="sp2-showcase">
    <div class="sp-container sp2-showcase-grid">
      <div v-reveal class="sp2-showcase-copy">
        <p class="sp2-eyebrow">{{ shopName }}</p>
        <h2 class="sp2-title">{{ showcaseTitle }}</h2>
        <p v-if="showcaseText" class="sp2-showcase-text">{{ showcaseText }}</p>
        <div class="sp2-showcase-ctas">
          <RouterLink v-if="showCatalog" class="sp-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
          <RouterLink v-else-if="servicesPage" class="sp-btn" :to="servicesTo">Ver servicios <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
          <RouterLink v-if="servicesPage && showCatalog" class="sp-btn ghost" :to="servicesTo"><AppIcon name="wrench" :size="16" /> Servicios</RouterLink>
          <a v-if="showContact" class="sp-btn ghost" href="#contacto"><AppIcon name="message-circle" :size="16" /> Contáctanos</a>
        </div>
      </div>
      <figure v-reveal="120" class="sp2-showcase-frame" aria-hidden="true">
        <img :src="decorBand.url" alt="" loading="lazy" />
      </figure>
    </div>
  </section>

  <!-- ===== Galería: tira horizontal con scroll en vez de grilla ===== -->
  <section v-if="showGallery" id="galeria" class="sp2-gallery" aria-labelledby="sp2-gallery-title">
    <div class="sp-container">
      <h2 id="sp2-gallery-title" v-reveal class="sp2-title">Galería</h2>
      <div class="sp2-gallery-track">
        <button
          v-for="(img, i) in gallery" :key="img.id" v-reveal="(i % 4) * 70"
          type="button" class="sp2-gallery-item"
          :aria-label="`Ver imagen ${i + 1} en grande`"
          @click="openLightbox(i)"
        >
          <img :src="img.url" :alt="`Imagen ${i + 1} de la galería de ${shopName}`" loading="lazy" />
        </button>
      </div>
    </div>
  </section>

  <!-- ===== Preguntas frecuentes: encabezado centrado y respuestas en dos
       columnas (la opción 1 alinea el intro a la izquierda en una sola) ===== -->
  <section v-if="showFaqs" class="sp2-faq" aria-labelledby="sp2-faq-title">
    <div class="sp-container">
      <div v-reveal class="sp2-faq-head">
        <p v-if="faqEyebrow" class="sp2-eyebrow">{{ faqEyebrow }}</p>
        <h2 id="sp2-faq-title" class="sp2-title">{{ faqsTitle }}</h2>
      </div>
      <div class="sp2-faq-cols">
        <details v-for="(f, i) in faqs" :key="i" v-reveal="(i % 4) * 60" class="sp2-faq-item">
          <summary>{{ f.q }}<span class="sp2-faq-caret" aria-hidden="true"><AppIcon name="chevron-down" :size="16" /></span></summary>
          <p class="sp2-faq-answer">{{ f.a }}</p>
        </details>
      </div>
    </div>
  </section>

  <!-- ===== Video: embed de YouTube/Vimeo en su propia sección ===== -->
  <section v-if="showVideo" class="sp-video" aria-labelledby="sp-video-title">
    <div class="sp-container">
      <header v-reveal class="sp-video-head">
        <h2 id="sp-video-title" class="sp-video-title">{{ videoTitle }}</h2>
      </header>
      <div v-reveal="80" class="sp-video-frame">
        <iframe
          :src="videoEmbed" :title="videoTitle" loading="lazy" allowfullscreen
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          referrerpolicy="strict-origin-when-cross-origin"
        ></iframe>
      </div>
    </div>
  </section>

  <!-- ===== Llamado a la acción: tarjeta de acento contenida ===== -->
  <section v-if="showCta" class="sp2-cta">
    <div class="sp-container">
      <div v-reveal class="sp2-cta-card">
        <h2 class="sp2-cta-title">{{ ctaTitle }}</h2>
        <p v-if="custom.cta_text" class="sp2-cta-text">{{ custom.cta_text }}</p>
        <component
          v-if="ctaLink" :is="ctaLink.to ? 'RouterLink' : 'a'" class="sp-btn sp2-cta-btn"
          :to="ctaLink.to" :href="ctaLink.href"
          :target="ctaLink.external ? '_blank' : null" :rel="ctaLink.external ? 'noopener' : null"
        >
          {{ ctaLabel }} <AppIcon name="arrow-right" :size="16" class="sp-arrow" />
        </component>
      </div>
    </div>
  </section>

  <!-- ===== Contáctanos espejado: formulario a la izquierda, info a la
       derecha y el mapa debajo a todo lo ancho ===== -->
  <section v-if="showContact" id="contacto" class="sp2-contact" aria-labelledby="sp2-contact-title">
    <div class="sp-container">
      <div class="sp2-contact-grid">
        <form v-reveal class="sp-form" novalidate @submit.prevent="submitContact">
          <div v-if="contactStatus === 'success'" class="sp-sent" role="status">
            <span class="sp-sent-check" aria-hidden="true"><AppIcon name="check" :size="30" :stroke="2.25" /></span>
            <strong>Mensaje enviado</strong>
            <p>Gracias por escribirnos. Te respondemos a la brevedad al email que dejaste.</p>
            <button type="button" class="sp-btn ghost sm" @click="contactStatus = 'idle'">Enviar otro mensaje</button>
          </div>
          <template v-else>
            <div class="sp-form-head">
              <span class="sp-form-badge" aria-hidden="true"><AppIcon name="message-circle" :size="20" /></span>
              <div>
                <strong>Dejanos tu mensaje</strong>
                <span>Respondemos en el día, de lunes a sábado.</span>
              </div>
            </div>
            <div class="sp-form-row">
              <div class="sp-field">
                <label for="sp-contact-name">Tu nombre</label>
                <div class="sp-input-wrap">
                  <AppIcon name="user" :size="16" aria-hidden="true" />
                  <input id="sp-contact-name" v-model="contactForm.name" class="sp-input" type="text" maxlength="80" autocomplete="name" placeholder="Cómo te llamás" required />
                </div>
              </div>
              <div class="sp-field">
                <label for="sp-contact-email">Tu email</label>
                <div class="sp-input-wrap">
                  <AppIcon name="mail" :size="16" aria-hidden="true" />
                  <input id="sp-contact-email" v-model="contactForm.email" class="sp-input" type="email" autocomplete="email" placeholder="nombre@correo.com" required />
                </div>
              </div>
            </div>
            <div class="sp-field">
              <label for="sp-contact-message">Mensaje</label>
              <textarea id="sp-contact-message" v-model="contactForm.message" class="sp-input sp-textarea" rows="4" maxlength="2000" placeholder="Contanos en qué te podemos ayudar" required></textarea>
              <span class="sp-counter" aria-hidden="true">{{ contactForm.message.length }} / 2000</span>
            </div>
            <div class="sp-field">
              <label for="sp-contact-captcha">Verificación rápida</label>
              <div class="sp-captcha-row">
                <span class="sp-captcha-q"><AppIcon name="shield-check" :size="16" aria-hidden="true" /> {{ captcha?.question || 'Cargando…' }}</span>
                <input id="sp-contact-captcha" v-model="contactForm.captcha_answer" class="sp-input" type="text" inputmode="numeric" autocomplete="off" placeholder="Respuesta" required />
                <button type="button" class="sp-icon-btn" :disabled="captchaLoading" aria-label="Nueva pregunta de verificación" title="Nueva pregunta" @click="loadCaptcha">
                  <AppIcon name="refresh" :size="15" />
                </button>
              </div>
            </div>
            <!-- Honeypot: invisible para personas; los bots lo completan y se descartan. -->
            <div class="sp-hp" aria-hidden="true">
              <label for="sp-contact-website">Website</label>
              <input id="sp-contact-website" v-model="contactForm.website" type="text" tabindex="-1" autocomplete="off" />
            </div>
            <p v-if="contactError" class="sp-form-error" role="alert">{{ contactError }}</p>
            <div class="sp-form-foot">
              <button type="submit" class="sp-btn" :disabled="contactStatus === 'loading' || !captcha">
                <span v-if="contactStatus === 'loading'" class="spinner" aria-hidden="true"></span>
                <AppIcon v-else name="mail" :size="16" />
                Enviar mensaje
              </button>
              <span class="sp-form-note"><AppIcon name="lock" :size="13" aria-hidden="true" /> Tus datos solo se usan para responderte.</span>
            </div>
          </template>
        </form>
        <div v-reveal="140" class="sp2-contact-info">
          <p class="sp2-eyebrow">Contacto</p>
          <h2 id="sp2-contact-title" class="sp2-title">Contáctanos</h2>
          <p class="sp2-contact-sub">Escribinos tu consulta y te respondemos a la brevedad.</p>
          <p v-if="mapAddress" class="sp-map-address"><AppIcon name="map-pin" :size="14" /> {{ mapAddress }}</p>
          <ul v-if="showHours" class="sp-contact-hours">
            <li v-for="(h, i) in contactHours" :key="i">
              <AppIcon name="clock" :size="14" aria-hidden="true" />
              <span>{{ h.label }}</span>
              <strong>{{ h.value }}</strong>
            </li>
          </ul>
          <div v-if="hasContactChannels" class="sp2-contact-channels">
            <a v-if="whatsappUrl" class="sp-btn" :href="whatsappUrl" target="_blank" rel="noopener">
              <AppIcon name="whatsapp" :size="16" /> WhatsApp
            </a>
            <a
              v-for="s in socials" :key="s.key" class="sp-icon-btn"
              :href="s.url" target="_blank" rel="noopener" :aria-label="s.label" :title="s.label"
            >
              <AppIcon :name="s.key" :size="17" />
            </a>
          </div>
          <figure v-if="decorContact" class="sp2-contact-photo" aria-hidden="true">
            <img :src="decorContact.url" alt="" loading="lazy" />
          </figure>
        </div>
      </div>
      <div v-if="mapUrl" v-reveal="120" class="sp-map-frame sp2-map">
        <iframe
          :src="mapUrl"
          title="Mapa con la ubicación del negocio"
          loading="lazy"
          referrerpolicy="no-referrer-when-downgrade"
          allowfullscreen
        ></iframe>
        <a class="sp-map-open" :href="mapLink" target="_blank" rel="noopener">
          <AppIcon name="map-pin" :size="14" /> Abrir en Google Maps <AppIcon name="arrow-up-right" :size="13" />
        </a>
      </div>
    </div>
  </section>

  <!-- ===== Galería: visor de imagen (mismo modal que la opción 1) ===== -->
  <Transition name="sp-modal">
  <div v-if="lightboxImage" class="sp-lightbox" role="dialog" aria-modal="true" aria-label="Visor de la galería" @click.self="closeLightbox">
    <button type="button" class="sp-modal-close" aria-label="Cerrar" @click="closeLightbox">
      <AppIcon name="x" :size="18" />
    </button>
    <button v-if="gallery.length > 1" type="button" class="sp-lightbox-arrow prev" aria-label="Imagen anterior" @click="stepLightbox(-1)">
      <AppIcon name="chevron-left" :size="22" />
    </button>
    <img :key="lightboxImage.id" class="sp-lightbox-img" :src="lightboxImage.url" :alt="`Imagen de la galería de ${shopName}`" />
    <button v-if="gallery.length > 1" type="button" class="sp-lightbox-arrow next" aria-label="Imagen siguiente" @click="stepLightbox(1)">
      <AppIcon name="chevron-right" :size="22" />
    </button>
    <span v-if="gallery.length > 1" class="sp-lightbox-count">{{ lightboxIndex + 1 }} / {{ gallery.length }}</span>
  </div>
  </Transition>
</div>
</template>
