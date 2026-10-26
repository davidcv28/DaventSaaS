<script setup>
import { ref, reactive, computed, inject, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { storesApi, resolveSectionOrder, SERVICE_ICONS } from '../api/stores.api.js'
import { extractApiError } from '../api/http.js'
import { formatARS } from '../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct } from '../api/catalog.api.js'
import { storeHostSlug } from '../config/env.js'
import AppIcon from '../components/AppIcon.vue'
import { vReveal } from '../directives/reveal.js'
import { openStatus } from '../utils/storeHours.js'

// Página de inicio de la web pública: presentación (hero), carrusel de
// destacados (premium), Sobre nosotros, Galería y Contáctanos. El catálogo
// es una página aparte (StoreCatalogView) y la tienda la resuelve
// StorePublicLayout (inject 'storePage').
const ctx = inject('storePage')
const { slug, custom, shopName, nameFont, initial, location, pageTemplate, hasAbout, showContact, showCatalog, hasDesignAdvanced, loadPublicCatalog } = ctx
// Diseño activo de la portada ('classic' | 'perspective' | 'promo' |
// 'street' | 'terminal'): la estructura del hero se reordena por CSS
// (grid-areas); el decor propio de cada diseño es el único markup extra.
const tpl = pageTemplate

const year = new Date().getFullYear()
const marqueeItems = computed(() => (tpl.value === 'promo'
  ? [{ icon: 'flame', text: 'Ofertas' }, { icon: 'sparkles', text: 'Novedades' }, { icon: 'percent', text: 'Promos' }, { icon: 'zap', text: 'Consultá ya' }]
  : tpl.value === 'street'
    ? [{ icon: 'zap', text: shopName.value }, { icon: 'flame', text: 'Nueva colección' }, { icon: 'tag', text: heroTitle.value }, { icon: 'map-pin', text: location.value || 'Tienda online' }]
    : tpl.value === 'terminal'
      ? [{ icon: 'terminal', text: shopName.value }, { icon: 'check', text: 'status: ok' }, { icon: 'package', text: heroTitle.value }, { icon: 'map-pin', text: location.value || 'tienda online' }]
      : [{ icon: 'zap', text: shopName.value }, { icon: 'star', text: heroTitle.value }, { icon: 'map-pin', text: location.value || 'Tienda online' }]))
const titleSplit = computed(() => {
  const words = heroTitle.value.split(/\s+/)
  return words.length > 1 ? { head: words.slice(0, -1).join(' '), last: words[words.length - 1] } : { head: '', last: heroTitle.value }
})

const copied = ref(false)
const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const router = useRouter()

// Imagen de portada (premium): fondo del hero. Sin diseño avanzado no se usa
// aunque haya quedado una guardada.
const cover = computed(() => (hasDesignAdvanced.value ? custom.value.cover || '' : ''))

// --- Tienda Pro (marketplace): la portada se arma como e-commerce. ---
// El banner principal usa la portada cargada o la primera imagen del
// carrusel; las tarjetas promo laterales toman las siguientes imágenes.
const shopImgs = computed(() => (custom.value.carousel || []).map((i) => i.url))
const shopSlideImg = computed(() => cover.value || shopImgs.value[0] || '')
const shopPromoImgs = computed(() => shopImgs.value.slice(cover.value ? 0 : 1, cover.value ? 2 : 3))
// Productos destacados: vitrina del catálogo en la portada (primeros 8 en
// Tienda Pro, primeros 4 como selección de pliegos en Lookbook).
const shopCatalog = ref({ categories: [], brands: [], products: [] })
const shopProducts = computed(() => shopCatalog.value.products.slice(0, tpl.value === 'lookbook' || tpl.value === 'cobre' ? 4 : tpl.value === 'signature' || tpl.value === 'aurora' ? 6 : 8))
// Minimal: la placa de imagen del hero — portada propia, primera imagen
// del carrusel o, en su defecto, el logo sobre el tile de la paleta.
const mnArtImg = computed(() => cover.value || shopImgs.value[0] || '')
const mnArtProduct = computed(() => shopCatalog.value.products.find((p) => p.image === mnArtImg.value))
// Barra de anuncio (el strip de tinta del diseño editorial): nunca
// promete una oferta que la tienda no tiene cargada.
const mnNotice = computed(() => {
  const parts = []
  if (showCatalog.value) {
    parts.push(shopOffers.value ? `${shopOffers.value} ${shopOffers.value === 1 ? 'oferta activa' : 'ofertas activas'}` : 'Nueva temporada ya disponible')
    parts.push(whatsappUrl.value ? 'Pedidos por WhatsApp' : 'Precios en pesos argentinos')
  } else {
    parts.push(location.value || 'Sitio oficial')
  }
  return parts.join(' · ')
})
const lbPlateImg = computed(() => cover.value || shopImgs.value[0] || shopCatalog.value.products.find((p) => p.image)?.image || '')
// Cobre: placas del hero — portada, carrusel y primeros productos con foto,
// sin repetir la misma imagen en ambas placas.
const cbImgs = computed(() => [cover.value, ...shopImgs.value, ...shopCatalog.value.products.map((p) => p.image)].filter(Boolean))
const cbTileA = computed(() => cbImgs.value[0] || '')
const cbTileB = computed(() => cbImgs.value.find((u) => u !== cbTileA.value) || '')
const cbTileProduct = (img) => shopCatalog.value.products.find((p) => p.image === img)
const cbTileALabel = computed(() => cbTileProduct(cbTileA.value)?.name || shopName.value)
const cbTileBLabel = computed(() => cbTileProduct(cbTileB.value)?.name || 'Nueva temporada')
// Boutique: la placa de prenda del hero reusa el mismo pool de imágenes
// (portada → carrusel → fotos de producto, sin repetir entre placas).
const btTileA = cbTileA
const btTileB = cbTileB
const btTileALabel = cbTileALabel
// Signature: mismas placas del pool (portada → carrusel → productos),
// enmarcadas como carta de autor — placa principal y una miniatura de apoyo.
const sgTileA = cbTileA
const sgTileB = cbTileB
const sgTileALabel = cbTileALabel
// Aurora: el cielo del observatorio — la primera imagen del pool va a la
// placa panorámica y la segunda al visor pequeño del escenario.
const auSky = cbTileA
const auTileB = cbTileB
const shopBrandOf = (p) => shopCatalog.value.brands.find((b) => b.id === p.brand)?.name || ''
const shopCatOf = (p) => shopCatalog.value.categories.find((c) => c.id === p.category)?.name || ''
// Departamentos: categorías reales con productos, en el orden que definió
// el dueño, con el conteo y la primera foto disponible como miniatura (la
// fila de accesos de la portada de un marketplace). Sin categorías cae a
// los destacados.
const shopDepts = computed(() => shopCatalog.value.categories
  .map((c) => {
    const items = shopCatalog.value.products.filter((p) => p.category === c.id)
    return { id: c.id, name: c.name, count: items.length, image: items.find((p) => p.image)?.image || '' }
  })
  .filter((d) => d.count > 0)
  .slice(0, 6))
const deptTo = (id) => ({ ...catalogTo.value, query: { category: id } })
// Clásico: placa del hero (carrusel o primer producto con foto; sin
// imágenes cae al logo) y chips con datos reales del negocio.
const clImg = computed(() => shopImgs.value[0] || shopCatalog.value.products.find((p) => p.image)?.image || '')
const clChipA = computed(() => (openNow.value
  ? { icon: 'clock', text: openNow.value.text }
  : { icon: location.value ? 'map-pin' : 'store', text: location.value || shopName.value }))
const clChipB = computed(() => {
  const n = shopCatalog.value.products.length
  if (showCatalog.value && n) return { icon: 'package', text: `${n} ${n === 1 ? 'producto' : 'productos'}` }
  if (custom.value.about_years) return { icon: 'star', text: `+${custom.value.about_years} años` }
  return { icon: 'shield-check', text: 'Atención personalizada' }
})
// Ofertas activas: alimentan el copy del acceso promo del hero (nunca se
// anuncia una oferta que la tienda no tiene).
const shopOffers = computed(() => shopCatalog.value.products.filter((p) => productOffer(p) != null).length)
const shopPromoEyebrow = computed(() => {
  if (!showCatalog.value) return 'Atención personalizada'
  return shopOffers.value
    ? `${shopOffers.value} ${shopOffers.value === 1 ? 'oferta activa' : 'ofertas activas'}`
    : 'Catálogo completo'
})
async function loadShopFeatured() {
  if (!['shop', 'lookbook', 'cobre', 'minimal', 'classic', 'boutique', 'signature', 'aurora'].includes(tpl.value) || !showCatalog.value) return
  try {
    shopCatalog.value = await loadPublicCatalog({ sort: 'recent' })
  } catch {
    shopCatalog.value = { categories: [], brands: [], products: [] }
  }
}
// La tarjeta entera abre la ficha del producto (mismo destino que en el
// catálogo: /producto/<id> en subdominio, /<slug>/producto/<id> en plataforma).
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })
const openProduct = (p) => router.push(productTo(p))

