<script setup>
// Bloque 'hero' de la familia StorePublicView: banda de acento con la
// identidad del negocio (titular, badge, CTAs, compartir, meta y el
// decor propio de cada diseño). Variante 'compact' reduce aires y apaga
// la decoración/secuencias secundarias via clase is-compact.
import { ref, computed, inject, onMounted, onBeforeUnmount } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { productOffer } from '../../../api/catalog.api.js'
import { openStatus } from '../../../utils/storeHours.js'
import AppIcon from '../../AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom, shopName, nameFont, initial, location, designTemplate, hasAbout, showContact, showCatalog, hasDesignAdvanced } = ctx
const tpl = designTemplate

const year = new Date().getFullYear()
const { featured: shopCatalog } = useFeaturedCatalog()

const copied = ref(false)
const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
// Página de servicios (site_templates): la landing enlaza al embudo de
// pedido por WhatsApp además del catálogo.
const servicesPage = ctx.showServices
const servicesTo = computed(() => ({ name: 'store-services', params: storeHostSlug ? {} : { slug: slug.value } }))
const whatsappUrl = computed(() => (custom.value.whatsapp ? `https://wa.me/${custom.value.whatsapp.replace(/\D/g, '')}` : ''))

// Imagen de portada (premium): fondo del hero. Sin diseño avanzado no se usa
// aunque haya quedado una guardada.
const cover = computed(() => (hasDesignAdvanced.value ? custom.value.cover || '' : ''))

// Imágenes del carrusel: alimentan placas y tarjetas del hero por diseño.
const shopImgs = computed(() => (custom.value.carousel || []).map((i) => i.url))
const shopSlideImg = computed(() => cover.value || shopImgs.value[0] || '')
const shopPromoImgs = computed(() => shopImgs.value.slice(cover.value ? 0 : 1, cover.value ? 2 : 3))
// Minimal: placa del hero — portada propia, primera imagen del carrusel o,
// en su defecto, el logo sobre el tile de la paleta.
const mnArtImg = computed(() => cover.value || shopImgs.value[0] || '')
const mnArtProduct = computed(() => shopCatalog.value.products.find((p) => p.image === mnArtImg.value))
// Barra de anuncio (strip de tinta del diseño editorial): nunca promete
// una oferta que la tienda no tiene cargada.
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
// sin repetir la misma imagen en ambas placas. Boutique, Signature y Aurora
// reusam el mismo pool para sus placas/pliegos.
const cbImgs = computed(() => [cover.value, ...shopImgs.value, ...shopCatalog.value.products.map((p) => p.image)].filter(Boolean))
const cbTileA = computed(() => cbImgs.value[0] || '')
const cbTileB = computed(() => cbImgs.value.find((u) => u !== cbTileA.value) || '')
const cbTileProduct = (img) => shopCatalog.value.products.find((p) => p.image === img)
const cbTileALabel = computed(() => cbTileProduct(cbTileA.value)?.name || shopName.value)
const cbTileBLabel = computed(() => cbTileProduct(cbTileB.value)?.name || 'Nueva temporada')
const btTileA = cbTileA
const btTileB = cbTileB
const btTileALabel = cbTileALabel
const sgTileA = cbTileA
const sgTileB = cbTileB
const sgTileALabel = cbTileALabel
const auSky = cbTileA
const auTileB = cbTileB
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

// --- Presentación (hero): banda de acento con la identidad del negocio.
// Si el dueño cargó un titular, el titular es el h1 y el nombre viaja en el
// badge; si no, el h1 es el nombre y el badge muestra la ubicación. ---
const heroTitleIsName = computed(() => !custom.value.headline?.trim())
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value)
const titleSplit = computed(() => {
  const words = heroTitle.value.split(/\s+/)
  return words.length > 1 ? { head: words.slice(0, -1).join(' '), last: words[words.length - 1] } : { head: '', last: heroTitle.value }
})
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
const marqueeItems = computed(() => (tpl.value === 'promo'
  ? [{ icon: 'flame', text: 'Ofertas' }, { icon: 'sparkles', text: 'Novedades' }, { icon: 'percent', text: 'Promos' }, { icon: 'zap', text: 'Consultá ya' }]
  : tpl.value === 'street'
    ? [{ icon: 'zap', text: shopName.value }, { icon: 'flame', text: 'Nueva colección' }, { icon: 'tag', text: heroTitle.value }, { icon: 'map-pin', text: location.value || 'Tienda online' }]
    : tpl.value === 'terminal'
      ? [{ icon: 'terminal', text: shopName.value }, { icon: 'check', text: 'status: ok' }, { icon: 'package', text: heroTitle.value }, { icon: 'map-pin', text: location.value || 'tienda online' }]
      : [{ icon: 'zap', text: shopName.value }, { icon: 'star', text: heroTitle.value }, { icon: 'map-pin', text: location.value || 'Tienda online' }]))
