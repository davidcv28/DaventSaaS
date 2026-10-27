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
import '../assets/store-terra.css'
import TplProductCard from '../components/store/TplProductCard.vue'

// Diseño "Terra": editorial cálido y artesanal. Papel crudo, titulares
// Fraunces, imágenes en arco, reglas finas y el acento de la marca como
// sello. La portada, el catálogo y la página de servicios comparten la
// misma identidad (store-terra.css + store-services.css).
const ctx = inject('storePage')
const { slug, custom, shopName, nameFont, initial, location, hasAbout, showContact, showCatalog, hasDesignAdvanced, loadPublicCatalog } = ctx

const router = useRouter()
const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${slug.value}` }))
const catalogTo = computed(() => ({ path: storeHostSlug ? '/catalogo' : `/${slug.value}/catalogo` }))
const servicesPage = ctx.showServices
const servicesTo = computed(() => ({ path: storeHostSlug ? '/servicios' : `/${slug.value}/servicios` }))
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })
const openProduct = (p) => router.push(productTo(p))

const listOf = (value) => (Array.isArray(value) ? value : [])

// --- Hero: titular serif, bajada, acciones y una imagen en arco con una
// ficha flotante (cifra destacada o estado del negocio).
const heroTitleIsName = computed(() => !custom.value.headline?.trim())
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value)

const gallery = computed(() => custom.value.gallery || [])
const decor = computed(() => custom.value.decor || [])
const heroImage = computed(() => {
  if (hasDesignAdvanced.value && custom.value.cover) return custom.value.cover
  return gallery.value[0]?.url || decor.value[0]?.url || ''
})
const aboutImage = computed(() => gallery.value[1]?.url || decor.value[0]?.url || gallery.value[0]?.url || '')

const now = ref(new Date())
let clock = null
const openNow = computed(() => (custom.value.show_hours !== false ? openStatus(custom.value.hours, now.value) : null))
const heroStatus = computed(() => {
  if (openNow.value) return { live: openNow.value.state === 'open', text: openNow.value.text }
  return { live: showCatalog.value, text: showCatalog.value ? 'Catálogo online' : 'Sitio oficial' }
})

const stats = computed(() => listOf(custom.value.stats))
const showStats = computed(() => custom.value.show_stats !== false && stats.value.length > 0)
const heroCard = computed(() => {
  const s = stats.value[0]
  if (s) return { value: s.value, label: s.label }
  if (custom.value.about_years) return { value: `+${custom.value.about_years}`, label: 'años de trayectoria' }
  return { value: showCatalog.value ? 'En línea' : 'A tu lado', label: showCatalog.value ? 'Catálogo abierto' : 'Atención personal' }
})

// --- Cinta de valores: nombre + especialidades + ubicación (datos reales).
const aboutSpecialties = computed(() => String(custom.value.about_specialties || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean)
  .slice(0, 6))
const bandItems = computed(() => {
  const items = [shopName.value]
  aboutSpecialties.value.forEach((s) => items.push(s))
  if (location.value) items.push(location.value)
  if (custom.value.about_years) items.push(`+${custom.value.about_years} años`)
  return items.slice(0, 6)
})

// --- Anuncios y video (bloques compartidos con el resto de diseños).
const announcements = computed(() => listOf(custom.value.announcements))
const showAnn = computed(() => custom.value.show_announcements !== false && announcements.value.length > 0)
const annLoop = computed(() => [...announcements.value, ...announcements.value, ...announcements.value])
const videoEmbed = computed(() => (custom.value.video_url || '').trim())
const showVideo = computed(() => custom.value.show_video !== false && Boolean(videoEmbed.value))
const videoTitle = computed(() => custom.value.video_title?.trim() || 'Mirá nuestro video')

// --- Catálogo: selección de recientes.
const catalog = ref({ categories: [], brands: [], products: [] })
// Landing = empresa + ofertas: la sección solo muestra productos en oferta.
const gridProducts = computed(() => catalog.value.products.filter((p) => productOffer(p) != null).slice(0, 4))
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

// --- Nosotros.
const aboutTitle = computed(() => custom.value.about_title?.trim() || 'Nuestra historia')
const hasMission = computed(() => Boolean(custom.value.about_mission?.trim()))

// --- Qué ofrecemos.
const services = computed(() => listOf(custom.value.services))
const showServices = computed(() => custom.value.show_services !== false && services.value.length > 0)
const servicesTitle = computed(() => custom.value.services_title?.trim() || 'Qué hacemos')
const serviceIcon = (key) => (SERVICE_ICONS[key] ? key : 'package')

// --- Testimonios.
const testimonials = computed(() => listOf(custom.value.testimonials))
const showTestimonials = computed(() => custom.value.show_testimonials !== false && testimonials.value.length > 0)
const testimonialsTitle = computed(() => custom.value.testimonials_title?.trim() || 'Lo que dicen nuestros clientes')

// --- Galería y visor.
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

// --- Preguntas frecuentes.
const faqs = computed(() => listOf(custom.value.faqs))
const showFaqs = computed(() => custom.value.show_faq !== false && faqs.value.length > 0)
const faqsTitle = computed(() => custom.value.faqs_title?.trim() || 'Preguntas frecuentes')

// --- Cierre.
const whatsappUrl = computed(() => (custom.value.whatsapp ? `https://wa.me/${custom.value.whatsapp.replace(/\D/g, '')}` : ''))
const showCta = computed(() => custom.value.show_cta !== false
  && Boolean(custom.value.cta_title?.trim() || custom.value.cta_text?.trim() || whatsappUrl.value || showCatalog.value))