// --- Presentación (hero): banda de acento con la identidad del negocio.
// Si el dueño cargó un titular, el titular es el h1 y el nombre viaja en el
// badge; si no, el h1 es el nombre y el badge muestra la ubicación. ---
const heroTitleIsName = computed(() => !custom.value.headline?.trim())
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value)
// Sin catálogo la web es una vidriera: el badge de fallback es "Sitio oficial".
const heroBadge = computed(() => (heroTitleIsName.value ? (location.value || (showCatalog.value ? 'Catálogo online' : 'Sitio oficial')) : shopName.value))
const heroBadgeIcon = computed(() => (heroTitleIsName.value ? (location.value ? 'map-pin' : 'store') : ''))
// "Abierto ahora / Cerrado": sale de los horarios cargados (texto libre); si
// no se pueden interpretar no se muestra nada. Se recalcula cada minuto.
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

// --- Sobre nosotros (se edita en "Mi empresa" del dashboard; el dueño la
// apaga con show_about y además se oculta sola si no cargó ningún contenido) ---
const aboutSpecialties = computed(() => String(custom.value.about_specialties || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean)
  .slice(0, 12))
// Tarjeta destacada de la sección (columna derecha): solo existe si hay
// años de trayectoria o misión cargados; sin ellos la info va a una columna.
const hasAboutCard = computed(() => Boolean(custom.value.about_years || custom.value.about_mission?.trim()))
const aboutTitle = computed(() => custom.value.about_title?.trim() || 'Sobre nosotros')

// --- Destacados: tarjetas con icono bajo el hero, armadas con lo que el
// negocio realmente tiene cargado y completadas con valores genéricos. ---
const highlights = computed(() => {
  const list = []
  if (showCatalog.value) list.push({ icon: 'package', title: 'Catálogo online', text: 'Explorá todos los productos con precios y detalles actualizados.', to: catalogTo.value })
  if (showContact.value) list.push({ icon: 'message-circle', title: 'Consultas directas', text: 'Escribinos y te respondemos a la brevedad.', href: '#contacto' })
  if (location.value) list.push({ icon: 'map-pin', title: 'Dónde estamos', text: location.value })
  if (custom.value.about_years) list.push({ icon: 'clock', title: `+${custom.value.about_years} años`, text: 'De trayectoria y experiencia en lo que hacemos.' })
  list.push(
    { icon: 'users', title: 'Atención personalizada', text: 'Te acompañamos en cada paso de tu compra.' },
    { icon: 'shield-check', title: 'Información clara', text: 'Productos y precios claros, sin sorpresas.' }
  )
  return list.slice(0, 4)
})

// --- Galería (imágenes propias del negocio; el dueño la apaga con
// show_gallery y se oculta sola sin imágenes cargadas) ---
const gallery = computed(() => custom.value.gallery || [])
const showGallery = computed(() => ctx.showGallery.value)
// Imágenes ilustrativas de la portada (premium, hasta 3): siempre van al
// lado de un texto — una enmarca Sobre nosotros, otra acompaña la banda de
// invitación antes de Contáctanos y la última cierra la columna de
// contacto. En móvil se ocultan por CSS.
const decor = computed(() => (hasDesignAdvanced.value ? (custom.value.decor || []).slice(0, 3) : []))
const decorAbout = computed(() => (hasAbout.value ? decor.value[0] || null : null))
const decorPool = computed(() => decor.value.slice(decorAbout.value ? 1 : 0))
const decorBand = computed(() => decorPool.value[0] || null)
const decorContact = computed(() => (showContact.value ? decorPool.value[decorBand.value ? 1 : 0] || null : null))
// Banda decorativa: la imagen acompaña una invitación con CTAs (la misión
// cargada sirve de bajada cuando existe); nunca una foto suelta a todo lo
// ancho ni sin contexto.
const showcaseTitle = computed(() => (showContact.value ? 'Hablemos de lo que buscás' : `Conocé ${shopName.value}`))
const showcaseText = computed(() => custom.value.about_mission?.trim() || '')
const lightboxIndex = ref(-1)
const lightboxImage = computed(() => (lightboxIndex.value >= 0 ? gallery.value[lightboxIndex.value] || null : null))
const openLightbox = (index) => { lightboxIndex.value = index }
const closeLightbox = () => { lightboxIndex.value = -1 }
function stepLightbox(direction) {
  const total = gallery.value.length
  if (total < 2) return
  lightboxIndex.value = ((lightboxIndex.value + direction) % total + total) % total
}

// --- Bloques de marketing (se editan en "Mi empresa"): cada uno se apaga
// con su show_* y además se oculta solo si quedó sin contenido. El orden
// de las secciones de la portada sale de section_order (claves cerradas):
// se aplica como CSS order sobre los <section> hijos de .sp-page-root —
// el hero va primero y Contáctanos último siempre (order 99). ---
const listOf = (value) => (Array.isArray(value) ? value : [])
const services = computed(() => listOf(custom.value.services))
const showServices = computed(() => custom.value.show_services !== false && services.value.length > 0)
const servicesTitle = computed(() => custom.value.services_title?.trim() || 'Qué ofrecemos')
const serviceIcon = (key) => (SERVICE_ICONS[key] ? key : 'package')
const stats = computed(() => listOf(custom.value.stats))
const showStats = computed(() => custom.value.show_stats !== false && stats.value.length > 0)
const testimonials = computed(() => listOf(custom.value.testimonials))
const showTestimonials = computed(() => custom.value.show_testimonials !== false && testimonials.value.length > 0)
const testimonialsTitle = computed(() => custom.value.testimonials_title?.trim() || 'Lo que dicen nuestros clientes')
const faqs = computed(() => listOf(custom.value.faqs))
const showFaqs = computed(() => custom.value.show_faq !== false && faqs.value.length > 0)
const faqsTitle = computed(() => custom.value.faqs_title?.trim() || 'Preguntas frecuentes')
// El eyebrow repite el título cuando el dueño dejó el texto por defecto
// ("DUDAS FRECUENTES / Dudas frecuentes"): en ese caso no se muestra.
const eyebrowUnless = (label, title) => (String(title || '').trim().toLowerCase() === label.toLowerCase() ? '' : label)
const faqEyebrow = computed(() => eyebrowUnless('Dudas frecuentes', faqsTitle.value))
const servicesEyebrow = computed(() => eyebrowUnless('Servicios', servicesTitle.value))
const testimonialsEyebrow = computed(() => eyebrowUnless('Clientes', testimonialsTitle.value))
// Tarjetas de testimonios 100% iguales: el grid solo estira por fila, así
// que se mide la tarjeta más alta y se iguala el resto con min-height
// (offsetHeight ignora el transform de la animación de entrada). Se
// recalcula al cambiar el tamaño del grid, la lista o al montar.
const testiGrid = ref(null)
let testiRO = null
function equalizeTestimonials() {
  const grid = testiGrid.value
  if (!grid) return
  const cards = grid.querySelectorAll('.sp-testimonial')
  cards.forEach((c) => { c.style.minHeight = '' })
  const max = Math.ceil(Math.max(0, ...[...cards].map((c) => c.offsetHeight)))
  if (max) cards.forEach((c) => { c.style.minHeight = `${max}px` })
}
watch(testiGrid, (el) => {
  testiRO?.disconnect()
  testiRO = null
  if (el && 'ResizeObserver' in window) { testiRO = new ResizeObserver(equalizeTestimonials); testiRO.observe(el) }
  nextTick(equalizeTestimonials)
})
watch(testimonials, () => nextTick(equalizeTestimonials))
const contactHours = computed(() => listOf(custom.value.hours))
const showHours = computed(() => custom.value.show_hours !== false && contactHours.value.length > 0)
// Orden efectivo de las secciones (posición CSS order; 0 queda para el hero).
const sectionPos = computed(() => {
  const pos = {}
  resolveSectionOrder(custom.value.section_order).forEach((key, i) => { pos[key] = i + 1 })
  return pos
})

// --- Contáctanos: formulario público (captcha + honeypot antispam), canales
// y el mapa de ubicación, que vive dentro de esta sección. ---
const contactForm = reactive({ name: '', email: '', message: '', website: '', captcha_answer: '' })
const captcha = ref(null) // {challenge_id, question}
const captchaLoading = ref(false)
const contactStatus = ref('idle') // idle | loading | success | error
const contactError = ref('')

// Canales de contacto (solo dentro de esta sección, regla de diseño).
const whatsappUrl = computed(() => (custom.value.whatsapp ? `https://wa.me/${custom.value.whatsapp.replace(/\D/g, '')}` : ''))
const instagramUrl = computed(() => (custom.value.instagram ? `https://instagram.com/${custom.value.instagram}` : ''))
const tiktokUrl = computed(() => (custom.value.tiktok ? `https://tiktok.com/@${custom.value.tiktok}` : ''))
const facebookUrl = computed(() => (custom.value.facebook ? `https://facebook.com/${custom.value.facebook}` : ''))
const socials = computed(() => [
  { key: 'instagram', label: 'Instagram', url: instagramUrl.value },
  { key: 'tiktok', label: 'TikTok', url: tiktokUrl.value },
  { key: 'facebook', label: 'Facebook', url: facebookUrl.value }
].filter((s) => s.url))
const hasContactChannels = computed(() => Boolean(whatsappUrl.value || socials.value.length))

