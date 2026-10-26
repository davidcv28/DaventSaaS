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
import '../assets/store-riso.css'

// Diseño "Riso": landing en risografía — papel crema con trama de puntos,
// tintas planas (rosa/azul/amarillo/menta) que se solapan con multiply,
// sombras desplazadas, botones píldora y motion con resorte. El azul toma
// el acento de la tienda. Es la portada real cuando la tienda elige 'riso'.
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

// --- Hero: titular XXL a tres tintas (primera palabra rosa, última azul).
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value)
const heroWords = computed(() => {
  const words = heroTitle.value.split(/\s+/).filter(Boolean)
  return words.map((w, i) => ({ w, tone: i === 0 ? 'pink' : i === words.length - 1 ? 'blue' : 'ink' }))
})
const heroLong = computed(() => heroWords.value.length > 3 || heroTitle.value.length > 22)

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

// Catálogo: vitrina de recientes en grilla con chips de categoría locales.
const catalog = ref({ categories: [], brands: [], products: [] })
const activeCat = ref(null)
const chipCats = computed(() => catalog.value.categories.filter((c) => catalog.value.products.some((p) => p.category === c.id)).slice(0, 6))
const gridProducts = computed(() => catalog.value.products.filter((p) => activeCat.value == null || p.category === activeCat.value).slice(0, 8))
const PLATE_TONES = ['pink', 'blue', 'yellow', 'mint']
const toneOf = (p) => PLATE_TONES[Math.max(0, catalog.value.categories.findIndex((c) => c.id === p.category)) % PLATE_TONES.length]
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
// Cinta de anuncios (avisos del dueño bajo el hero) y sección Video: la URL
// llega ya normalizada al embed oficial desde el serializer.
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
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
<div class="sp-page-root rs">
  <!-- ===== Hero: kicker, titular XXL a tres tintas, pie con sticker y acciones ===== -->
  <section class="rs-hero">
    <div class="sp-container">
      <div class="rs-hero-top">
        <span class="rs-kicker">{{ shopName }} · {{ new Date().getFullYear() }}</span>
        <span v-if="location" class="rs-note">{{ location }}</span>
      </div>
      <h1 class="rs-h1" :class="{ long: heroLong }">
        <span v-for="(x, i) in heroWords" :key="i" class="rs-w" :class="x.tone" :style="{ animationDelay: `${i * 120}ms` }">{{ x.w }}</span>
      </h1>
      <div class="rs-hero-foot">
        <p class="rs-hero-desc">{{ custom.description || `Bienvenido a ${shopName}.` }}</p>
        <div class="rs-sticker" aria-hidden="true"><span>{{ heroStatus.text }}</span></div>
        <div class="rs-hero-cta">
          <RouterLink v-if="showCatalog" class="rs-btn" :to="catalogTo">Ver catálogo <span class="rs-arr" aria-hidden="true">→</span></RouterLink>
          <RouterLink v-else-if="servicesPage" class="rs-btn" :to="servicesTo">Ver servicios <span class="rs-arr" aria-hidden="true">→</span></RouterLink>
          <RouterLink v-if="servicesPage && showCatalog" class="rs-btn card" :to="servicesTo">Servicios <span class="rs-arr" aria-hidden="true">→</span></RouterLink>
          <a v-if="showContact" class="rs-btn card" href="#contacto">Contacto</a>
          <RouterLink v-else-if="hasAbout" class="rs-btn card" :to="{ path: homeTo.path, hash: '#nosotros' }">Nosotros</RouterLink>
        </div>
      </div>
    </div>
  </section>

  <!-- ===== Cinta rosa inclinada con datos reales en loop ===== -->
  <div class="rs-band" aria-hidden="true">
    <div class="rs-band-track">
      <span v-for="(t, i) in tickerItems" :key="`a-${i}`">{{ t }}</span>
      <span v-for="(t, i) in tickerItems" :key="`b-${i}`">{{ t }}</span>
    </div>
  </div>

  <!-- ===== Cinta de anuncios: avisos del dueño en banda propia ===== -->
  <div v-if="showAnn" class="sp-ann" role="note" aria-label="Anuncios de la tienda">
    <div class="sp-ann-track">
      <span v-for="(a, i) in annLoop" :key="i" class="sp-ann-item" :aria-hidden="i >= announcements.length"><AppIcon :name="serviceIcon(a.icon)" :size="14" />{{ a.text }}</span>
    </div>
  </div>

  <!-- ===== Cifras: tarjetas de tinta plana ===== -->
  <section v-if="showStats" class="rs-sec rs-stats-sec" aria-label="Cifras del negocio">
    <div class="sp-container rs-stats">
      <div v-for="(s, i) in stats" :key="i" v-reveal="i * 60" class="rs-stat" :class="`t${i % 4}`">
        <strong>{{ s.value }}</strong>
        <span>{{ s.label }}</span>
      </div>
    </div>
  </section>

  <!-- ===== Catálogo: chips de categoría + grilla de tarjetas con placa de color ===== -->
  <section v-if="catalog.products.length" id="catalogo" class="rs-sec" aria-labelledby="rs-prod-title">
    <div class="sp-container">
      <header v-reveal class="rs-sec-head">
        <h2 id="rs-prod-title" class="rs-h2">Catálogo <em>destacado</em></h2>
        <div class="rs-chips" role="group" aria-label="Filtrar productos">
          <button type="button" class="rs-chip" :aria-pressed="activeCat == null" @click="activeCat = null">Todo</button>
          <button v-for="c in chipCats" :key="c.id" type="button" class="rs-chip" :aria-pressed="activeCat === c.id" @click="activeCat = c.id">{{ c.name }}</button>
        </div>
      </header>
      <div class="rs-cards">
        <article
          v-for="(p, i) in gridProducts" :key="p.id" v-reveal="(i % 4) * 60"
          class="rs-card" :class="`t-${toneOf(p)}`" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
          @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
        >
          <figure class="rs-plate">
            <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
            <span v-else class="rs-plate-ph"><AppIcon name="package" :size="44" /></span>
            <span class="rs-idx">{{ String(i + 1).padStart(3, '0') }}</span>
            <span v-if="productOffer(p) != null" class="rs-badge">−{{ offerPct(p) }}%</span>
            <span v-else-if="isNewProduct(p)" class="rs-badge">Nuevo</span>
          </figure>
          <div class="rs-info">
            <div class="rs-info-row">
              <h3>{{ p.name }}</h3>
              <span class="rs-price">
                <s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>
                {{ formatARS(effectivePrice(p)) }}
              </span>
            </div>
            <p v-if="catOf(p) || brandOf(p)">{{ [catOf(p), brandOf(p)].filter(Boolean).join(' · ') }}</p>
          </div>
          <span class="rs-add" aria-hidden="true">Ver producto</span>
        </article>
      </div>
      <p v-if="!gridProducts.length" class="rs-empty">No hay productos en esta categoría todavía.</p>
      <RouterLink class="rs-btn card rs-more" :to="catalogTo">Ver todo el catálogo <span class="rs-arr" aria-hidden="true">→</span></RouterLink>
    </div>
  </section>

  <!-- ===== Nosotros: tarjeta de título + copy ===== -->
  <section v-if="hasAbout" id="nosotros" class="rs-sec" aria-labelledby="rs-about-title">
    <div class="sp-container rs-process">
      <header v-reveal class="rs-process-head">
        <span class="rs-kicker">Nosotros</span>
        <h2 id="rs-about-title" class="rs-h2 big">{{ aboutTitle }}<em>.</em></h2>
      </header>
      <div class="rs-process-copy">
        <p v-if="custom.about_text" v-reveal="80" class="rs-lead">{{ custom.about_text }}</p>
        <blockquote v-if="hasMission" v-reveal="140" class="rs-mission">
          <span class="rs-kicker sm">Misión</span>
          {{ custom.about_mission }}
        </blockquote>
        <ul v-if="aboutSpecialties.length" v-reveal="180" class="rs-tags">
          <li v-for="(s, i) in aboutSpecialties" :key="s" :class="`t${i % 4}`">{{ s }}</li>
        </ul>
        <p v-if="custom.about_years" v-reveal="220" class="rs-years"><strong>+{{ custom.about_years }}</strong> años de trayectoria</p>
      </div>
    </div>
  </section>

  <!-- ===== Qué ofrecemos: tarjetas con ícono en disco de color ===== -->
  <section v-if="showServices" class="rs-sec" aria-labelledby="rs-serv-title">
    <div class="sp-container">
      <header v-reveal class="rs-sec-head">
        <h2 id="rs-serv-title" class="rs-h2">{{ servicesTitle }}</h2>
      </header>
      <ul class="rs-services">
        <li v-for="(s, i) in services" :key="i" v-reveal="(i % 3) * 60" class="rs-service">
          <span class="rs-service-icon" :class="`t${i % 4}`" aria-hidden="true"><AppIcon :name="serviceIcon(s.icon)" :size="22" /></span>
          <strong>{{ s.title }}</strong>
          <p v-if="s.text">{{ s.text }}</p>
        </li>
      </ul>
      <div v-if="servicesPage" class="rs-more">
        <RouterLink class="rs-btn" :to="servicesTo">Ver precios y pedir por WhatsApp <span class="rs-arr" aria-hidden="true">→</span></RouterLink>
      </div>
    </div>
  </section>

  <!-- ===== Testimonios ===== -->
  <section v-if="showTestimonials" class="rs-sec" aria-labelledby="rs-test-title">
    <div class="sp-container">
      <header v-reveal class="rs-sec-head">
        <h2 id="rs-test-title" class="rs-h2">{{ testimonialsTitle }}</h2>
      </header>
      <div class="rs-quotes">
        <figure v-for="(t, i) in testimonials" :key="i" v-reveal="(i % 3) * 70" class="rs-quote" :class="`t${i % 4}`">
          <blockquote>{{ t.text }}</blockquote>
          <figcaption>
            <strong>{{ t.name }}</strong>
            <span v-if="t.detail">{{ t.detail }}</span>
          </figcaption>
        </figure>
      </div>
    </div>
  </section>

  <!-- ===== Galería ===== -->
  <section v-if="showGallery" id="galeria" class="rs-sec" aria-labelledby="rs-gal-title">
    <div class="sp-container">
      <header v-reveal class="rs-sec-head">
        <h2 id="rs-gal-title" class="rs-h2">Galería</h2>
      </header>
      <div class="rs-gallery">
        <button
          v-for="(img, i) in gallery" :key="img.id" v-reveal="(i % 4) * 60"
          type="button" class="rs-gallery-item"
          :aria-label="`Ver imagen ${i + 1} en grande`"
          @click="openLightbox(i)"
        >
          <img :src="img.url" :alt="`Imagen ${i + 1} de la galería de ${shopName}`" loading="lazy" />
        </button>
      </div>
    </div>
  </section>

  <!-- ===== Preguntas frecuentes ===== -->
  <section v-if="showFaqs" class="rs-sec" aria-labelledby="rs-faq-title">
    <div class="sp-container rs-faq-grid">
      <header v-reveal class="rs-sec-head col">
        <h2 id="rs-faq-title" class="rs-h2">{{ faqsTitle }}</h2>
      </header>
      <div class="rs-faqs">
        <details v-for="(f, i) in faqs" :key="i" v-reveal="(i % 4) * 50" class="rs-faq">
          <summary>{{ f.q }}<AppIcon name="plus" :size="16" aria-hidden="true" /></summary>
          <p>{{ f.a }}</p>
        </details>
      </div>
    </div>
  </section>

  <!-- ===== CTA: bloque azul con sombra desplazada ===== -->
  <!-- ===== Video: embed en placas de tinta plana ===== -->
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

  <section v-if="showCta" class="rs-sec">
    <div class="sp-container">
      <div class="rs-shop">
        <div>
          <h2 v-reveal class="rs-cta-title">{{ ctaTitle }}<span>.</span></h2>
          <p v-if="custom.cta_text" v-reveal="80" class="rs-cta-text">{{ custom.cta_text }}</p>
        </div>
        <component
          v-if="ctaLink" :is="ctaLink.to ? 'RouterLink' : 'a'" v-reveal="140" class="rs-btn pink"
          :to="ctaLink.to" :href="ctaLink.href"
          :target="ctaLink.external ? '_blank' : null" :rel="ctaLink.external ? 'noopener' : null"
        >
          {{ ctaLabel }} <span class="rs-arr" aria-hidden="true">→</span>
        </component>
      </div>
    </div>
  </section>

  <!-- ===== Contacto ===== -->
  <section v-if="showContact" id="contacto" class="rs-sec rs-contact" aria-labelledby="rs-contact-title">
    <div class="sp-container rs-contact-grid">
      <div class="rs-contact-info">
        <header v-reveal class="rs-sec-head col">
          <h2 id="rs-contact-title" class="rs-h2">Contacto</h2>
        </header>
        <p v-if="mapAddress" class="rs-contact-line"><AppIcon name="map-pin" :size="15" /> {{ mapAddress }}</p>
        <ul v-if="showHours" class="rs-hours">
          <li v-for="(h, i) in contactHours" :key="i"><span>{{ h.label }}</span><strong>{{ h.value }}</strong></li>
        </ul>
        <div class="rs-contact-channels">
          <a v-if="whatsappUrl" class="rs-btn" :href="whatsappUrl" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" /> WhatsApp</a>
          <a v-for="s in socials" :key="s.key" class="rs-btn card sm" :href="s.url" target="_blank" rel="noopener">{{ s.label }}</a>
        </div>
      </div>
      <form v-reveal="120" class="sp-form rs-form" novalidate @submit.prevent="submitContact">
        <div v-if="contactStatus === 'success'" class="sp-sent" role="status">
          <span class="sp-sent-check" aria-hidden="true"><AppIcon name="check" :size="30" :stroke="2.25" /></span>
          <strong>Mensaje enviado</strong>
          <p>Gracias por escribirnos. Te respondemos a la brevedad al email que dejaste.</p>
          <button type="button" class="rs-btn card sm" @click="contactStatus = 'idle'">Enviar otro mensaje</button>
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
              <label for="rs-contact-name">Tu nombre</label>
              <input id="rs-contact-name" v-model="contactForm.name" class="sp-input" type="text" maxlength="80" autocomplete="name" placeholder="Cómo te llamás" required />
            </div>
            <div class="sp-field">
              <label for="rs-contact-email">Tu email</label>
              <input id="rs-contact-email" v-model="contactForm.email" class="sp-input" type="email" autocomplete="email" placeholder="nombre@correo.com" required />
            </div>
          </div>
          <div class="sp-field">
            <label for="rs-contact-message">Mensaje</label>
            <textarea id="rs-contact-message" v-model="contactForm.message" class="sp-input sp-textarea" rows="4" maxlength="2000" placeholder="Contanos en qué te podemos ayudar" required></textarea>
          </div>
          <div class="sp-field">
            <label for="rs-contact-captcha">Verificación rápida</label>
            <div class="sp-captcha-row">
              <span class="sp-captcha-q"><AppIcon name="shield-check" :size="16" aria-hidden="true" /> {{ captcha?.question || 'Cargando…' }}</span>
              <input id="rs-contact-captcha" v-model="contactForm.captcha_answer" class="sp-input" type="text" inputmode="numeric" autocomplete="off" placeholder="Respuesta" required />
              <button type="button" class="sp-icon-btn" :disabled="captchaLoading" aria-label="Nueva pregunta de verificación" title="Nueva pregunta" @click="loadCaptcha">
                <AppIcon name="refresh" :size="15" />
              </button>
            </div>
          </div>
          <div class="sp-hp" aria-hidden="true">
            <label for="rs-contact-website">Website</label>
            <input id="rs-contact-website" v-model="contactForm.website" type="text" tabindex="-1" autocomplete="off" />
          </div>
          <p v-if="contactError" class="sp-form-error" role="alert">{{ contactError }}</p>
          <div class="sp-form-foot">
            <button type="submit" class="rs-btn" :disabled="contactStatus === 'loading' || !captcha">
              <span v-if="contactStatus === 'loading'" class="spinner" aria-hidden="true"></span>
              Enviar mensaje
            </button>
          </div>
        </template>
      </form>
    </div>
    <div v-if="mapUrl" class="sp-container rs-map-wrap">
      <figure v-reveal="120" class="rs-map">
        <iframe :src="mapUrl" title="Mapa con la ubicación del negocio" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe>
        <figcaption><a :href="mapLink" target="_blank" rel="noopener">Abrir en Google Maps <AppIcon name="arrow-up-right" :size="13" /></a></figcaption>
      </figure>
    </div>
  </section>

  <!-- ===== Palabra de cierre: la marca a todo lo ancho en rosa multiply ===== -->
  <div class="rs-word" aria-hidden="true"><span :style="nameFont">{{ shopName }}</span></div>

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
