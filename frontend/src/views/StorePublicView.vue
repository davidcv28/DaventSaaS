<script setup>
import { ref, reactive, computed, inject, onMounted, onBeforeUnmount } from 'vue'
import { storesApi } from '../api/stores.api.js'
import { extractApiError } from '../api/http.js'
import { storeHostSlug } from '../config/env.js'
import { formatARS } from '../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct } from '../api/catalog.api.js'
import AppIcon from '../components/AppIcon.vue'
import { vReveal } from '../directives/reveal.js'

// Página de inicio de la web pública: presentación (hero), carrusel de
// destacados (premium), Sobre nosotros, Galería y Contáctanos. El catálogo
// es una página aparte (StoreCatalogView) y la tienda la resuelve
// StorePublicLayout (inject 'storePage').
const ctx = inject('storePage')
const { slug, custom, shopName, nameFont, initial, location, pageTemplate, hasAbout, showContact, showCatalog, hasDesignAdvanced } = ctx
// Diseño activo de la portada ('classic' | 'editorial' | 'perspective' |
// 'promo' | 'catalog'): la estructura del hero se reordena por CSS
// (grid-areas); solo la cinta de marca de 'perspective'/'promo' es markup extra.
const tpl = pageTemplate

const year = new Date().getFullYear()
const marqueeItems = computed(() => (tpl.value === 'promo'
  ? [{ icon: 'flame', text: 'Ofertas' }, { icon: 'sparkles', text: 'Novedades' }, { icon: 'percent', text: 'Promos' }, { icon: 'zap', text: 'Consultá ya' }]
  : [{ icon: 'zap', text: shopName.value }, { icon: 'star', text: heroTitle.value }, { icon: 'map-pin', text: location.value || 'Tienda online' }]))
const titleSplit = computed(() => {
  const words = heroTitle.value.split(/\s+/)
  return words.length > 1 ? { head: words.slice(0, -1).join(' '), last: words[words.length - 1] } : { head: '', last: heroTitle.value }
})

const copied = ref(false)
const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const catalogToQuery = (query) => ({ ...catalogTo.value, query })

// Imagen de portada (premium): fondo del hero. Sin diseño avanzado no se usa
// aunque haya quedado una guardada.
const cover = computed(() => (hasDesignAdvanced.value ? custom.value.cover || '' : ''))

// --- Diseño "Catálogo exclusivo": vitrina estilo marketplace. Carga el
// catálogo (más recientes primero) para armar categorías, novedades y marcas. ---
const isCatalogTpl = computed(() => tpl.value === 'catalog')
const shelf = ref({ categories: [], brands: [], products: [] })
const shelfStatus = ref('idle') // idle | loading | success | error
const shelfProducts = computed(() => shelf.value.products.slice(0, 8))
const shelfCategories = computed(() => shelf.value.categories
  .map((c) => {
    const items = shelf.value.products.filter((p) => p.category === c.id)
    return { ...c, count: items.length, image: items.find((p) => p.image)?.image || '' }
  })
  .filter((c) => c.count)
  .slice(0, 6))
const shelfBrands = computed(() => shelf.value.brands.slice(0, 8))
const brandNameOf = (p) => shelf.value.brands.find((b) => b.id === p.brand)?.name || ''
const categoryNameOf = (p) => shelf.value.categories.find((c) => c.id === p.category)?.name || ''
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })
const trustItems = computed(() => [
  { icon: 'shield-check', title: 'Compra segura', text: 'Información clara y precios sin sorpresas.' },
  { icon: 'message-circle', title: 'Atención directa', text: whatsappUrl.value ? 'Respondemos por WhatsApp.' : 'Escribinos y te respondemos.' },
  { icon: 'package', title: shelf.value.products.length ? `${shelf.value.products.length} productos` : 'Catálogo online', text: 'Siempre actualizado por el comercio.' },
  { icon: 'users', title: 'Atención personalizada', text: 'Te acompañamos en cada compra.' }
])
// Tiles laterales del banner: imágenes decorativas si existen, si no tarjetas de acento.
const sideTiles = computed(() => {
  const tiles = decor.value.slice(0, 2).map((img) => ({ key: img.id, image: img.url }))
  const fallback = [
    { key: 'new', icon: 'sparkles', title: 'Novedades', text: 'Lo último que llegó', to: catalogToQuery({ sort: 'recent' }) },
    { key: 'wa', icon: 'whatsapp', title: 'Consultanos', text: 'Respondemos al instante', href: whatsappUrl.value || '#contacto' }
  ]
  return [...tiles, ...fallback].slice(0, 2)
})
async function loadShelf() {
  shelfStatus.value = 'loading'
  try {
    shelf.value = await storesApi.publicCatalog(slug.value, { sort: 'recent' })
    shelfStatus.value = 'success'
  } catch {
    shelfStatus.value = 'error'
  }
}