// Banda de llamado a la acción: el botón apunta a WhatsApp si el dueño
// cargó uno; si no, al formulario de contacto o al catálogo (en ese orden
// de preferencia). La banda solo existe si hay título o texto cargados.
const showCta = computed(() => custom.value.show_cta !== false
  && Boolean(custom.value.cta_title?.trim() || custom.value.cta_text?.trim()))
const ctaTitle = computed(() => custom.value.cta_title?.trim() || '¿Hablamos?')
const ctaLink = computed(() => {
  if (whatsappUrl.value) return { href: whatsappUrl.value, external: true }
  if (showContact.value) return { href: '#contacto', external: false }
  if (showCatalog.value) return { to: catalogTo.value, external: false }
  return null
})
const ctaLabel = computed(() => custom.value.cta_label?.trim()
  || (ctaLink.value?.external ? 'Escribinos por WhatsApp' : ctaLink.value?.href === '#contacto' ? 'Contáctanos' : 'Ver catálogo'))

// Mapa de ubicación (beneficio has_location_map, Estándar y Premium): el
// backend devuelve location_address ya armada para geocodificar, o null si
// el dueño lo apagó en Diseño web.
const mapAddress = computed(() => ctx.store.value?.location_address || '')
const mapUrl = computed(() => (
  mapAddress.value
    ? `https://maps.google.com/maps?q=${encodeURIComponent(mapAddress.value)}&output=embed&z=16`
    : ''
))
// Enlace directo al mapa: sirve de salida si el navegador bloquea el embed.
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
  loadShopFeatured()
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
<div class="sp-page-root">
  <!-- ===== Presentación (portada de la empresa) ===== -->
  <section class="sp-hero">
    <div class="sp-hero-band" :class="{ 'has-cover': cover && tpl !== 'lookbook' && tpl !== 'shop' && tpl !== 'cobre' && tpl !== 'minimal' && tpl !== 'boutique' && tpl !== 'signature' && tpl !== 'aurora' }">
      <!-- Minimal y Boutique: barra de anuncio (strip editorial del diseño) -->
      <p v-if="tpl === 'minimal' || tpl === 'boutique'" class="sp-mn-announce">{{ mnNotice }}</p>
      <div v-if="cover && tpl !== 'lookbook' && tpl !== 'shop' && tpl !== 'cobre' && tpl !== 'minimal' && tpl !== 'boutique' && tpl !== 'signature' && tpl !== 'aurora'" class="sp-hero-cover" aria-hidden="true">
        <img :src="cover" alt="" fetchpriority="high" />
      </div>
      <div class="sp-hero-decor" aria-hidden="true">
        <span class="sp-orb o1"></span>
        <span class="sp-orb o2"></span>
        <span class="sp-orb o3"></span>
        <span class="sp-float f1"><AppIcon name="package" :size="26" /></span>
        <span class="sp-float f2"><AppIcon name="tag" :size="22" /></span>
        <span class="sp-float f3"><AppIcon name="shield-check" :size="24" /></span>
        <span class="sp-float f4"><AppIcon name="trending-up" :size="22" /></span>
        <span class="sp-float f5"><AppIcon name="store" :size="24" /></span>
        <template v-if="tpl === 'street'">
          <span class="sp-st-ghost">{{ shopName }}</span>
          <span class="sp-st-sticker">
            <svg class="sp-st-sticker-ring" viewBox="0 0 200 200">
              <defs><path id="sp-st-circle" d="M100,100 m-80,0 a80,80 0 1,1 160,0 a80,80 0 1,1 -160,0" /></defs>
              <text><textPath href="#sp-st-circle" textLength="498" lengthAdjust="spacing">NUEVA COLECCIÓN • DROP EXCLUSIVO • </textPath></text>
            </svg>
            <span class="sp-st-sticker-core"><AppIcon name="zap" :size="34" :stroke="2" /></span>
          </span>
          <span class="sp-st-barcode"><i></i><em>SS{{ String(year).slice(2) }}</em></span>
          <span class="sp-st-spray"></span>
          <span class="sp-st-tape"></span>
        </template>
        <template v-else-if="tpl === 'perspective'">
          <span class="sp-px-floor"></span>
          <span class="sp-px-plane p1"></span>
          <span class="sp-px-plane p2"></span>
          <span class="sp-px-mote m1"></span>
          <span class="sp-px-mote m2"></span>
          <span class="sp-px-mote m3"></span>
          <span class="sp-px-mote m4"></span>
          <span class="sp-px-ripple r1"></span>
          <span class="sp-px-ripple r2"></span>
        </template>
        <template v-else-if="tpl === 'promo'">
          <span class="sp-pr-burst"></span>
          <span class="sp-pr-spark s1"><AppIcon name="sparkles" :size="30" :stroke="2" /></span>
          <span class="sp-pr-spark s2"><AppIcon name="star" :size="22" :stroke="2" /></span>
          <span class="sp-pr-spark s3"><AppIcon name="zap" :size="26" :stroke="2" /></span>
          <span class="sp-pr-conf c1"></span>
          <span class="sp-pr-conf c2"></span>
          <span class="sp-pr-conf c3"></span>
          <span class="sp-pr-conf c4"></span>
          <span class="sp-pr-conf c5"></span>
          <span class="sp-pr-tagfloat"><AppIcon name="percent" :size="20" :stroke="2.5" /></span>
        </template>
        <template v-else-if="tpl === 'terminal'">
          <span class="sp-tm-ghost">&gt;_</span>
          <span class="sp-tm-rain r1"><i>0110100101101011010010110100101101</i><i>0110100101101011010010110100101101</i></span>
          <span class="sp-tm-rain r2"><i>1011010010110100101101001011010010</i><i>1011010010110100101101001011010010</i></span>
          <span class="sp-tm-corner tl"></span>
          <span class="sp-tm-corner tr"></span>
          <span class="sp-tm-corner bl"></span>
          <span class="sp-tm-corner br"></span>
          <span class="sp-tm-log">
            <i><b>[ ok ]</b> tienda inicializada</i>
            <i><b>[ ok ]</b> identidad cargada</i>
            <i><b>[ ok ]</b> catálogo indexado</i>
            <i class="dim">$ esperando visitante<span class="sp-tm-caret"></span></i>
          </span>
        </template>
        <template v-else-if="tpl === 'lookbook'">
          <span class="sp-lb-rail">Lookbook</span>
          <span class="sp-lb-asterisk">*</span>
          <span class="sp-lb-folio">Pág. 01 / 04</span>
        </template>
        <template v-else-if="tpl === 'boutique'">
          <span class="sp-bt-ghost">{{ shopName }}</span>
          <span class="sp-bt-sparkle s1"><AppIcon name="sparkles" :size="22" :stroke="1.5" /></span>
          <span class="sp-bt-sparkle s2"><AppIcon name="star" :size="15" :stroke="1.5" /></span>
          <span class="sp-bt-sparkle s3"><AppIcon name="sparkles" :size="17" :stroke="1.5" /></span>
          <span class="sp-bt-seal">
            <svg class="sp-bt-seal-ring" viewBox="0 0 200 200">
              <defs><path id="sp-bt-circle" d="M100,100 m-76,0 a76,76 0 1,1 152,0 a76,76 0 1,1 -152,0" /></defs>
              <text><textPath href="#sp-bt-circle" textLength="474" lengthAdjust="spacing">COLECCIÓN • NUEVA TEMPORADA • </textPath></text>
            </svg>
            <span class="sp-bt-seal-core"><AppIcon name="star" :size="20" :stroke="1.5" /></span>
          </span>
        </template>
        <template v-else-if="tpl === 'classic'">
          <span class="sp-cl-ring"></span>
          <span class="sp-cl-orbit"><i></i></span>
          <span class="sp-cl-spark s1"><AppIcon name="plus" :size="18" :stroke="2.5" /></span>
          <span class="sp-cl-spark s2"><AppIcon name="plus" :size="14" :stroke="2.5" /></span>
        </template>
        <template v-else-if="tpl === 'cobre'">
          <span class="sp-cb-stitch t1"></span>
          <span class="sp-cb-stitch t2"></span>
          <span class="sp-cb-tape"></span>
        </template>
        <template v-else-if="tpl === 'minimal'">
          <span class="sp-mn-circle"></span>
          <span class="sp-mn-plus p1"></span>
          <span class="sp-mn-plus p2"></span>
          <span class="sp-mn-index">Nº 01</span>
        </template>
        <template v-else-if="tpl === 'shop'">
          <span class="sp-shop-chip d1"><AppIcon name="package" :size="20" :stroke="2" /></span>
          <span class="sp-shop-chip d2"><AppIcon name="percent" :size="17" :stroke="2.25" /></span>
          <span class="sp-shop-chip d3"><AppIcon name="tag" :size="16" :stroke="2" /></span>
        </template>
        <template v-else-if="tpl === 'signature'">
          <span class="sp-sg-ghost">{{ initial }}</span>
          <span class="sp-sg-seal">
            <svg class="sp-sg-seal-ring" viewBox="0 0 200 200">
              <defs><path id="sp-sg-circle" d="M100,100 m-76,0 a76,76 0 1,1 152,0 a76,76 0 1,1 -152,0" /></defs>
              <text><textPath href="#sp-sg-circle" textLength="474" lengthAdjust="spacing">FIRMA DE AUTOR • EDICIÓN CONTINUA • </textPath></text>
            </svg>
            <span class="sp-sg-seal-core"><AppIcon name="gem" :size="20" :stroke="1.5" /></span>
          </span>
        </template>
        <template v-else-if="tpl === 'aurora'">
          <!-- Cortinas de aurora: haces de luz inclinados en el acento del
               negocio, un segundo tono frío y estrellas que titilan. -->
          <span class="sp-au-beam b1"></span>
          <span class="sp-au-beam b2"></span>
          <span class="sp-au-beam b3"></span>
          <span class="sp-au-star s1"><AppIcon name="star" :size="13" :stroke="1.5" /></span>
          <span class="sp-au-star s2"><AppIcon name="sparkles" :size="18" :stroke="1.5" /></span>
          <span class="sp-au-star s3"><AppIcon name="star" :size="10" :stroke="1.5" /></span>
          <span class="sp-au-star s4"><AppIcon name="sparkles" :size="12" :stroke="1.5" /></span>
          <span class="sp-au-horizon"></span>
        </template>
      </div>
      <div v-if="tpl === 'terminal'" class="sp-container sp-tm-bar" aria-hidden="true">
        <span class="sp-tm-dots"><i></i><i></i><i></i></span>
        <span class="sp-tm-path">tienda@davent:~/{{ slug }}</span>
        <span class="sp-tm-live">[ en línea ]</span>
      </div>
      <div class="sp-container sp-hero-inner">
        <span v-if="tpl === 'promo'" class="sp-pr-tag"><AppIcon name="megaphone" :size="15" :stroke="2.25" /> ¡Novedad!</span>
        <template v-if="tpl === 'lookbook'">
          <!-- Lookbook: columna de texto en .sp-lb-copy para que el pliego no
               infle las filas del grid (un item que abarca N filas reparte su
               alto entre ellas y dejaba huecos enormes). -->
          <div class="sp-lb-copy">
            <p v-reveal class="sp-lb-dateline">
              <span>Nº 01</span><i aria-hidden="true"></i><span>{{ year }}</span><i aria-hidden="true"></i><span>{{ location || 'Tienda online' }}</span>
            </p>
            <h1 v-reveal="160" class="sp-hero-title" :class="{ 'is-name': heroTitleIsName }" :style="heroTitleIsName ? nameFont : null">{{ titleSplit.head }} <em class="sp-lb-mark">{{ titleSplit.last }}</em></h1>
            <p v-if="custom.description" v-reveal="240" class="sp-hero-sub">{{ custom.description }}</p>
            <div v-reveal="320" class="sp-hero-ctas">
              <RouterLink v-if="showCatalog" class="sp-btn sp-hero-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
              <a v-if="showContact" class="sp-btn sp-hero-ghost" href="#contacto"><AppIcon name="message-circle" :size="16" /> Contáctanos</a>
              <button type="button" class="sp-icon-btn" :aria-label="copied ? 'Link copiado' : 'Compartir tienda'" :title="copied ? 'Link copiado' : 'Compartir'" @click="share">
                <AppIcon :name="copied ? 'check' : 'share-2'" :size="17" />
              </button>
            </div>
            <ul v-if="heroMeta.length" v-reveal="400" class="sp-hero-meta">
              <li v-for="m in heroMeta" :key="m.key" :class="m.state ? `sp-open is-${m.state}` : null"><span v-if="m.state" class="sp-live-dot" aria-hidden="true"></span><AppIcon v-else :name="m.icon" :size="14" /> {{ m.text }}</li>
            </ul>
          </div>
          <figure v-reveal="120" class="sp-lb-plate" :class="{ 'is-logo': !lbPlateImg && custom.logo }">
            <div class="sp-lb-plate-frame">
              <img v-if="lbPlateImg" :src="lbPlateImg" alt="" fetchpriority="high" />
              <img v-else-if="custom.logo" :src="custom.logo" :alt="`Logo de ${shopName}`" />
              <span v-else class="sp-lb-plate-initial" aria-hidden="true">{{ initial }}</span>
            </div>
            <figcaption><span>Fig. 01</span><i></i><span>{{ shopName }}</span></figcaption>
            <span class="sp-lb-plate-seal" aria-hidden="true">Nº<br />01</span>
          </figure>
        </template>
        <template v-else-if="tpl === 'cobre'">
          <!-- Cobre (retail de indumentaria): copy a la izquierda y dos
               placas de imagen superpuestas — la primera sobre acento, la
               segunda sobre tinta, como el afiche de la vidriera. -->
          <div class="sp-cb-copy">
            <p v-reveal class="sp-cb-kicker">
              <AppIcon :name="heroBadgeIcon || 'store'" :size="14" :stroke="2.25" /> {{ heroBadge }}
            </p>
            <h1 v-reveal="160" class="sp-hero-title" :class="{ 'is-name': heroTitleIsName }" :style="heroTitleIsName ? nameFont : null">{{ titleSplit.head }} <span class="sp-cb-mark">{{ titleSplit.last }}</span></h1>
            <p v-if="custom.description" v-reveal="240" class="sp-hero-sub">{{ custom.description }}</p>
            <div v-reveal="320" class="sp-hero-ctas">
              <RouterLink v-if="showCatalog" class="sp-btn sp-hero-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
              <a v-if="showContact" class="sp-btn sp-hero-ghost" href="#contacto"><AppIcon name="message-circle" :size="16" /> Contáctanos</a>
              <button type="button" class="sp-icon-btn" :aria-label="copied ? 'Link copiado' : 'Compartir tienda'" :title="copied ? 'Link copiado' : 'Compartir'" @click="share">
                <AppIcon :name="copied ? 'check' : 'share-2'" :size="17" />
              </button>
            </div>
            <ul v-if="heroMeta.length" v-reveal="400" class="sp-hero-meta">
              <li v-for="m in heroMeta" :key="m.key" :class="m.state ? `sp-open is-${m.state}` : null"><span v-if="m.state" class="sp-live-dot" aria-hidden="true"></span><AppIcon v-else :name="m.icon" :size="14" /> {{ m.text }}</li>
            </ul>
          </div>
          <div v-reveal="120" class="sp-cb-art">
            <figure class="sp-cb-tile main" :class="{ 'is-logo': !cbTileA && custom.logo }">
              <img v-if="cbTileA" :src="cbTileA" alt="" fetchpriority="high" />
              <img v-else-if="custom.logo" :src="custom.logo" :alt="`Logo de ${shopName}`" />
              <span v-else class="sp-cb-tile-initial" aria-hidden="true">{{ initial }}</span>
              <figcaption>{{ cbTileALabel }}</figcaption>
            </figure>
            <figure class="sp-cb-tile alt" :class="{ 'is-logo': !cbTileB && custom.logo }">
              <img v-if="cbTileB" :src="cbTileB" alt="" loading="lazy" />
              <img v-else-if="custom.logo" :src="custom.logo" :alt="`Logo de ${shopName}`" />
              <span v-else class="sp-cb-tile-initial" aria-hidden="true">{{ initial }}</span>
              <figcaption>{{ cbTileBLabel }}</figcaption>
            </figure>
          </div>
        </template>
        <template v-else-if="tpl === 'minimal'">
          <!-- Minimal: hero tipográfico editorial — eyebrow de acento,
               titular XXL pesado y una placa de imagen a la derecha
               (portada, carrusel, logo o la inicial sobre el tile). -->
          <div class="sp-mn-copy">
            <p v-reveal class="sp-mn-kicker">
              <AppIcon :name="heroBadgeIcon || 'tag'" :size="13" :stroke="2.5" /> {{ heroBadge }}
            </p>
            <h1 v-reveal="160" class="sp-hero-title" :class="{ 'is-name': heroTitleIsName }" :style="heroTitleIsName ? nameFont : null">{{ titleSplit.head }} <span class="sp-mn-mark">{{ titleSplit.last }}</span></h1>
            <p v-if="custom.description" v-reveal="240" class="sp-hero-sub">{{ custom.description }}</p>
            <div v-reveal="320" class="sp-hero-ctas">
              <RouterLink v-if="showCatalog" class="sp-btn sp-hero-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
              <a v-if="showContact" class="sp-btn sp-hero-ghost" href="#contacto"><AppIcon name="message-circle" :size="16" /> Contáctanos</a>
              <button type="button" class="sp-icon-btn" :aria-label="copied ? 'Link copiado' : 'Compartir tienda'" :title="copied ? 'Link copiado' : 'Compartir'" @click="share">
                <AppIcon :name="copied ? 'check' : 'share-2'" :size="17" />
              </button>
            </div>
            <ul v-if="heroMeta.length" v-reveal="400" class="sp-hero-meta">
              <li v-for="m in heroMeta" :key="m.key" :class="m.state ? `sp-open is-${m.state}` : null"><span v-if="m.state" class="sp-live-dot" aria-hidden="true"></span><AppIcon v-else :name="m.icon" :size="14" /> {{ m.text }}</li>
            </ul>
          </div>
          <figure v-reveal="120" class="sp-mn-art" :class="{ 'is-logo': !mnArtImg && custom.logo }">
            <img v-if="mnArtImg" :src="mnArtImg" alt="" fetchpriority="high" />
            <img v-else-if="custom.logo" :src="custom.logo" :alt="`Logo de ${shopName}`" />
            <span v-else class="sp-mn-art-initial" aria-hidden="true">{{ initial }}</span>
            <figcaption>{{ mnArtProduct?.name || shopName }}</figcaption>
          </figure>
        </template>
        <template v-else-if="tpl === 'boutique'">
          <!-- Boutique (catálogo de indumentaria): hero de campaña — copy
               con serif editorial a la izquierda y placa de prenda 3:4 a la
               derecha con etiqueta de temporada y placa secundaria
               superpuesta (como el afiche de una boutique). -->
          <div class="sp-bt-copy">
            <p v-reveal class="sp-bt-kicker">
              <AppIcon :name="heroBadgeIcon || 'tag'" :size="13" :stroke="2.5" /> {{ heroBadge }}
            </p>
            <h1 v-reveal="160" class="sp-hero-title" :class="{ 'is-name': heroTitleIsName }" :style="heroTitleIsName ? nameFont : null">{{ titleSplit.head }} <em class="sp-bt-mark">{{ titleSplit.last }}</em></h1>
            <p v-if="custom.description" v-reveal="240" class="sp-hero-sub">{{ custom.description }}</p>
            <div v-reveal="320" class="sp-hero-ctas">
              <RouterLink v-if="showCatalog" class="sp-btn sp-hero-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
              <a v-if="showContact" class="sp-btn sp-hero-ghost" href="#contacto"><AppIcon name="message-circle" :size="16" /> Contáctanos</a>
              <button type="button" class="sp-icon-btn" :aria-label="copied ? 'Link copiado' : 'Compartir tienda'" :title="copied ? 'Link copiado' : 'Compartir'" @click="share">
                <AppIcon :name="copied ? 'check' : 'share-2'" :size="17" />
              </button>
            </div>
            <ul v-if="heroMeta.length" v-reveal="400" class="sp-hero-meta">
              <li v-for="m in heroMeta" :key="m.key" :class="m.state ? `sp-open is-${m.state}` : null"><span v-if="m.state" class="sp-live-dot" aria-hidden="true"></span><AppIcon v-else :name="m.icon" :size="14" /> {{ m.text }}</li>
            </ul>
          </div>
          <div v-reveal="120" class="sp-bt-art">
            <figure class="sp-bt-plate" :class="{ 'is-logo': !btTileA && custom.logo }">
              <img v-if="btTileA" :src="btTileA" alt="" fetchpriority="high" />
              <img v-else-if="custom.logo" :src="custom.logo" :alt="`Logo de ${shopName}`" />
              <span v-else class="sp-bt-plate-initial" aria-hidden="true">{{ initial }}</span>
              <figcaption>{{ btTileALabel }}</figcaption>
            </figure>
            <figure v-if="btTileB" class="sp-bt-plate alt" aria-hidden="true">
              <img :src="btTileB" alt="" loading="lazy" />
            </figure>
            <span class="sp-bt-tag" aria-hidden="true">SS{{ String(year).slice(2) }}</span>
          </div>
        </template>
        <template v-else-if="tpl === 'signature'">
          <!-- Signature (casa de autor): composición ceremonial — copy a la
               izquierda con dateline grabado, titular Cinzel con doble
               filete en la última palabra y la firma manuscrita del
               negocio; a la derecha una placa retrato enmar­cada con
               doble filete y el monograma en cartucho. -->
          <div class="sp-sg-copy">
            <p v-reveal class="sp-sg-dateline">
              <i aria-hidden="true"></i><span>{{ heroBadge }}</span><i aria-hidden="true"></i><span>{{ year }}</span>
            </p>
            <h1 v-reveal="160" class="sp-hero-title" :class="{ 'is-name': heroTitleIsName }" :style="heroTitleIsName ? nameFont : null">{{ titleSplit.head }} <span class="sp-sg-mark">{{ titleSplit.last }}</span></h1>
            <p v-if="custom.description" v-reveal="240" class="sp-hero-sub">{{ custom.description }}</p>
            <div v-reveal="320" class="sp-hero-ctas">
              <RouterLink v-if="showCatalog" class="sp-btn sp-hero-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
              <a v-if="showContact" class="sp-btn sp-hero-ghost" href="#contacto"><AppIcon name="message-circle" :size="16" /> Contáctanos</a>
              <button type="button" class="sp-icon-btn" :aria-label="copied ? 'Link copiado' : 'Compartir tienda'" :title="copied ? 'Link copiado' : 'Compartir'" @click="share">
                <AppIcon :name="copied ? 'check' : 'share-2'" :size="17" />
              </button>
            </div>
            <ul v-if="heroMeta.length" v-reveal="400" class="sp-hero-meta">
              <li v-for="m in heroMeta" :key="m.key" :class="m.state ? `sp-open is-${m.state}` : null"><span v-if="m.state" class="sp-live-dot" aria-hidden="true"></span><AppIcon v-else :name="m.icon" :size="14" /> {{ m.text }}</li>
            </ul>
          </div>
          <div v-reveal="120" class="sp-sg-art">
            <figure class="sp-sg-plate" :class="{ 'is-logo': !sgTileA && custom.logo }">
              <img v-if="sgTileA" :src="sgTileA" alt="" fetchpriority="high" />
              <img v-else-if="custom.logo" :src="custom.logo" :alt="`Logo de ${shopName}`" />
              <span v-else class="sp-sg-plate-initial" aria-hidden="true">{{ initial }}</span>
              <figcaption>{{ sgTileALabel }}</figcaption>
            </figure>
            <figure v-if="sgTileB" class="sp-sg-plate alt" aria-hidden="true">
              <img :src="sgTileB" alt="" loading="lazy" />
            </figure>
            <span class="sp-sg-mono" aria-hidden="true"><i>{{ initial }}</i></span>
          </div>
        </template>
        <template v-else-if="tpl === 'aurora'">
          <!-- Aurora (observatorio de luz): el orden se invierte respecto de
               los demás diseños — primero el raíl de instrumentos (datos
               finos a todo lo ancho), después el cielo panorámico con sus
               piezas flotantes y, solapando su borde inferior, la placa de
               vidrio esmerilado que lleva el mensaje. -->
          <div class="sp-au-wrap">
            <div v-reveal class="sp-au-rail">
              <p class="sp-au-badge"><AppIcon :name="heroBadgeIcon || 'sparkles'" :size="13" :stroke="2.25" /> {{ heroBadge }}</p>
              <div class="sp-au-rail-side">
                <ul v-if="heroMeta.length" class="sp-au-rail-meta">
                  <li v-for="m in heroMeta" :key="m.key" :class="m.state ? `sp-open is-${m.state}` : null"><span v-if="m.state" class="sp-live-dot" aria-hidden="true"></span><AppIcon v-else :name="m.icon" :size="13" /> {{ m.text }}</li>
                </ul>
                <span class="sp-au-rail-year" aria-hidden="true"><i></i>{{ year }}</span>
              </div>
            </div>
            <div v-reveal="120" class="sp-au-stage">
              <figure class="sp-au-media" :class="{ 'is-logo': !auSky && custom.logo }">
                <img v-if="auSky" :src="auSky" alt="" fetchpriority="high" />
                <img v-else-if="custom.logo" :src="custom.logo" :alt="`Logo de ${shopName}`" />
                <span v-else class="sp-au-initial" aria-hidden="true">{{ initial }}</span>
              </figure>
              <figure v-if="auTileB" class="sp-au-mini" aria-hidden="true">
                <img :src="auTileB" alt="" loading="lazy" />
              </figure>
              <span class="sp-au-chip"><AppIcon :name="clChipB.icon" :size="13" :stroke="2.25" /> {{ clChipB.text }}</span>
              <span class="sp-au-polaris" aria-hidden="true"><AppIcon name="star" :size="15" :stroke="1.75" /></span>
              <div v-reveal="200" class="sp-au-card">
                <h1 class="sp-hero-title" :class="{ 'is-name': heroTitleIsName }" :style="heroTitleIsName ? nameFont : null">{{ titleSplit.head }} <span class="sp-au-mark">{{ titleSplit.last }}</span></h1>
                <p v-if="custom.description" class="sp-hero-sub">{{ custom.description }}</p>
                <div class="sp-hero-ctas">
                  <RouterLink v-if="showCatalog" class="sp-btn sp-hero-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
                  <a v-if="showContact" class="sp-btn sp-hero-ghost" href="#contacto"><AppIcon name="message-circle" :size="16" /> Contáctanos</a>
                  <button type="button" class="sp-icon-btn" :aria-label="copied ? 'Link copiado' : 'Compartir tienda'" :title="copied ? 'Link copiado' : 'Compartir'" @click="share">
                    <AppIcon :name="copied ? 'check' : 'share-2'" :size="17" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </template>
        <template v-else-if="tpl === 'shop'">
          <!-- Tienda Pro (marketplace): banner principal + dos tarjetas
               promo apiladas, como la portada de un e-commerce. La foto va
               como fondo del banner; en las promos la imagen ocupa el panel
               derecho para que el texto siempre quede sobre color sólido. -->
          <div v-reveal class="sp-shop-slide" :class="{ 'has-img': shopSlideImg, 'is-bare': !shopSlideImg && !custom.description }">
            <img v-if="shopSlideImg" class="sp-shop-slide-img" :src="shopSlideImg" alt="" fetchpriority="high" />
            <div class="sp-shop-slide-copy">
              <p class="sp-shop-eyebrow">
                <AppIcon :name="heroBadgeIcon || 'store'" :size="13" :stroke="2.25" /> {{ heroBadge }}
              </p>
              <h1 class="sp-hero-title sp-shop-title" :class="{ 'is-name': heroTitleIsName }" :style="heroTitleIsName ? nameFont : null">{{ titleSplit.head }} <mark class="sp-shop-mark">{{ titleSplit.last }}</mark></h1>
              <p v-if="custom.description" class="sp-hero-sub sp-shop-sub">{{ custom.description }}</p>
              <div class="sp-hero-ctas">
                <RouterLink v-if="showCatalog" class="sp-btn sp-hero-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
                <a v-if="showContact" class="sp-btn sp-hero-ghost" href="#contacto"><AppIcon name="message-circle" :size="16" /> Contáctanos</a>
              </div>
              <ul v-if="heroMeta.length" class="sp-hero-meta">
                <li v-for="m in heroMeta" :key="m.key" :class="m.state ? `sp-open is-${m.state}` : null"><span v-if="m.state" class="sp-live-dot" aria-hidden="true"></span><AppIcon v-else :name="m.icon" :size="14" /> {{ m.text }}</li>
              </ul>
            </div>
            <button type="button" class="sp-icon-btn sp-shop-share" :aria-label="copied ? 'Link copiado' : 'Compartir tienda'" :title="copied ? 'Link copiado' : 'Compartir'" @click="share">
              <AppIcon :name="copied ? 'check' : 'share-2'" :size="17" />
            </button>
          </div>
          <div class="sp-shop-side">
            <component
              :is="showCatalog ? 'RouterLink' : 'a'" v-reveal="120" class="sp-shop-promo"
              :class="{ 'has-img': shopPromoImgs[0] }"
              :to="showCatalog ? catalogTo : null" :href="showCatalog ? null : '#contacto'"
            >
              <span class="sp-shop-promo-copy">
                <span class="sp-shop-promo-eyebrow"><AppIcon name="percent" :size="12" :stroke="2.5" /> {{ shopPromoEyebrow }}</span>
                <strong>{{ showCatalog ? 'Explorá el catálogo' : 'Escribinos tu consulta' }}</strong>
                <span class="sp-shop-promo-go">{{ showCatalog ? 'Ver ahora' : 'Contáctanos' }} <AppIcon name="arrow-right" :size="13" /></span>
              </span>
              <span v-if="shopPromoImgs[0]" class="sp-shop-promo-media" aria-hidden="true">
                <img :src="shopPromoImgs[0]" alt="" loading="lazy" />
              </span>
            </component>
            <a v-reveal="200" class="sp-shop-promo alt" :class="{ 'has-img': shopPromoImgs[1] }" :href="hasAbout ? '#nosotros' : '#contacto'">
              <span class="sp-shop-promo-copy">
                <span class="sp-shop-promo-eyebrow"><AppIcon :name="location ? 'map-pin' : 'store'" :size="12" :stroke="2.5" /> {{ location || shopName }}</span>
                <strong>{{ hasAbout ? aboutTitle : 'Hablemos de lo que buscás' }}</strong>
                <span class="sp-shop-promo-go">{{ hasAbout ? 'Conócenos' : 'Contacto' }} <AppIcon name="arrow-right" :size="13" /></span>
              </span>
              <span v-if="shopPromoImgs[1]" class="sp-shop-promo-media" aria-hidden="true">
                <img :src="shopPromoImgs[1]" alt="" loading="lazy" />
              </span>
            </a>
          </div>
        </template>
        <template v-else-if="tpl === 'classic'">
          <!-- Clásico: hero partido — copy alineado a la izquierda y una
               placa de presentación (foto o logo) con chips flotantes de
               datos reales del negocio. -->
          <div class="sp-cl-copy">
            <p v-reveal class="sp-hero-badge">
              <AppIcon v-if="heroBadgeIcon" :name="heroBadgeIcon" :size="13" />
              {{ heroBadge }}
            </p>
            <h1 v-reveal="120" class="sp-hero-title" :class="{ 'is-name': heroTitleIsName }" :style="heroTitleIsName ? nameFont : null">{{ heroTitle }}</h1>
            <p v-if="custom.description" v-reveal="200" class="sp-hero-sub">{{ custom.description }}</p>
            <div v-reveal="280" class="sp-hero-ctas">
              <RouterLink v-if="showCatalog" class="sp-btn sp-hero-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
              <a v-if="showContact" class="sp-btn sp-hero-ghost" href="#contacto"><AppIcon name="message-circle" :size="16" /> Contáctanos</a>
              <button type="button" class="sp-icon-btn" :aria-label="copied ? 'Link copiado' : 'Compartir tienda'" :title="copied ? 'Link copiado' : 'Compartir'" @click="share">
                <AppIcon :name="copied ? 'check' : 'share-2'" :size="17" />
              </button>
            </div>
            <ul v-if="heroMeta.length" v-reveal="360" class="sp-hero-meta">
              <li v-for="m in heroMeta" :key="m.key" :class="m.state ? `sp-open is-${m.state}` : null"><span v-if="m.state" class="sp-live-dot" aria-hidden="true"></span><AppIcon v-else :name="m.icon" :size="14" /> {{ m.text }}</li>
            </ul>
          </div>
          <div v-reveal="140" class="sp-cl-art">
            <figure class="sp-cl-frame" :class="{ 'is-logo': !clImg }">
              <img v-if="clImg" :src="clImg" alt="" fetchpriority="high" />
              <img v-else-if="custom.logo" class="sp-cl-logo" :src="custom.logo" :alt="`Logo de ${shopName}`" />
              <span v-else class="sp-cl-initial" aria-hidden="true">{{ initial }}</span>
            </figure>
            <span class="sp-cl-chip c1"><span class="sp-cl-chip-ico"><AppIcon :name="clChipA.icon" :size="15" :stroke="2.25" /></span>{{ clChipA.text }}</span>
            <span class="sp-cl-chip c2"><span class="sp-cl-chip-ico"><AppIcon :name="clChipB.icon" :size="15" :stroke="2.25" /></span>{{ clChipB.text }}</span>
          </div>
        </template>
        <template v-else>
          <span v-reveal class="sp-ava">
            <img v-if="custom.logo" class="sp-logo lg" :src="custom.logo" :alt="`Logo de ${shopName}`" />
            <span v-else class="sp-mono lg" aria-hidden="true">{{ initial }}</span>
          </span>
          <p v-reveal="80" class="sp-hero-badge">
            <AppIcon v-if="heroBadgeIcon" :name="heroBadgeIcon" :size="13" />
            {{ heroBadge }}
          </p>
          <h1 v-reveal="160" class="sp-hero-title" :class="{ 'is-name': heroTitleIsName }" :style="heroTitleIsName ? nameFont : null"><template v-if="tpl === 'promo'">{{ titleSplit.head }} <mark class="sp-pr-mark">{{ titleSplit.last }}</mark></template><template v-else-if="tpl === 'street'">{{ titleSplit.head }} <mark class="sp-st-mark">{{ titleSplit.last }}</mark></template><template v-else-if="tpl === 'terminal'">{{ titleSplit.head }} <mark class="sp-tm-mark">{{ titleSplit.last }}</mark></template><template v-else>{{ heroTitle }}</template></h1>
          <p v-if="custom.description" v-reveal="240" class="sp-hero-sub">{{ custom.description }}</p>
          <div v-reveal="320" class="sp-hero-ctas">
            <a v-if="tpl === 'promo' && whatsappUrl" class="sp-btn sp-pr-wa" :href="whatsappUrl" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="18" /> Escribinos ahora</a>
            <RouterLink v-if="showCatalog" class="sp-btn sp-hero-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
            <a v-if="showContact" class="sp-btn sp-hero-ghost" href="#contacto"><AppIcon name="message-circle" :size="16" /> Contáctanos</a>
            <button type="button" class="sp-icon-btn" :aria-label="copied ? 'Link copiado' : 'Compartir tienda'" :title="copied ? 'Link copiado' : 'Compartir'" @click="share">
              <AppIcon :name="copied ? 'check' : 'share-2'" :size="17" />
            </button>
          </div>
          <ul v-if="heroMeta.length" v-reveal="400" class="sp-hero-meta">
            <li v-for="m in heroMeta" :key="m.key" :class="m.state ? `sp-open is-${m.state}` : null"><span v-if="m.state" class="sp-live-dot" aria-hidden="true"></span><AppIcon v-else :name="m.icon" :size="14" /> {{ m.text }}</li>
          </ul>
          <div v-if="tpl === 'promo'" class="sp-pr-seal" aria-hidden="true">
            <svg class="sp-pr-seal-ring" viewBox="0 0 200 200">
              <defs><path id="sp-pr-circle" d="M100,100 m-78,0 a78,78 0 1,1 156,0 a78,78 0 1,1 -156,0" /></defs>
              <text><textPath href="#sp-pr-circle" textLength="486" lengthAdjust="spacing">OFERTAS • NOVEDADES • CONSULTÁ YA • </textPath></text>
            </svg>
            <span class="sp-pr-seal-core"><AppIcon name="gift" :size="46" :stroke="1.75" /></span>
          </div>
        </template>
      </div>
      <!-- Cinta de marca de Perspectiva, Publicidad, Urbano y Terminal:
           marquee infinito (dos secuencias idénticas, el track se desplaza
           -50% en loop). Solo decoración. -->
      <div v-if="tpl === 'perspective' || tpl === 'promo' || tpl === 'street' || tpl === 'terminal'" class="sp-hero-marquee" aria-hidden="true">
        <div class="sp-hero-marquee-track">
          <span v-for="n in 2" :key="n" class="sp-hero-marquee-seq">
            <template v-for="(m, i) in marqueeItems" :key="i"><AppIcon :name="m.icon" :size="15" :stroke="2.25" /> {{ m.text }} <i></i></template>
          </span>
        </div>
      </div>
      <!-- Lookbook: pie de edición (regla + número + temporada), sin marquee. -->
      <div v-if="tpl === 'lookbook'" class="sp-container sp-lb-hero-foot" aria-hidden="true">
        <span>Edición Nº 01</span><i></i><span>{{ year }}</span>
        <span class="sp-lb-hero-foot-note">Colección de temporada</span>
      </div>
      <!-- Signature: línea de firma bajo el hero — dateline en mayúsculas
           grabadas a los bordes y el nombre del negocio manuscrito al
           centro, como la firma al pie de un documento. -->
      <div v-if="tpl === 'signature'" class="sp-container sp-sg-strip">
        <span class="sp-sg-strip-edge">Est. {{ year }}</span>
        <span class="sp-sg-strip-sign">{{ shopName }}</span>
        <span class="sp-sg-strip-edge">{{ location || 'Tienda online' }}</span>
      </div>
    </div>

    <!-- Tienda Pro y Boutique: departamentos reales del catálogo
         (categorías con productos, miniatura del primer producto y
         conteo). Sin catálogo se mantiene la fila de destacados del resto
         de los diseños. -->
    <div v-if="(tpl === 'shop' || tpl === 'boutique' || tpl === 'signature' || tpl === 'aurora') && shopDepts.length" class="sp-container">
      <div class="sp-shop-depts" :style="{ maxWidth: `${(shopDepts.length + (showCatalog ? 1 : 0)) * 156}px` }" aria-label="Departamentos del catálogo">
        <RouterLink v-for="d in shopDepts" :key="d.id" v-reveal class="sp-shop-dept" :to="deptTo(d.id)">
          <span class="sp-shop-dept-thumb">
            <img v-if="d.image" :src="d.image" alt="" loading="lazy" />
            <span v-else class="sp-shop-dept-initial" aria-hidden="true">{{ d.name.slice(0, 1) }}</span>
          </span>
          <span class="sp-shop-dept-name">{{ d.name }}</span>
          <span class="sp-shop-dept-count">{{ d.count }} {{ d.count === 1 ? 'producto' : 'productos' }}</span>
        </RouterLink>
        <RouterLink v-if="showCatalog" v-reveal="80" class="sp-shop-dept all" :to="catalogTo">
          <span class="sp-shop-dept-thumb"><AppIcon name="layout-grid" :size="22" /></span>
          <span class="sp-shop-dept-name">Ver todo</span>
          <span class="sp-shop-dept-count">Catálogo completo</span>
        </RouterLink>
      </div>
    </div>
    <div v-else-if="custom.show_highlights !== false" class="sp-container sp-highlights">
      <component
        :is="h.to ? 'RouterLink' : h.href ? 'a' : 'div'" v-for="(h, i) in highlights" :key="h.title"
        v-reveal="i * 90" class="sp-hl" :to="h.to" :href="h.href"
      >
        <span class="sp-hl-icon" aria-hidden="true"><AppIcon :name="h.icon" :size="22" /></span>
        <strong>{{ h.title }}</strong>
        <span class="sp-hl-text">{{ h.text }}</span>
      </component>
    </div>

    <!-- Tienda Pro, Lookbook, Cobre, Minimal y Boutique: vitrina de
         productos destacados en la portada (8 en marketplace/Minimal/
         Boutique, 4 pliegos en Lookbook y en la colección). -->
    <div v-if="(tpl === 'shop' || tpl === 'lookbook' || tpl === 'cobre' || tpl === 'minimal' || tpl === 'boutique' || tpl === 'signature' || tpl === 'aurora') && shopProducts.length" class="sp-container sp-shop-featured">
      <div class="sp-shop-featured-head">
        <div class="sp-shop-featured-copy">
          <p class="sp-shop-featured-eyebrow">{{ tpl === 'lookbook' ? 'Selección de la edición' : tpl === 'signature' ? 'Curaduría de autor' : tpl === 'aurora' ? 'Cielo despejado' : tpl === 'cobre' || tpl === 'minimal' || tpl === 'boutique' ? 'Nueva temporada' : 'Recién llegados' }}</p>
          <h2 class="sp-shop-featured-title">{{ tpl === 'lookbook' ? 'Pliegos destacados' : tpl === 'signature' ? 'La vitrina' : tpl === 'aurora' ? 'El observatorio' : tpl === 'cobre' || tpl === 'boutique' ? 'La colección' : tpl === 'minimal' ? 'Selección' : 'Productos destacados' }}</h2>
        </div>
        <RouterLink class="sp-shop-viewall" :to="catalogTo">{{ tpl === 'lookbook' ? 'Ver índice completo' : tpl === 'cobre' ? 'Ver todo' : tpl === 'signature' ? 'Ver el catálogo completo' : tpl === 'boutique' ? 'Ver toda la colección' : 'Ver todo el catálogo' }} <AppIcon name="arrow-right" :size="14" class="sp-arrow" /></RouterLink>
      </div>
      <div class="sp-shop-featured-grid">
        <article
          v-for="(p, i) in shopProducts" :key="p.id" v-reveal="(i % 4) * 80"
          class="sp-card" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
          @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
        >
          <div class="sp-card-img">
            <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
            <span v-else class="sp-card-placeholder"><AppIcon name="package" :size="28" /></span>
            <span class="sp-card-quick" aria-hidden="true"><AppIcon name="eye" :size="15" /> Ver producto</span>
            <span v-if="isNewProduct(p)" class="sp-card-flag">Nuevo</span>
            <span v-if="productOffer(p) != null" class="sp-card-flag offer">-{{ offerPct(p) }}%</span>
          </div>
          <div class="sp-card-body">
            <p v-if="shopCatOf(p) || shopBrandOf(p)" class="sp-card-eyebrow">
              <span v-if="shopCatOf(p)">{{ shopCatOf(p) }}</span>
              <i v-if="shopCatOf(p) && shopBrandOf(p)" aria-hidden="true"></i>
              <span v-if="shopBrandOf(p)">{{ shopBrandOf(p) }}</span>
            </p>
            <h3 class="sp-card-name">{{ p.name }}</h3>
            <div class="sp-card-foot">
              <span class="sp-card-price"><s v-if="productOffer(p) != null" class="sp-price-old">{{ formatARS(p.price) }}</s>{{ formatARS(effectivePrice(p)) }}</span>
              <span class="sp-card-go" aria-hidden="true">Ver más <AppIcon name="arrow-right" :size="16" /></span>
            </div>
          </div>
        </article>
      </div>
    </div>
  </section>

  <!-- ===== Sobre nosotros: contenido a la izquierda con la foto decorativa
       al costado; la tarjeta de trayectoria/misión baja a una banda a todo
       lo ancho para que no quede flotando contra el texto ===== -->
  <section v-if="hasAbout" id="nosotros" class="sp-about" :style="{ order: sectionPos.about }" aria-labelledby="sp-about-title">
    <div class="sp-container sp-about-grid" :class="{ 'no-side': !decorAbout }">
      <div v-reveal class="sp-about-info">
        <p class="sp-eyebrow">Conócenos</p>
        <h2 id="sp-about-title" class="sp-about-heading">
          <span class="sp-about-heading-icon" aria-hidden="true"><AppIcon name="store" :size="26" /></span>
          {{ aboutTitle }}
        </h2>
        <p v-if="custom.about_text" class="sp-about-text">{{ custom.about_text }}</p>
        <ul v-if="aboutSpecialties.length" class="sp-about-list">
          <li v-for="s in aboutSpecialties" :key="s"><AppIcon name="check" :size="16" /> <span>{{ s }}</span></li>
        </ul>
      </div>
      <div v-if="decorAbout" class="sp-about-side">
        <figure v-reveal="140" class="sp-about-photo">
          <img :src="decorAbout.url" :alt="`Imagen de ${shopName}`" loading="lazy" />
        </figure>
      </div>
      <div v-if="hasAboutCard" v-reveal="140" class="sp-about-card">
        <p v-if="custom.about_years" class="sp-about-years">
          <strong>+{{ custom.about_years }}</strong>
          <span>años de trayectoria</span>
        </p>
        <blockquote v-if="custom.about_mission" class="sp-about-mission">
          <span class="sp-about-mission-label">Nuestra misión</span>
          {{ custom.about_mission }}
        </blockquote>
      </div>
    </div>
  </section>

  <!-- ===== Banda decorativa: la imagen va junto a un texto de invitación
       con CTAs (nunca una foto suelta a todo lo ancho); en móvil la foto
       se oculta y queda solo el bloque de texto ===== -->
  <section v-if="decorBand" class="sp-showcase" :style="{ order: sectionPos.gallery }">
    <div class="sp-container sp-showcase-grid">
      <figure v-reveal class="sp-showcase-frame" aria-hidden="true">
        <img :src="decorBand.url" alt="" loading="lazy" />
      </figure>
      <div v-reveal="120" class="sp-showcase-copy">
        <p class="sp-eyebrow">{{ shopName }}</p>
        <h2 class="sp-showcase-title">{{ showcaseTitle }}</h2>
        <p v-if="showcaseText" class="sp-showcase-text">{{ showcaseText }}</p>
        <div class="sp-showcase-ctas">
          <RouterLink v-if="showCatalog" class="sp-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
          <a v-if="showContact" class="sp-btn ghost" href="#contacto"><AppIcon name="message-circle" :size="16" /> Contáctanos</a>
        </div>
      </div>
    </div>
  </section>

  <!-- ===== Galería ===== -->
  <section v-if="showGallery" id="galeria" class="sp-gallery" :style="{ order: sectionPos.gallery }" aria-labelledby="sp-gallery-title">
    <div class="sp-container">
      <h2 id="sp-gallery-title" v-reveal class="sp-section-title">Galería</h2>
      <div class="sp-gallery-grid">
        <button
          v-for="(img, i) in gallery" :key="img.id" v-reveal="(i % 4) * 70"
          type="button" class="sp-gallery-item"
          :aria-label="`Ver imagen ${i + 1} en grande`"
          @click="openLightbox(i)"
        >
          <img :src="img.url" :alt="`Imagen ${i + 1} de la galería de ${shopName}`" loading="lazy" />
        </button>
      </div>
    </div>
  </section>

  <!-- ===== Qué ofrecemos: tarjetas de servicios/ventajas con ícono ===== -->
  <section v-if="showServices" class="sp-services" :style="{ order: sectionPos.services }" aria-labelledby="sp-services-title">
    <div class="sp-container">
      <p v-if="servicesEyebrow" class="sp-eyebrow">{{ servicesEyebrow }}</p>
      <h2 id="sp-services-title" v-reveal class="sp-section-title">{{ servicesTitle }}</h2>
      <div class="sp-services-grid">
        <article v-for="(s, i) in services" :key="i" v-reveal="(i % 3) * 80" class="sp-service">
          <span class="sp-service-icon" aria-hidden="true"><AppIcon :name="serviceIcon(s.icon)" :size="22" /></span>
          <strong>{{ s.title }}</strong>
          <p v-if="s.text">{{ s.text }}</p>
        </article>
      </div>
    </div>
  </section>

  <!-- ===== Tus números: banda de cifras destacadas ===== -->
  <section v-if="showStats" class="sp-stats" :style="{ order: sectionPos.stats }" aria-label="Cifras del negocio">
    <div class="sp-container sp-stats-grid">
      <div v-for="(s, i) in stats" :key="i" v-reveal="i * 80" class="sp-stat">
        <strong>{{ s.value }}</strong>
        <span>{{ s.label }}</span>
      </div>
    </div>
  </section>

  <!-- ===== Testimonios ===== -->
  <section v-if="showTestimonials" class="sp-testimonials" :style="{ order: sectionPos.testimonials }" aria-labelledby="sp-testimonials-title">
    <div class="sp-container">
      <p v-if="testimonialsEyebrow" class="sp-eyebrow">{{ testimonialsEyebrow }}</p>
      <h2 id="sp-testimonials-title" v-reveal class="sp-section-title">{{ testimonialsTitle }}</h2>
      <div ref="testiGrid" class="sp-testimonials-grid">
        <figure v-for="(t, i) in testimonials" :key="i" v-reveal="(i % 3) * 80" class="sp-testimonial">
          <span class="sp-testimonial-quote" aria-hidden="true"><AppIcon name="quote" :size="20" /></span>
          <blockquote class="sp-testimonial-text">{{ t.text }}</blockquote>
          <figcaption class="sp-testimonial-by">
            <strong>{{ t.name }}</strong>
            <span v-if="t.detail">{{ t.detail }}</span>
          </figcaption>
        </figure>
      </div>
    </div>
  </section>

  <!-- ===== Preguntas frecuentes: respuestas desplegables ===== -->
  <section v-if="showFaqs" class="sp-faq" :style="{ order: sectionPos.faq }" aria-labelledby="sp-faq-title">
    <div class="sp-container sp-faq-wrap">
      <div class="sp-faq-intro">
        <p v-if="faqEyebrow" class="sp-eyebrow">{{ faqEyebrow }}</p>
        <h2 id="sp-faq-title" v-reveal class="sp-section-title">{{ faqsTitle }}</h2>
        <p v-if="tpl === 'shop'" class="sp-faq-note">
          ¿No encontrás lo que buscás?
          <a v-if="showContact" href="#contacto">Escribinos</a><template v-else>Consultanos por WhatsApp.</template>
        </p>
      </div>
      <div class="sp-faq-list">
        <details v-for="(f, i) in faqs" :key="i" v-reveal="(i % 4) * 60" class="sp-faq-item">
          <summary>{{ f.q }}<span class="sp-faq-caret" aria-hidden="true"><AppIcon name="chevron-down" :size="16" /></span></summary>
          <p class="sp-faq-answer">{{ f.a }}</p>
        </details>
      </div>
    </div>
  </section>

  <!-- ===== Llamado a la acción: banda de cierre de la portada ===== -->
  <section v-if="showCta" class="sp-cta" :style="{ order: sectionPos.cta }">
    <div class="sp-container sp-cta-inner">
      <h2 v-reveal class="sp-cta-title">{{ ctaTitle }}</h2>
      <p v-if="custom.cta_text" v-reveal="80" class="sp-cta-text">{{ custom.cta_text }}</p>
      <component
        v-if="ctaLink" :is="ctaLink.to ? 'RouterLink' : 'a'" v-reveal="160" class="sp-btn sp-cta-btn"
        :to="ctaLink.to" :href="ctaLink.href"
        :target="ctaLink.external ? '_blank' : null" :rel="ctaLink.external ? 'noopener' : null"
      >
        {{ ctaLabel }} <AppIcon name="arrow-right" :size="16" class="sp-arrow" />
      </component>
    </div>
  </section>

  <!-- ===== Contáctanos (formulario + canales + mapa de ubicación) ===== -->
  <section v-if="showContact" id="contacto" class="sp-contact" :style="{ order: 99 }" aria-labelledby="sp-contact-title">
    <div class="sp-container">
      <div class="sp-contact-grid">
        <div v-reveal class="sp-contact-info">
          <p class="sp-eyebrow">Contacto</p>
          <h2 id="sp-contact-title" class="sp-contact-title">Contáctanos</h2>
          <p class="sp-contact-sub">Escribinos tu consulta y te respondemos a la brevedad.</p>
          <p v-if="mapAddress" class="sp-map-address"><AppIcon name="map-pin" :size="14" /> {{ mapAddress }}</p>
          <ul v-if="showHours" class="sp-contact-hours">
            <li v-for="(h, i) in contactHours" :key="i">
              <AppIcon name="clock" :size="14" aria-hidden="true" />
              <span>{{ h.label }}</span>
              <strong>{{ h.value }}</strong>
            </li>
          </ul>
          <div v-if="hasContactChannels" class="sp-contact-channels">
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
          <figure v-if="decorContact" class="sp-contact-photo" aria-hidden="true">
            <img :src="decorContact.url" alt="" loading="lazy" />
          </figure>
        </div>
        <form v-reveal="180" class="sp-form" novalidate @submit.prevent="submitContact">
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
                <span v-if="contactStatus === 'loading'" class="sp-spinner" aria-hidden="true"></span>
                <AppIcon v-else name="mail" :size="16" />
                Enviar mensaje
              </button>
              <span class="sp-form-note"><AppIcon name="lock" :size="13" aria-hidden="true" /> Tus datos solo se usan para responderte.</span>
            </div>
          </template>
        </form>
      </div>
      <div v-if="mapUrl" v-reveal="120" class="sp-map-frame">
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

  <!-- ===== Galería: visor de imagen ===== -->
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