const ctaTitle = computed(() => custom.value.cta_title?.trim() || `Hablemos de tu próximo proyecto`)
const ctaLink = computed(() => {
  if (whatsappUrl.value) return { href: whatsappUrl.value, external: true }
  if (showContact.value) return { href: '#contacto', external: false }
  if (showCatalog.value) return { to: catalogTo.value, external: false }
  if (servicesPage.value) return { to: servicesTo.value, external: false }
  return null
})
const ctaLabel = computed(() => custom.value.cta_label?.trim()
  || (ctaLink.value?.external ? 'Escribinos por WhatsApp' : ctaLink.value?.href === '#contacto' ? 'Contáctanos' : ctaLink.value?.to === servicesTo.value ? 'Ver servicios' : 'Ver catálogo'))

// --- Contacto.
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
  window.addEventListener('keydown', onKey)
  clock = setInterval(() => { now.value = new Date() }, 60000)
})

onBeforeUnmount(() => {
  clearInterval(clock)
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
<div class="sp-page-root tr">
  <!-- ===== Portada: titular serif, bajada y arco con ficha flotante ===== -->
  <section class="tr-hero">
    <div class="sp-container tr-hero-grid">
      <div class="tr-hero-copy">
        <p class="tr-eyebrow"><span class="tr-rule" aria-hidden="true"></span>{{ location || 'Hecho con dedicación' }}</p>
        <h1 v-reveal class="tr-h1" :class="{ 'is-name': heroTitleIsName }">{{ heroTitle }}</h1>
        <p v-if="custom.description" v-reveal="60" class="tr-lead">{{ custom.description }}</p>
        <div v-reveal="120" class="tr-actions">
          <RouterLink v-if="showCatalog" class="tr-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="15" /></RouterLink>
          <RouterLink v-else-if="servicesPage" class="tr-btn" :to="servicesTo">Ver servicios <AppIcon name="arrow-right" :size="15" /></RouterLink>
          <RouterLink v-if="servicesPage && showCatalog" class="tr-btn ghost" :to="servicesTo">Servicios</RouterLink>
          <a v-if="whatsappUrl" class="tr-btn ghost" :href="whatsappUrl" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="15" /> Escribinos</a>
          <a v-else-if="showContact" class="tr-btn ghost" href="#contacto">Contacto</a>
        </div>
        <ul v-reveal="160" class="tr-trust">
          <li><span class="tr-dot" :class="{ live: heroStatus.live }" aria-hidden="true"></span>{{ heroStatus.text }}</li>
          <li v-if="showServices"><AppIcon name="checklist" :size="15" /> {{ services.length }} {{ services.length === 1 ? 'servicio' : 'servicios' }}</li>
          <li v-if="showCatalog"><AppIcon name="package" :size="15" /> Catálogo con precios</li>
        </ul>
      </div>

      <figure v-reveal="80" class="tr-hero-media">
        <div class="tr-arch">
          <img v-if="heroImage" :src="heroImage" :alt="`Imagen de ${shopName}`" loading="eager" />
          <span v-else class="tr-arch-empty" aria-hidden="true">
            <em>{{ initial }}</em>
            <small>{{ shopName }}</small>
          </span>
        </div>
        <span class="tr-seal" aria-hidden="true"><AppIcon name="sparkles" :size="13" /> {{ initial }}</span>
        <figcaption class="tr-hero-card">
          <span>{{ heroCard.label }}</span>
          <strong>{{ heroCard.value }}</strong>
        </figcaption>
      </figure>
    </div>
  </section>

  <!-- ===== Cinta de valores ===== -->
  <div class="tr-band" aria-hidden="true">
    <div class="sp-container tr-band-inner">
      <span v-for="(t, i) in bandItems" :key="i" class="tr-band-item">{{ t }}<i>✦</i></span>
    </div>
  </div>

  <!-- ===== Anuncios ===== -->
  <div v-if="showAnn" class="sp-ann" role="note" aria-label="Anuncios de la tienda">
    <div class="sp-ann-track">
      <span v-for="(a, i) in annLoop" :key="i" class="sp-ann-item" :aria-hidden="i >= announcements.length"><AppIcon :name="serviceIcon(a.icon)" :size="14" />{{ a.text }}</span>
    </div>
  </div>

  <!-- ===== Cifras ===== -->
  <section v-if="showStats" class="tr-stats" aria-label="Cifras del negocio">
    <div class="sp-container tr-stats-row">
      <div v-for="(s, i) in stats" :key="i" v-reveal="i * 60" class="tr-stat">
        <strong>{{ s.value }}</strong>
        <span>{{ s.label }}</span>
      </div>
    </div>
  </section>

  <!-- ===== Catálogo: selección en arcos ===== -->
  <section v-if="gridProducts.length" id="catalogo" class="tr-sec" aria-labelledby="tr-prod-title">
    <div class="sp-container">
      <header v-reveal class="tr-sec-head">
        <div>
          <p class="tr-eyebrow"><span class="tr-rule" aria-hidden="true"></span>Selección</p>
          <h2 id="tr-prod-title" class="tr-h2">Ofertas de la tienda</h2>
        </div>
        <RouterLink class="tr-link" :to="catalogTo">Ver todo el catálogo <AppIcon name="arrow-right" :size="14" /></RouterLink>
      </header>
      <div class="tr-grid">
        <TplProductCard
          v-for="(p, i) in gridProducts" :key="p.id" v-reveal="(i % 4) * 70"
          tag="figure" class="tr-card" :p="p"
          :cat="catOf(p)" :brand="brandOf(p)"
          seal-shape="" offer-new :ph-size="26" :go="false"
          @open="openProduct" />
      </div>
    </div>
  </section>

  <!-- ===== Nosotros ===== -->
  <section v-if="hasAbout" id="nosotros" class="tr-sec tr-about" aria-labelledby="tr-about-title">
    <div class="sp-container tr-about-grid">
      <figure v-reveal class="tr-about-media">
        <div class="tr-arch">
          <img v-if="aboutImage" :src="aboutImage" :alt="`Sobre ${shopName}`" loading="lazy" />
          <span v-else class="tr-arch-empty" aria-hidden="true"><em>{{ initial }}</em><small>{{ shopName }}</small></span>
        </div>
        <figcaption v-if="custom.about_years" class="tr-about-badge">
          <strong>+{{ custom.about_years }}</strong>
          <span>años de trayectoria</span>
        </figcaption>
      </figure>
      <div class="tr-about-copy">
        <p class="tr-eyebrow"><span class="tr-rule" aria-hidden="true"></span>Nosotros</p>
        <h2 id="tr-about-title" class="tr-h2">{{ aboutTitle }}</h2>
        <p v-if="custom.about_text" v-reveal="80" class="tr-about-text">{{ custom.about_text }}</p>
        <blockquote v-if="hasMission" v-reveal="140" class="tr-mission">
          <span>Nuestra misión</span>
          {{ custom.about_mission }}
        </blockquote>
        <ul v-if="aboutSpecialties.length" v-reveal="180" class="tr-chips">
          <li v-for="s in aboutSpecialties" :key="s">{{ s }}</li>
        </ul>
      </div>
    </div>
  </section>

  <!-- ===== Servicios ===== -->
  <section v-if="showServices" class="tr-sec" aria-labelledby="tr-serv-title">
    <div class="sp-container">
      <header v-reveal class="tr-sec-head">
        <div>
          <p class="tr-eyebrow"><span class="tr-rule" aria-hidden="true"></span>Servicios</p>
          <h2 id="tr-serv-title" class="tr-h2">{{ servicesTitle }}</h2>
        </div>
        <RouterLink v-if="servicesPage" class="tr-link" :to="servicesTo">Ver precios y pedir <AppIcon name="arrow-right" :size="14" /></RouterLink>
      </header>
      <div class="tr-services">
        <article v-for="(s, i) in services" :key="i" v-reveal="(i % 3) * 70" class="tr-service">
          <span class="tr-service-ico" aria-hidden="true"><AppIcon :name="serviceIcon(s.icon)" :size="22" /></span>
          <span class="tr-service-n" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
          <h3>{{ s.title }}</h3>
          <p v-if="s.text">{{ s.text }}</p>
        </article>
      </div>
    </div>
  </section>

  <!-- ===== Testimonios ===== -->
  <section v-if="showTestimonials" class="tr-sec tr-quotes" aria-labelledby="tr-test-title">
    <div class="sp-container">
      <header v-reveal class="tr-sec-head">
        <div>
          <p class="tr-eyebrow"><span class="tr-rule" aria-hidden="true"></span>Confianza</p>
          <h2 id="tr-test-title" class="tr-h2">{{ testimonialsTitle }}</h2>
        </div>
      </header>
      <div class="tr-quote-grid">
        <figure v-for="(t, i) in testimonials" :key="i" v-reveal="(i % 3) * 80" class="tr-quote">
          <span class="tr-quote-mark" aria-hidden="true">“</span>
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
  <section v-if="showGallery" id="galeria" class="tr-sec" aria-labelledby="tr-gal-title">
    <div class="sp-container">
      <header v-reveal class="tr-sec-head">
        <div>
          <p class="tr-eyebrow"><span class="tr-rule" aria-hidden="true"></span>Galería</p>
          <h2 id="tr-gal-title" class="tr-h2">Un vistazo al día a día</h2>
        </div>
      </header>
      <div class="tr-gallery">
        <button
          v-for="(img, i) in gallery" :key="img.id" v-reveal="(i % 4) * 60"
          type="button" class="tr-gallery-item"
          :aria-label="`Ver imagen ${i + 1} en grande`"
          @click="openLightbox(i)"
        >
          <img :src="img.url" :alt="`Imagen ${i + 1} de la galería de ${shopName}`" loading="lazy" />
        </button>
      </div>
    </div>
  </section>

  <!-- ===== Preguntas frecuentes ===== -->
  <section v-if="showFaqs" class="tr-sec tr-faq" aria-labelledby="tr-faq-title">
    <div class="sp-container tr-faq-grid">
      <div>
        <p class="tr-eyebrow"><span class="tr-rule" aria-hidden="true"></span>Dudas</p>
        <h2 id="tr-faq-title" class="tr-h2">{{ faqsTitle }}</h2>
      </div>
      <div class="tr-faqs">
        <details v-for="(f, i) in faqs" :key="i" v-reveal="(i % 4) * 50" class="tr-faq-item">
          <summary>{{ f.q }}<AppIcon name="plus" :size="16" aria-hidden="true" /></summary>
          <p>{{ f.a }}</p>
        </details>
      </div>
    </div>
  </section>

  <!-- ===== Video ===== -->
  <section v-if="showVideo" class="sp-video tr-video" aria-labelledby="tr-video-title">
    <div class="sp-container">
      <header v-reveal class="sp-video-head">
        <h2 id="tr-video-title" class="sp-video-title">{{ videoTitle }}</h2>
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

  <!-- ===== Cierre ===== -->
  <section v-if="showCta" class="tr-cta">
    <div class="sp-container tr-cta-inner">
      <div>
        <p class="tr-eyebrow light"><span class="tr-rule" aria-hidden="true"></span>Hablemos</p>
        <h2 v-reveal class="tr-cta-title">{{ ctaTitle }}</h2>
        <p v-if="custom.cta_text" v-reveal="70" class="tr-cta-text">{{ custom.cta_text }}</p>
      </div>
      <component
        v-if="ctaLink" :is="ctaLink.to ? 'RouterLink' : 'a'" v-reveal="120" class="tr-btn light"
        :to="ctaLink.to" :href="ctaLink.href"
        :target="ctaLink.external ? '_blank' : null" :rel="ctaLink.external ? 'noopener' : null"
      >
        {{ ctaLabel }} <AppIcon name="arrow-right" :size="15" />
      </component>
    </div>
  </section>

  <!-- ===== Contacto ===== -->
  <section v-if="showContact" id="contacto" class="tr-sec tr-contact" aria-labelledby="tr-contact-title">
    <div class="sp-container tr-contact-grid">
      <div class="tr-contact-info">
        <p class="tr-eyebrow"><span class="tr-rule" aria-hidden="true"></span>Contacto</p>
        <h2 id="tr-contact-title" class="tr-h2">Pasá por acá o escribinos</h2>
        <p v-if="mapAddress" class="tr-contact-line"><AppIcon name="map-pin" :size="15" /> {{ mapAddress }}</p>
        <ul v-if="showHours" class="tr-hours">
          <li v-for="(h, i) in contactHours" :key="i"><span>{{ h.label }}</span><strong>{{ h.value }}</strong></li>
        </ul>
        <div class="tr-channels">
          <a v-if="whatsappUrl" class="tr-btn" :href="whatsappUrl" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="15" /> WhatsApp</a>
          <a v-for="s in socials" :key="s.key" class="tr-btn ghost sm" :href="s.url" target="_blank" rel="noopener">{{ s.label }}</a>
        </div>
      </div>
      <form v-reveal="120" class="sp-form tr-form" novalidate @submit.prevent="submitContact">
        <div v-if="contactStatus === 'success'" class="sp-sent" role="status">
          <span class="sp-sent-check" aria-hidden="true"><AppIcon name="check" :size="30" :stroke="2.25" /></span>
          <strong>Mensaje enviado</strong>
          <p>Gracias por escribirnos. Te respondemos a la brevedad al email que dejaste.</p>
          <button type="button" class="tr-btn ghost sm" @click="contactStatus = 'idle'">Enviar otro mensaje</button>
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
              <label for="tr-contact-name">Tu nombre</label>
              <input id="tr-contact-name" v-model="contactForm.name" class="sp-input" type="text" maxlength="80" autocomplete="name" placeholder="Cómo te llamás" required />
            </div>
            <div class="sp-field">
              <label for="tr-contact-email">Tu email</label>
              <input id="tr-contact-email" v-model="contactForm.email" class="sp-input" type="email" autocomplete="email" placeholder="nombre@correo.com" required />
            </div>
          </div>
          <div class="sp-field">
            <label for="tr-contact-message">Mensaje</label>
            <textarea id="tr-contact-message" v-model="contactForm.message" class="sp-input sp-textarea" rows="4" maxlength="2000" placeholder="Contanos en qué te podemos ayudar" required></textarea>
          </div>
          <div class="sp-field">
            <label for="tr-contact-captcha">Verificación rápida</label>
            <div class="sp-captcha-row">
              <span class="sp-captcha-q"><AppIcon name="shield-check" :size="16" aria-hidden="true" /> {{ captcha?.question || 'Cargando…' }}</span>
              <input id="tr-contact-captcha" v-model="contactForm.captcha_answer" class="sp-input" type="text" inputmode="numeric" autocomplete="off" placeholder="Respuesta" required />
              <button type="button" class="sp-icon-btn" :disabled="captchaLoading" aria-label="Nueva pregunta de verificación" title="Nueva pregunta" @click="loadCaptcha">
                <AppIcon name="refresh" :size="15" />
              </button>
            </div>
          </div>
          <div class="sp-hp" aria-hidden="true">
            <label for="tr-contact-website">Website</label>
            <input id="tr-contact-website" v-model="contactForm.website" type="text" tabindex="-1" autocomplete="off" />
          </div>
          <p v-if="contactError" class="sp-form-error" role="alert">{{ contactError }}</p>
          <div class="sp-form-foot">
            <button type="submit" class="tr-btn" :disabled="contactStatus === 'loading' || !captcha">
              <span v-if="contactStatus === 'loading'" class="spinner" aria-hidden="true"></span>
              Enviar mensaje
            </button>
          </div>
        </template>
      </form>
    </div>
    <div v-if="mapUrl" class="sp-container tr-map-wrap">
      <figure v-reveal="120" class="tr-map">
        <iframe :src="mapUrl" title="Mapa con la ubicación del negocio" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe>
        <figcaption><a :href="mapLink" target="_blank" rel="noopener">Abrir en Google Maps <AppIcon name="arrow-up-right" :size="13" /></a></figcaption>
      </figure>
    </div>
  </section>

  <!-- ===== Firma de cierre ===== -->
  <div class="tr-word" aria-hidden="true"><span :style="nameFont">{{ shopName }}</span></div>

  <!-- ===== Visor de galería ===== -->
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
