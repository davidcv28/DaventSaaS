<script setup>
import { ref, reactive, computed, inject, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { storesApi, SERVICE_ICONS } from '../api/stores.api.js'
import { extractApiError } from '../api/http.js'
import { formatARS } from '../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct } from '../api/catalog.api.js'
import { storeHostSlug } from '../config/env.js'
import AppIcon from '../components/AppIcon.vue'
import { vReveal } from '../directives/reveal.js'
import { openStatus } from '../utils/storeHours.js'
import '../assets/store-bloque.css'

// Diseño "Bloque": grid suizo de bordes duros — papel y tinta con reglas
// visibles, titulares Archivo XXL en mayúsculas, metadata en JetBrains Mono,
// acento a bloque y motion mecánico (wipe por palabra, cinta marquee). Es la
// portada real cuando la tienda elige 'bloque' (StoreHomeView la monta).
const ctx = inject('storePage')
const { slug, custom, shopName, nameFont, initial, location, hasAbout, showContact, showCatalog, hasDesignAdvanced, loadPublicCatalog } = ctx

const router = useRouter()
const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${slug.value}` }))
const catalogTo = computed(() => ({ path: storeHostSlug ? '/catalogo' : `/${slug.value}/catalogo` }))
// Página de servicios (site_templates): acceso desde la portada además del
// catálogo.
const servicesPage = ctx.showServices
const servicesTo = computed(() => ({ path: storeHostSlug ? '/servicios' : `/${slug.value}/servicios` }))
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })
const openProduct = (p) => router.push(productTo(p))

// --- Hero: meta en mono arriba, titular XXL con wipe por palabra y pie en
// 3 celdas (descripción / estado / acciones) divididas por reglas.
const heroTitleIsName = computed(() => !custom.value.headline?.trim())
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value)
const heroWords = computed(() => {
  const words = heroTitle.value.split(/\s+/).filter(Boolean)
  return words.map((w, i) => ({ w, last: i === words.length - 1 }))
})
const heroOn = ref(false)

const now = ref(new Date())
let clock = null
const openNow = computed(() => (custom.value.show_hours !== false ? openStatus(custom.value.hours, now.value) : null))
const heroStatus = computed(() => {
  if (openNow.value) return { live: openNow.value.state === 'open', text: openNow.value.text }
  return { live: showCatalog.value, text: showCatalog.value ? 'Catálogo online' : 'Sitio oficial' }
})

const listOf = (value) => (Array.isArray(value) ? value : [])
const stats = computed(() => listOf(custom.value.stats))
const showStats = computed(() => custom.value.show_stats !== false && stats.value.length > 0)

// Cinta de anuncios (avisos del dueño bajo el hero) y sección Video: la URL
// llega ya normalizada al embed oficial desde el serializer.
const announcements = computed(() => listOf(custom.value.announcements))
const showAnn = computed(() => custom.value.show_announcements !== false && announcements.value.length > 0)
const annLoop = computed(() => [...announcements.value, ...announcements.value, ...announcements.value])
const videoEmbed = computed(() => (custom.value.video_url || '').trim())
const showVideo = computed(() => custom.value.show_video !== false && Boolean(videoEmbed.value))
const videoTitle = computed(() => custom.value.video_title?.trim() || 'Mirá nuestro video')

// Catálogo: vitrina de recientes en grilla (misma fuente que el riel de Dúo).
const catalog = ref({ categories: [], brands: [], products: [] })
const gridProducts = computed(() => catalog.value.products.slice(0, 8))
const catOf = (p) => catalog.value.categories.find((c) => c.id === p.category)?.name || ''
const brandOf = (p) => catalog.value.brands.find((b) => b.id === p.brand)?.name || ''

async function loadCatalog() {
  if (!showCatalog.value) return
  try {
    catalog.value = await loadPublicCatalog({ sort: 'recent' })
  } catch {
    catalog.value = { categories: [], brands: [], products: [] }
  }
}

// Cinta marquee: nombre + highlights/especialidades — datos reales del
// negocio; con la lista corta se repite para el loop continuo.
const aboutSpecialties = computed(() => String(custom.value.about_specialties || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean)
  .slice(0, 6))
const tickerItems = computed(() => {
  const items = [shopName.value]
  if (showCatalog.value) items.push('Catálogo online')
  aboutSpecialties.value.forEach((s) => items.push(s))
  if (location.value) items.push(location.value)
  if (custom.value.about_years) items.push(`+${custom.value.about_years} años`)
  return items.slice(0, 8)
})

// --- Nosotros: cabecera pegada a la izquierda, cuerpo a la derecha.
const aboutTitle = computed(() => custom.value.about_title?.trim() || 'La marca')
const hasMission = computed(() => Boolean(custom.value.about_mission?.trim()))

// --- Qué ofrecemos: filas numeradas separadas por reglas.
const services = computed(() => listOf(custom.value.services))
const showServices = computed(() => custom.value.show_services !== false && services.value.length > 0)
const servicesTitle = computed(() => custom.value.services_title?.trim() || 'Qué ofrecemos')
const serviceIcon = (key) => (SERVICE_ICONS[key] ? key : 'package')

// --- Testimonios: celdas de la misma grilla, cita protagonista primero.
const testimonials = computed(() => listOf(custom.value.testimonials))
const showTestimonials = computed(() => custom.value.show_testimonials !== false && testimonials.value.length > 0)
const testimonialsTitle = computed(() => custom.value.testimonials_title?.trim() || 'Lo que dicen nuestros clientes')

// --- Galería: grilla de placas con el mismo lightbox compartido.
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

// --- Preguntas frecuentes: details con regla superior, chevron mecánico.
const faqs = computed(() => listOf(custom.value.faqs))
const showFaqs = computed(() => custom.value.show_faq !== false && faqs.value.length > 0)
const faqsTitle = computed(() => custom.value.faqs_title?.trim() || 'Preguntas frecuentes')

// --- CTA: bloque de tinta a todo lo ancho con la palabra de la marca.
const whatsappUrl = computed(() => (custom.value.whatsapp ? `https://wa.me/${custom.value.whatsapp.replace(/\D/g, '')}` : ''))
const showCta = computed(() => custom.value.show_cta !== false
  && Boolean(custom.value.cta_title?.trim() || custom.value.cta_text?.trim() || whatsappUrl.value || showCatalog.value))
const ctaTitle = computed(() => custom.value.cta_title?.trim() || shopName.value)
const ctaLink = computed(() => {
  if (whatsappUrl.value) return { href: whatsappUrl.value, external: true }
  if (showContact.value) return { href: '#contacto', external: false }
  if (showCatalog.value) return { to: catalogTo.value, external: false }
  if (servicesPage.value) return { to: servicesTo.value, external: false }
  return null
})
const ctaLabel = computed(() => custom.value.cta_label?.trim()
  || (ctaLink.value?.external ? 'Escribinos por WhatsApp' : ctaLink.value?.href === '#contacto' ? 'Contáctanos' : ctaLink.value?.to === servicesTo.value ? 'Ver servicios' : 'Ver catálogo'))

// --- Contacto: canales e info en celdas + el formulario compartido (sp-form)
// con inputs cuadrados propios del estilo.
const contactForm = reactive({ name: '', email: '', message: '', website: '', captcha_answer: '' })
const captcha = ref(null)
const captchaLoading = ref(false)
const contactStatus = ref('idle')
const contactError = ref('')
const instagramUrl = computed(() => (custom.value.instagram ? `https://instagram.com/${custom.value.instagram}` : ''))
const tiktokUrl = computed(() => (custom.value.tiktok ? `https://tiktok.com/@${custom.value.tiktok}` : ''))
const facebookUrl = computed(() => (custom.value.facebook ? `https://facebook.com/${custom.value.facebook}` : ''))
const socials = computed(() => [
  { key: 'instagram', label: 'Instagram', url: instagramUrl.value },
  { key: 'tiktok', label: 'TikTok', url: tiktokUrl.value },
  { key: 'facebook', label: 'Facebook', url: facebookUrl.value }
].filter((s) => s.url))
const contactHours = computed(() => listOf(custom.value.hours))
const showHours = computed(() => custom.value.show_hours !== false && contactHours.value.length > 0)
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

const onKey = (e) => {
  if (e.key === 'Escape') closeLightbox()
  else if (lightboxIndex.value >= 0 && e.key === 'ArrowLeft') stepLightbox(-1)
  else if (lightboxIndex.value >= 0 && e.key === 'ArrowRight') stepLightbox(1)
}

onMounted(() => {
  if (showContact.value) loadCaptcha()
  loadCatalog()
  requestAnimationFrame(() => { heroOn.value = true })
  window.addEventListener('keydown', onKey)
  clock = setInterval(() => { now.value = new Date() }, 60000)
})

onBeforeUnmount(() => {
  clearInterval(clock)
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
<div class="sp-page-root bq">
  <!-- ===== Hero: meta mono, titular XXL con wipe por palabra y pie en
       3 celdas regladas (descripción / estado / acciones) ===== -->
  <section class="bq-hero">
    <div class="sp-container">
      <p class="bq-meta" aria-hidden="true">
        <span>{{ shopName }}</span>
        <span v-if="location">{{ location }}</span>
        <span>{{ new Date().getFullYear() }}</span>
      </p>
      <h1 class="bq-h1" :class="{ 'is-on': heroOn, 'is-name': heroTitleIsName }">
        <span v-for="(x, i) in heroWords" :key="i" class="bq-w"><span class="bq-wi" :class="{ accent: x.last && !heroTitleIsName }" :style="{ transitionDelay: `${i * 70}ms` }">{{ x.w }}</span></span>
      </h1>
      <div class="bq-hero-foot">
        <p class="bq-hero-desc">{{ custom.description || `Bienvenido a ${shopName}.` }}</p>
        <div class="bq-hero-status">
          <span class="bq-dot" :class="{ live: heroStatus.live }" aria-hidden="true"></span>
          <span class="bq-hero-status-text">{{ heroStatus.text }}</span>
        </div>
        <div class="bq-hero-ctas">
          <RouterLink v-if="showCatalog" class="bq-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="15" /></RouterLink>
          <RouterLink v-else-if="servicesPage" class="bq-btn" :to="servicesTo">Ver servicios <AppIcon name="arrow-right" :size="15" /></RouterLink>
          <RouterLink v-if="servicesPage && showCatalog" class="bq-btn ghost" :to="servicesTo">Servicios</RouterLink>
          <a v-if="showContact" class="bq-btn ghost" href="#contacto">Contacto</a>
          <RouterLink v-else-if="hasAbout" class="bq-btn ghost" :to="{ path: homeTo.path, hash: '#nosotros' }">Nosotros</RouterLink>
        </div>
      </div>
    </div>
  </section>

  <!-- ===== Cinta: nombre + datos reales en loop continuo ===== -->
  <div class="bq-ticker" aria-hidden="true">
    <div class="bq-ticker-track">
      <span v-for="(t, i) in tickerItems" :key="`a-${i}`" class="bq-ticker-item">{{ t }} <i>·</i></span>
      <span v-for="(t, i) in tickerItems" :key="`b-${i}`" class="bq-ticker-item">{{ t }} <i>·</i></span>
    </div>
  </div>

  <!-- ===== Cinta de anuncios: avisos del dueño en banda de acento ===== -->
  <div v-if="showAnn" class="sp-ann" role="note" aria-label="Anuncios de la tienda">
    <div class="sp-ann-track">
      <span v-for="(a, i) in annLoop" :key="i" class="sp-ann-item" :aria-hidden="i >= announcements.length"><AppIcon :name="serviceIcon(a.icon)" :size="14" />{{ a.text }}</span>
    </div>
  </div>

  <!-- ===== Tus números: celdas de grilla pegadas a la cinta ===== -->
  <section v-if="showStats" class="bq-stats" aria-label="Cifras del negocio">
    <div class="sp-container bq-stats-row">
      <div v-for="(s, i) in stats" :key="i" v-reveal="i * 60" class="bq-stat">
        <strong>{{ s.value }}</strong>
        <span>{{ s.label }}</span>
      </div>
    </div>
  </section>

  <!-- ===== Catálogo: cabecera numerada + grilla de placas duras ===== -->
  <section v-if="gridProducts.length" id="catalogo" class="bq-sec" aria-labelledby="bq-prod-title">
    <div class="sp-container">
      <header v-reveal class="bq-sec-head">
        <span class="bq-idx" aria-hidden="true">01</span>
        <h2 id="bq-prod-title" class="bq-h2">Catálogo</h2>
        <RouterLink class="bq-sec-link" :to="catalogTo">Ver todo <AppIcon name="arrow-right" :size="14" /></RouterLink>
      </header>
      <div class="bq-cards">
        <article
          v-for="(p, i) in gridProducts" :key="p.id" v-reveal="(i % 4) * 60"
          class="bq-card" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
          @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
        >
          <figure class="bq-card-plate">
            <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
            <span v-else class="bq-card-ph"><AppIcon name="package" :size="26" /></span>
            <span v-if="isNewProduct(p)" class="bq-card-flag">Nuevo</span>
            <span v-if="productOffer(p) != null" class="bq-card-flag offer">−{{ offerPct(p) }}%</span>
          </figure>
          <div class="bq-card-row">
            <span class="bq-card-idx" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
            <h3 class="bq-card-name">{{ p.name }}</h3>
            <span class="bq-card-price">
              <s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>
              {{ formatARS(effectivePrice(p)) }}
            </span>
          </div>
          <p v-if="catOf(p) || brandOf(p)" class="bq-card-cat">{{ [catOf(p), brandOf(p)].filter(Boolean).join(' / ') }}</p>
        </article>
      </div>
    </div>
  </section>

  <!-- ===== Nosotros: cabecera a la izquierda, texto y especialidades a la
       derecha (el split de la referencia) ===== -->
  <section v-if="hasAbout" id="nosotros" class="bq-sec bq-about" aria-labelledby="bq-about-title">
    <div class="sp-container bq-about-grid">
      <header v-reveal class="bq-sec-head col">
        <span class="bq-idx" aria-hidden="true">02</span>
        <h2 id="bq-about-title" class="bq-h2">{{ aboutTitle }}</h2>
      </header>
      <div class="bq-about-body">
        <p v-if="custom.about_text" v-reveal="80" class="bq-about-text">{{ custom.about_text }}</p>
        <blockquote v-if="hasMission" v-reveal="140" class="bq-about-mission">
          <span class="bq-meta-label">Misión</span>
          {{ custom.about_mission }}
        </blockquote>
        <ul v-if="aboutSpecialties.length" v-reveal="180" class="bq-chips">
          <li v-for="s in aboutSpecialties" :key="s">{{ s }}</li>
        </ul>
        <p v-if="custom.about_years" v-reveal="220" class="bq-about-years"><strong>+{{ custom.about_years }}</strong> años de trayectoria</p>
      </div>
    </div>
  </section>

  <!-- ===== Qué ofrecemos: filas numeradas entre reglas ===== -->
  <section v-if="showServices" class="bq-sec" aria-labelledby="bq-serv-title">
    <div class="sp-container">
      <header v-reveal class="bq-sec-head">
        <span class="bq-idx" aria-hidden="true">03</span>
        <h2 id="bq-serv-title" class="bq-h2">{{ servicesTitle }}</h2>
        <RouterLink v-if="servicesPage" class="bq-sec-link" :to="servicesTo">Ver precios <AppIcon name="arrow-right" :size="14" /></RouterLink>
      </header>
      <ol class="bq-rows">
        <li v-for="(s, i) in services" :key="i" v-reveal="(i % 3) * 60" class="bq-row">
          <span class="bq-row-idx" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
          <span class="bq-row-icon" aria-hidden="true"><AppIcon :name="serviceIcon(s.icon)" :size="17" /></span>
          <div class="bq-row-copy">
            <strong>{{ s.title }}</strong>
            <p v-if="s.text">{{ s.text }}</p>
          </div>
        </li>
      </ol>
    </div>
  </section>

  <!-- ===== Testimonios: citas como celdas de la grilla ===== -->
  <section v-if="showTestimonials" class="bq-sec" aria-labelledby="bq-test-title">
    <div class="sp-container">
      <header v-reveal class="bq-sec-head">
        <span class="bq-idx" aria-hidden="true">04</span>
        <h2 id="bq-test-title" class="bq-h2">{{ testimonialsTitle }}</h2>
      </header>
      <div class="bq-quotes">
        <figure v-for="(t, i) in testimonials" :key="i" v-reveal="(i % 3) * 70" class="bq-quote">
          <blockquote>{{ t.text }}</blockquote>
          <figcaption>
            <strong>{{ t.name }}</strong>
            <span v-if="t.detail">{{ t.detail }}</span>
          </figcaption>
        </figure>
      </div>
    </div>
  </section>

  <!-- ===== Galería: placas regladas con el lightbox compartido ===== -->
  <section v-if="showGallery" id="galeria" class="bq-sec" aria-labelledby="bq-gal-title">
    <div class="sp-container">
      <header v-reveal class="bq-sec-head">
        <span class="bq-idx" aria-hidden="true">05</span>
        <h2 id="bq-gal-title" class="bq-h2">Galería</h2>
      </header>
      <div class="bq-gallery">
        <button
          v-for="(img, i) in gallery" :key="img.id" v-reveal="(i % 4) * 60"
          type="button" class="bq-gallery-item"
          :aria-label="`Ver imagen ${i + 1} en grande`"
          @click="openLightbox(i)"
        >
          <img :src="img.url" :alt="`Imagen ${i + 1} de la galería de ${shopName}`" loading="lazy" />
        </button>
      </div>
    </div>
  </section>

  <!-- ===== Preguntas frecuentes ===== -->
  <section v-if="showFaqs" class="bq-sec" aria-labelledby="bq-faq-title">
    <div class="sp-container bq-faq-grid">
      <header v-reveal class="bq-sec-head col">
        <span class="bq-idx" aria-hidden="true">06</span>
        <h2 id="bq-faq-title" class="bq-h2">{{ faqsTitle }}</h2>
      </header>
      <div class="bq-faqs">
        <details v-for="(f, i) in faqs" :key="i" v-reveal="(i % 4) * 50" class="bq-faq">
          <summary>{{ f.q }}<AppIcon name="plus" :size="15" aria-hidden="true" /></summary>
          <p>{{ f.a }}</p>
        </details>
      </div>
    </div>
  </section>

  <!-- ===== Video: embed enmarcado con las mismas reglas duras ===== -->
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

  <!-- ===== CTA: bloque de tinta a todo lo ancho ===== -->
  <section v-if="showCta" class="bq-cta">
    <div class="sp-container bq-cta-inner">
      <h2 v-reveal class="bq-cta-title">{{ ctaTitle }}</h2>
      <p v-if="custom.cta_text" v-reveal="80" class="bq-cta-text">{{ custom.cta_text }}</p>
      <component
        v-if="ctaLink" :is="ctaLink.to ? 'RouterLink' : 'a'" v-reveal="140" class="bq-btn invert"
        :to="ctaLink.to" :href="ctaLink.href"
        :target="ctaLink.external ? '_blank' : null" :rel="ctaLink.external ? 'noopener' : null"
      >
        {{ ctaLabel }} <AppIcon name="arrow-right" :size="15" />
      </component>
    </div>
  </section>

  <!-- ===== Contacto: canales e info en celdas + formulario compartido ===== -->
  <section v-if="showContact" id="contacto" class="bq-sec bq-contact" aria-labelledby="bq-contact-title">
    <div class="sp-container bq-contact-grid">
      <div class="bq-contact-info">
        <header v-reveal class="bq-sec-head col">
          <span class="bq-idx" aria-hidden="true">07</span>
          <h2 id="bq-contact-title" class="bq-h2">Contacto</h2>
        </header>
        <p v-if="mapAddress" class="bq-contact-line"><AppIcon name="map-pin" :size="14" /> {{ mapAddress }}</p>
        <ul v-if="showHours" class="bq-contact-hours">
          <li v-for="(h, i) in contactHours" :key="i"><span>{{ h.label }}</span><strong>{{ h.value }}</strong></li>
        </ul>
        <div class="bq-contact-channels">
          <a v-if="whatsappUrl" class="bq-btn" :href="whatsappUrl" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="15" /> WhatsApp</a>
          <a v-for="s in socials" :key="s.key" class="bq-btn ghost sm" :href="s.url" target="_blank" rel="noopener">{{ s.label }}</a>
        </div>
      </div>
      <form v-reveal="120" class="sp-form bq-form" novalidate @submit.prevent="submitContact">
        <div v-if="contactStatus === 'success'" class="sp-sent" role="status">
          <span class="sp-sent-check" aria-hidden="true"><AppIcon name="check" :size="30" :stroke="2.25" /></span>
          <strong>Mensaje enviado</strong>
          <p>Gracias por escribirnos. Te respondemos a la brevedad al email que dejaste.</p>
          <button type="button" class="bq-btn ghost sm" @click="contactStatus = 'idle'">Enviar otro mensaje</button>
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
              <label for="bq-contact-name">Tu nombre</label>
              <input id="bq-contact-name" v-model="contactForm.name" class="sp-input" type="text" maxlength="80" autocomplete="name" placeholder="Cómo te llamás" required />
            </div>
            <div class="sp-field">
              <label for="bq-contact-email">Tu email</label>
              <input id="bq-contact-email" v-model="contactForm.email" class="sp-input" type="email" autocomplete="email" placeholder="nombre@correo.com" required />
            </div>
          </div>
          <div class="sp-field">
            <label for="bq-contact-message">Mensaje</label>
            <textarea id="bq-contact-message" v-model="contactForm.message" class="sp-input sp-textarea" rows="4" maxlength="2000" placeholder="Contanos en qué te podemos ayudar" required></textarea>
          </div>
          <div class="sp-field">
            <label for="bq-contact-captcha">Verificación rápida</label>
            <div class="sp-captcha-row">
              <span class="sp-captcha-q"><AppIcon name="shield-check" :size="16" aria-hidden="true" /> {{ captcha?.question || 'Cargando…' }}</span>
              <input id="bq-contact-captcha" v-model="contactForm.captcha_answer" class="sp-input" type="text" inputmode="numeric" autocomplete="off" placeholder="Respuesta" required />
              <button type="button" class="sp-icon-btn" :disabled="captchaLoading" aria-label="Nueva pregunta de verificación" title="Nueva pregunta" @click="loadCaptcha">
                <AppIcon name="refresh" :size="15" />
              </button>
            </div>
          </div>
          <div class="sp-hp" aria-hidden="true">
            <label for="bq-contact-website">Website</label>
            <input id="bq-contact-website" v-model="contactForm.website" type="text" tabindex="-1" autocomplete="off" />
          </div>
          <p v-if="contactError" class="sp-form-error" role="alert">{{ contactError }}</p>
          <div class="sp-form-foot">
            <button type="submit" class="bq-btn" :disabled="contactStatus === 'loading' || !captcha">
              <span v-if="contactStatus === 'loading'" class="spinner" aria-hidden="true"></span>
              Enviar mensaje
            </button>
          </div>
        </template>
      </form>
    </div>
    <div v-if="mapUrl" class="sp-container bq-map-wrap">
      <figure v-reveal="120" class="bq-map">
        <iframe :src="mapUrl" title="Mapa con la ubicación del negocio" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe>
        <figcaption><a :href="mapLink" target="_blank" rel="noopener">Abrir en Google Maps <AppIcon name="arrow-up-right" :size="13" /></a></figcaption>
      </figure>
    </div>
  </section>

  <!-- ===== Palabra de cierre: la marca a todo lo ancho ===== -->
  <div class="bq-word" aria-hidden="true"><span :style="nameFont">{{ shopName }}</span></div>

  <!-- ===== Galería: visor (mismo modal que el resto de diseños) ===== -->
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