const aboutTitle = computed(() => custom.value.about_title?.trim() || 'Sobre nosotros')

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

onMounted(() => { clock = setInterval(() => { now.value = new Date() }, 60000) })
onBeforeUnmount(() => clearInterval(clock))
</script>

<template>
  <!-- ===== Presentación (portada de la empresa) ===== -->
  <section class="sp-hero" :class="{ 'is-compact': block?.variant === 'compact' }">
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
              <RouterLink v-if="servicesPage" class="sp-btn" :class="showCatalog ? 'sp-hero-ghost' : 'sp-hero-btn'" :to="servicesTo">Servicios <AppIcon name="wrench" :size="16" /></RouterLink>
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
              <RouterLink v-if="servicesPage" class="sp-btn" :class="showCatalog ? 'sp-hero-ghost' : 'sp-hero-btn'" :to="servicesTo">Servicios <AppIcon name="wrench" :size="16" /></RouterLink>
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
              <RouterLink v-if="servicesPage" class="sp-btn" :class="showCatalog ? 'sp-hero-ghost' : 'sp-hero-btn'" :to="servicesTo">Servicios <AppIcon name="wrench" :size="16" /></RouterLink>
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
              <RouterLink v-if="servicesPage" class="sp-btn" :class="showCatalog ? 'sp-hero-ghost' : 'sp-hero-btn'" :to="servicesTo">Servicios <AppIcon name="wrench" :size="16" /></RouterLink>
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
              <RouterLink v-if="servicesPage" class="sp-btn" :class="showCatalog ? 'sp-hero-ghost' : 'sp-hero-btn'" :to="servicesTo">Servicios <AppIcon name="wrench" :size="16" /></RouterLink>
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
                  <RouterLink v-if="servicesPage" class="sp-btn" :class="showCatalog ? 'sp-hero-ghost' : 'sp-hero-btn'" :to="servicesTo">Servicios <AppIcon name="wrench" :size="16" /></RouterLink>
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
                <RouterLink v-if="servicesPage" class="sp-btn" :class="showCatalog ? 'sp-hero-ghost' : 'sp-hero-btn'" :to="servicesTo">Servicios <AppIcon name="wrench" :size="16" /></RouterLink>
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
              <RouterLink v-if="servicesPage" class="sp-btn" :class="showCatalog ? 'sp-hero-ghost' : 'sp-hero-btn'" :to="servicesTo">Servicios <AppIcon name="wrench" :size="16" /></RouterLink>
              <a v-if="showContact" class="sp-btn sp-hero-ghost" href="#contacto"><AppIcon name="message-circle" :size="16" /> Contáctanos</a>
              <button type="button" class="sp-icon-btn" :aria-label="copied ? 'Link copiado' : 'Compartir tienda'" :title="copied ? 'Link copiado' : 'Compartir'" @click="share">
                <AppIcon :name="copied ? 'check' : 'share-2'" :size="17" />
              </button>
            </div>
          </div>
          <div v-reveal="140" class="sp-cl-art">
            <figure class="sp-cl-frame" :class="{ 'is-logo': !clImg }">
              <img v-if="clImg" :src="clImg" alt="" fetchpriority="high" />
              <img v-else-if="custom.logo" class="sp-cl-logo" :src="custom.logo" :alt="`Logo de ${shopName}`" />
              <span v-else class="sp-cl-initial" aria-hidden="true">{{ initial }}</span>
            </figure>
            <span class="sp-cl-chip c1"><span class="sp-cl-chip-ico"><AppIcon :name="clChipA.icon" :size="15" :stroke="2.25" /></span>{{ clChipA.text }}</span>
            <span class="sp-cl-chip c2"><span class="sp-cl-chip-ico"><AppIcon :name="clChipB.icon" :size="15" :stroke="2.5" /></span>{{ clChipB.text }}</span>
          </div>
          <!-- Barra de confianza bajo el hero: estado, ubicación y WhatsApp
               a todo el ancho de la banda (una columna en pantallas chicas). -->
          <ul v-if="heroMeta.length || whatsappUrl" v-reveal="360" class="sp-cl-trust">
            <li v-for="m in heroMeta" :key="m.key" :class="m.state ? `sp-open is-${m.state}` : null"><span v-if="m.state" class="sp-live-dot" aria-hidden="true"></span><AppIcon v-else :name="m.icon" :size="14" /> {{ m.text }}</li>
            <li v-if="whatsappUrl" class="sp-cl-trust-wa"><a :href="whatsappUrl" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="14" /> WhatsApp</a></li>
          </ul>
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
            <RouterLink v-if="servicesPage" class="sp-btn" :class="showCatalog ? 'sp-hero-ghost' : 'sp-hero-btn'" :to="servicesTo">Servicios <AppIcon name="wrench" :size="16" /></RouterLink>
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
  </section>
</template>