// --- Presentación (hero): banda de acento con la identidad del negocio.
// Si el dueño cargó un titular, el titular es el h1 y el nombre viaja en el
// badge; si no, el h1 es el nombre y el badge muestra la ubicación. ---
const heroTitleIsName = computed(() => !custom.value.headline?.trim())
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value)
// Sin catálogo la web es una vidriera: el badge de fallback es "Sitio oficial".
const heroBadge = computed(() => (heroTitleIsName.value ? (location.value || (showCatalog.value ? 'Catálogo online' : 'Sitio oficial')) : shopName.value))
const heroBadgeIcon = computed(() => (heroTitleIsName.value ? (location.value ? 'map-pin' : 'store') : ''))
const heroMeta = computed(() => {
  const items = []
  if (!heroTitleIsName.value && location.value) items.push({ icon: 'map-pin', text: location.value })
  if (custom.value.about_years) items.push({ icon: 'clock', text: `+${custom.value.about_years} años de trayectoria` })
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
// contacto. En "Catálogo exclusivo" alimentan los tiles laterales del
// banner (sideTiles). En móvil se ocultan por CSS.
const decor = computed(() => (hasDesignAdvanced.value ? (custom.value.decor || []).slice(0, 3) : []))
const decorAbout = computed(() => (!isCatalogTpl.value && hasAbout.value ? decor.value[0] || null : null))
const decorPool = computed(() => decor.value.slice(decorAbout.value ? 1 : 0))
const decorBand = computed(() => (isCatalogTpl.value ? null : decorPool.value[0] || null))
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

// Mapa de ubicación (beneficio has_location_map, Estándar y Premium): el
// backend devuelve location_address ya armada para geocodificar, o null si
// el dueño lo apagó en Diseño web.
const mapAddress = computed(() => ctx.store.value?.location_address || '')
const mapUrl = computed(() => (
  mapAddress.value
    ? `https://maps.google.com/maps?q=${encodeURIComponent(mapAddress.value)}&output=embed&z=16`
    : ''
))

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
  if (isCatalogTpl.value && showCatalog.value) loadShelf()
  window.addEventListener('keydown', onKey)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
<div class="sp-page-root">
  <!-- ===== Presentación (portada de la empresa) ===== -->
  <section class="sp-hero">
    <!-- ===== Diseño Catálogo exclusivo: vitrina estilo marketplace ===== -->
    <template v-if="isCatalogTpl">
      <div class="sp-container sp-cx-hero">
        <div class="sp-cx-banner" :class="{ 'has-cover': cover }">
          <img v-if="cover" class="sp-cx-banner-img" :src="cover" alt="" fetchpriority="high" />
          <span v-else class="sp-cx-banner-art" aria-hidden="true"><AppIcon name="package" :size="120" :stroke="1" /></span>
          <div class="sp-cx-banner-copy">
            <p v-reveal class="sp-cx-kicker"><AppIcon v-if="heroBadgeIcon" :name="heroBadgeIcon" :size="13" /> {{ heroBadge }}</p>
            <h1 v-reveal="80" class="sp-cx-title" :class="{ 'is-name': heroTitleIsName }" :style="heroTitleIsName ? nameFont : null">{{ heroTitle }}</h1>
            <p v-if="custom.description" v-reveal="160" class="sp-cx-sub">{{ custom.description }}</p>
            <div v-reveal="240" class="sp-cx-ctas">
              <RouterLink v-if="showCatalog" class="sp-btn sp-cx-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
              <a v-if="showContact" class="sp-btn sp-cx-ghost" href="#contacto"><AppIcon name="message-circle" :size="16" /> Contáctanos</a>
              <button type="button" class="sp-icon-btn" :aria-label="copied ? 'Link copiado' : 'Compartir tienda'" :title="copied ? 'Link copiado' : 'Compartir'" @click="share">
                <AppIcon :name="copied ? 'check' : 'share-2'" :size="17" />
              </button>
            </div>
            <span v-if="custom.logo" class="sp-cx-logo"><img class="sp-logo lg" :src="custom.logo" :alt="`Logo de ${shopName}`" /></span>
          </div>
        </div>
        <div class="sp-cx-side">
          <component
            :is="t.to ? 'RouterLink' : t.href ? 'a' : 'div'" v-for="(t, i) in sideTiles" :key="t.key" v-reveal="i * 100"
            class="sp-cx-tile" :class="{ 'has-img': t.image }" :to="t.image ? catalogTo : t.to" :href="t.href"
          >
            <img v-if="t.image" :src="t.image" alt="" loading="lazy" />
            <template v-else>
              <span class="sp-cx-tile-icon" aria-hidden="true"><AppIcon :name="t.icon" :size="22" /></span>
              <strong>{{ t.title }}</strong>
              <span>{{ t.text }}</span>
            </template>
          </component>
        </div>
      </div>

      <div class="sp-container">
        <ul class="sp-cx-trust">
          <li v-for="(t, i) in trustItems" :key="t.title" v-reveal="i * 70">
            <span class="sp-cx-trust-icon" aria-hidden="true"><AppIcon :name="t.icon" :size="20" /></span>
            <span><strong>{{ t.title }}</strong><small>{{ t.text }}</small></span>
          </li>
        </ul>
      </div>

      <div v-if="showCatalog && shelfCategories.length" class="sp-container sp-cx-block">
        <header v-reveal class="sp-cx-head">
          <h2 class="sp-cx-h2">Comprá por categoría</h2>
        </header>
        <div class="sp-cx-cats">
          <RouterLink v-for="(c, i) in shelfCategories" :key="c.id" v-reveal="(i % 6) * 60" class="sp-cx-cat" :to="catalogToQuery({ category: c.id })">
            <span class="sp-cx-cat-img">
              <img v-if="c.image" :src="c.image" :alt="c.name" loading="lazy" />
              <AppIcon v-else name="layout-grid" :size="26" />
            </span>
            <strong>{{ c.name }}</strong>
            <small>{{ c.count }} {{ c.count === 1 ? 'producto' : 'productos' }}</small>
          </RouterLink>
        </div>
      </div>

      <div v-if="showCatalog && (shelfProducts.length || shelfStatus === 'loading')" class="sp-container sp-cx-block">
        <header v-reveal class="sp-cx-head">
          <h2 class="sp-cx-h2">Novedades</h2>
          <RouterLink class="sp-cx-more" :to="catalogToQuery({ sort: 'recent' })">Ver todo <AppIcon name="arrow-right" :size="15" /></RouterLink>
        </header>
        <div v-if="shelfStatus === 'loading'" class="sp-cx-grid" aria-busy="true">
          <div v-for="n in 4" :key="n" class="sp-cx-card sp-skeleton" aria-hidden="true"><div class="sp-cx-card-img"></div><div class="sp-cx-card-body"><span class="sp-sk-line"></span><span class="sp-sk-line short"></span></div></div>
        </div>
        <div v-else class="sp-cx-grid">
          <RouterLink v-for="(p, i) in shelfProducts" :key="p.id" v-reveal="(i % 4) * 70" class="sp-cx-card" :to="productTo(p)">
            <span class="sp-cx-card-img">
              <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
              <AppIcon v-else name="package" :size="30" />
              <span v-if="isNewProduct(p)" class="sp-cx-flag">Nuevo</span>
              <span v-if="productOffer(p) != null" class="sp-cx-flag offer">-{{ offerPct(p) }}%</span>
            </span>
            <span class="sp-cx-card-body">
              <small v-if="categoryNameOf(p) || brandNameOf(p)" class="sp-cx-card-eyebrow">{{ brandNameOf(p) || categoryNameOf(p) }}</small>
              <span class="sp-cx-card-name">{{ p.name }}</span>
              <span class="sp-cx-card-price"><s v-if="productOffer(p) != null" class="sp-price-old">{{ formatARS(p.price) }}</s>{{ formatARS(effectivePrice(p)) }}</span>
            </span>
          </RouterLink>
        </div>
      </div>

      <div v-if="showCatalog && shelfBrands.length" class="sp-container sp-cx-block">
        <header v-reveal class="sp-cx-head"><h2 class="sp-cx-h2">Marcas</h2></header>
        <ul class="sp-cx-brands">
          <li v-for="(b, i) in shelfBrands" :key="b.id" v-reveal="(i % 8) * 40">
            <RouterLink :to="catalogToQuery({ brand: b.id })"><AppIcon name="tag" :size="14" /> {{ b.name }}</RouterLink>
          </li>
        </ul>
      </div>
    </template>

    <template v-else>
    <div class="sp-hero-band" :class="{ 'has-cover': cover }">
      <div v-if="cover && tpl !== 'editorial'" class="sp-hero-cover" aria-hidden="true">
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
        <template v-if="tpl === 'editorial'">
          <span class="sp-ed-letter">{{ initial }}</span>
        </template>
        <template v-else-if="tpl === 'perspective'">
          <span class="sp-px-floor"></span>
          <span class="sp-px-plane p1"></span>
          <span class="sp-px-plane p2"></span>
        </template>
        <template v-else-if="tpl === 'promo'">
          <span class="sp-pr-burst"></span>
          <span class="sp-pr-spark s1"><AppIcon name="sparkles" :size="30" :stroke="2" /></span>
          <span class="sp-pr-spark s2"><AppIcon name="star" :size="22" :stroke="2" /></span>
          <span class="sp-pr-spark s3"><AppIcon name="zap" :size="26" :stroke="2" /></span>
        </template>
      </div>
      <div v-if="tpl === 'editorial'" class="sp-container sp-ed-masthead" aria-hidden="true">
        <span>Nº 01</span><i></i><span>Edición {{ year }}</span><i></i><span>{{ location || (showCatalog ? 'Catálogo' : 'Sitio oficial') }}</span>
      </div>
      <div class="sp-container sp-hero-inner">
        <figure v-if="cover && tpl === 'editorial'" v-reveal="120" class="sp-ed-cover">
          <img :src="cover" alt="" fetchpriority="high" />
        </figure>
        <span v-if="tpl === 'promo'" class="sp-pr-tag"><AppIcon name="megaphone" :size="15" :stroke="2.25" /> ¡Novedad!</span>
        <span v-reveal class="sp-ava">
          <img v-if="custom.logo" class="sp-logo lg" :src="custom.logo" :alt="`Logo de ${shopName}`" />
          <span v-else class="sp-mono lg" aria-hidden="true">{{ initial }}</span>
        </span>
        <p v-reveal="80" class="sp-hero-badge">
          <AppIcon v-if="heroBadgeIcon" :name="heroBadgeIcon" :size="13" />
          {{ heroBadge }}
        </p>
        <h1 v-reveal="160" class="sp-hero-title" :class="{ 'is-name': heroTitleIsName }" :style="heroTitleIsName ? nameFont : null"><template v-if="tpl === 'promo'">{{ titleSplit.head }} <mark class="sp-pr-mark">{{ titleSplit.last }}</mark></template><template v-else>{{ heroTitle }}</template></h1>
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
          <li v-for="m in heroMeta" :key="m.text"><AppIcon :name="m.icon" :size="14" /> {{ m.text }}</li>
        </ul>
        <div v-if="tpl === 'promo'" class="sp-pr-seal" aria-hidden="true">
          <svg class="sp-pr-seal-ring" viewBox="0 0 200 200">
            <defs><path id="sp-pr-circle" d="M100,100 m-78,0 a78,78 0 1,1 156,0 a78,78 0 1,1 -156,0" /></defs>
            <text><textPath href="#sp-pr-circle" textLength="486" lengthAdjust="spacing">OFERTAS • NOVEDADES • CONSULTÁ YA • </textPath></text>
          </svg>
          <span class="sp-pr-seal-core"><AppIcon name="gift" :size="46" :stroke="1.75" /></span>
        </div>
      </div>
      <!-- Cinta de marca de Perspectiva y Publicidad: marquee infinito (dos
           secuencias idénticas, el track se desplaza -50% en loop).
           Solo decoración. -->
      <div v-if="tpl === 'perspective' || tpl === 'promo'" class="sp-hero-marquee" aria-hidden="true">
        <div class="sp-hero-marquee-track">
          <span v-for="n in 2" :key="n" class="sp-hero-marquee-seq">
            <template v-for="(m, i) in marqueeItems" :key="i"><AppIcon :name="m.icon" :size="15" :stroke="2.25" /> {{ m.text }} <i></i></template>
          </span>
        </div>
      </div>
    </div>

    <div class="sp-container sp-highlights">
      <component
        :is="h.to ? 'RouterLink' : h.href ? 'a' : 'div'" v-for="(h, i) in highlights" :key="h.title"
        v-reveal="i * 90" class="sp-hl" :to="h.to" :href="h.href"
      >
        <span class="sp-hl-icon" aria-hidden="true"><AppIcon :name="h.icon" :size="22" /></span>
        <strong>{{ h.title }}</strong>
        <span class="sp-hl-text">{{ h.text }}</span>
      </component>
    </div>
    </template>
  </section>

  <!-- ===== Sobre nosotros: contenido a la izquierda, tarjeta destacada a la derecha ===== -->
  <section v-if="hasAbout" id="nosotros" class="sp-about" aria-labelledby="sp-about-title">
    <div class="sp-container sp-about-grid" :class="{ 'no-card': !hasAboutCard && !decorAbout }">
      <div v-reveal class="sp-about-info">
        <p class="sp-eyebrow">Conocenos</p>
        <h2 id="sp-about-title" class="sp-about-heading">
          <span class="sp-about-heading-icon" aria-hidden="true"><AppIcon name="store" :size="26" /></span>
          {{ aboutTitle }}
        </h2>
        <p v-if="custom.about_text" class="sp-about-text">{{ custom.about_text }}</p>
        <ul v-if="aboutSpecialties.length" class="sp-about-list">
          <li v-for="s in aboutSpecialties" :key="s"><AppIcon name="check" :size="16" /> <span>{{ s }}</span></li>
        </ul>
      </div>
      <div v-if="hasAboutCard || decorAbout" class="sp-about-side">
        <figure v-if="decorAbout" v-reveal="140" class="sp-about-photo">
          <img :src="decorAbout.url" :alt="`Imagen de ${shopName}`" loading="lazy" />
        </figure>
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
    </div>
  </section>

  <!-- ===== Banda decorativa: la imagen va junto a un texto de invitación
       con CTAs (nunca una foto suelta a todo lo ancho); en móvil la foto
       se oculta y queda solo el bloque de texto ===== -->
  <section v-if="decorBand" class="sp-showcase">
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
  <section v-if="showGallery" id="galeria" class="sp-gallery" aria-labelledby="sp-gallery-title">
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

  <!-- ===== Contáctanos (formulario + canales + mapa de ubicación) ===== -->
  <section v-if="showContact" id="contacto" class="sp-contact" aria-labelledby="sp-contact-title">
    <div class="sp-container">
      <div class="sp-contact-grid">
        <div v-reveal class="sp-contact-info">
          <p class="sp-eyebrow">Contacto</p>
          <h2 id="sp-contact-title" class="sp-contact-title">Contáctanos</h2>
          <p class="sp-contact-sub">Escribinos tu consulta y te respondemos a la brevedad.</p>
          <p v-if="mapAddress" class="sp-map-address"><AppIcon name="map-pin" :size="14" /> {{ mapAddress }}</p>
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
