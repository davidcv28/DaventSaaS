<script setup>
// Portada del diseño CIRCUITO: hero partido con la identidad del negocio a la
// izquierda y la tarjeta del producto destacado a la derecha (con badge -N%
// y chips de especificaciones reales del producto). Es markup propio del
// diseño porque la tarjeta de specs no existe en el hero compartido; reusa
// las piezas comunes (AppIcon, vReveal, useFeaturedCatalog, helpers de
// precio/oferta y el estado de horario) sin fetching nuevo.
import { ref, computed, inject, onMounted, onBeforeUnmount } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { openStatus } from '../../../utils/storeHours.js'
import { productOffer, offerPct, effectivePrice } from '../../../api/catalog.api.js'
import { formatARS } from '../../../api/billing.api.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

const ctx = inject('storePage')
const { slug, custom, shopName, nameFont, initial, location, showContact, showCatalog } = ctx
const servicesPage = ctx.showServices

const { featured: shopCatalog } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const servicesTo = computed(() => ({ name: 'store-services', params: storeHostSlug ? {} : { slug: slug.value } }))
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })

// El titular es el del dueño; si no cargó uno, el nombre del negocio es el h1.
const heroTitleIsName = computed(() => !custom.value.headline?.trim())
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value)
// Palabra(s) acentuadas del titular: las dos últimas, para el remate de la
// referencia ("…lista para usar"). Con una sola palabra no se acenta nada.
const titleParts = computed(() => {
  const words = heroTitle.value.split(/\s+/).filter(Boolean)
  if (words.length < 3) return { head: heroTitle.value, accent: '' }
  return { head: words.slice(0, -2).join(' '), accent: words.slice(-2).join(' ') }
})
const heroBadge = computed(() => (heroTitleIsName.value
  ? (location.value || (showCatalog.value ? 'Catálogo online' : 'Sitio oficial'))
  : shopName.value))

const now = ref(new Date())
let clock = null
onMounted(() => { clock = setInterval(() => { now.value = new Date() }, 60000) })
onBeforeUnmount(() => clearInterval(clock))
const openNow = computed(() => (custom.value.show_hours !== false ? openStatus(custom.value.hours, now.value) : null))
const heroMeta = computed(() => {
  const items = []
  if (openNow.value) items.push({ key: 'open', state: openNow.value.state, text: openNow.value.text })
  if (location.value) items.push({ key: 'loc', text: location.value })
  if (custom.value.about_years) items.push({ key: 'years', text: `${custom.value.about_years} años` })
  return items
})

// Producto destacado: el primero con foto (los chips de specs necesitan
// features reales cargadas por el dueño). Sin producto la tarjeta muestra el
// logo/monograma como placa, nunca un texto de "foto del producto".
const heroProduct = computed(() => {
  const list = shopCatalog.value.products || []
  return list.find((p) => p.image && Object.keys(p.features || {}).length) || list.find((p) => p.image) || null
})
const heroImage = computed(() => heroProduct.value?.image || (ctx.hasDesignAdvanced.value ? custom.value.cover : '') || '')
const heroOffer = computed(() => (heroProduct.value ? productOffer(heroProduct.value) : null))
const heroPct = computed(() => (heroProduct.value ? offerPct(heroProduct.value) : 0))
const heroPrice = computed(() => (heroProduct.value ? formatARS(effectivePrice(heroProduct.value)) : ''))
// Dos chips de especificaciones (RAM/SSD, pantalla, etc.): los primeros pares
// cargados en el producto, recortados para que no rompan la placa.
const heroChips = computed(() => {
  const f = heroProduct.value?.features || {}
  return Object.entries(f).slice(0, 2).map(([k, v]) => `${k} ${v}`).slice(0, 2)
})

const copied = ref(false)
async function share() {
  const data = { title: shopName.value, text: custom.value.description?.trim() || `Mirá ${shopName.value}`, url: window.location.href }
  if (navigator.share) {
    try { await navigator.share(data); return } catch (e) { if (e?.name === 'AbortError') return }
  }
  try {
    await navigator.clipboard.writeText(window.location.href)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2500)
  } catch { /* el link ya está en la barra del navegador */ }
}
</script>

<template>
  <section class="ci-hero" aria-labelledby="ci-hero-title">
    <div class="ci-container ci-hero-grid">
      <div class="ci-hero-copy">
        <p v-reveal class="ci-hero-badge">{{ heroBadge }}</p>
        <h1 id="ci-hero-title" v-reveal="70" class="ci-hero-title" :class="{ 'is-name': heroTitleIsName }" :style="heroTitleIsName ? nameFont : null">
          <span>{{ titleParts.head }}</span><span v-if="titleParts.accent" class="ci-acc">{{ ' ' + titleParts.accent }}</span>
        </h1>
        <p v-if="custom.description" v-reveal="140" class="ci-hero-sub">{{ custom.description }}</p>

        <div v-reveal="210" class="ci-hero-ctas">
          <RouterLink v-if="showCatalog" class="ci-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" /></RouterLink>
          <RouterLink v-if="servicesPage" class="ci-btn is-ghost" :to="servicesTo"><AppIcon name="wrench" :size="15" /> Servicio técnico</RouterLink>
          <a v-if="showContact" class="ci-hero-link" href="#contacto">Contáctanos</a>
          <button type="button" class="ci-iconbtn" :aria-label="copied ? 'Link copiado' : 'Compartir tienda'" :title="copied ? 'Link copiado' : 'Compartir'" @click="share">
            <AppIcon :name="copied ? 'check' : 'share-2'" :size="16" />
          </button>
        </div>

        <ul v-if="heroMeta.length" v-reveal="280" class="ci-hero-meta">
          <li v-for="m in heroMeta" :key="m.key" :class="{ 'is-open': m.state }">
            <span v-if="m.state" class="ci-dot" aria-hidden="true"></span>
            {{ m.text }}
          </li>
        </ul>
      </div>

      <!-- Tarjeta del producto destacado -->
      <component
        :is="heroProduct ? 'RouterLink' : 'div'" v-reveal="120" class="ci-hero-card"
        :to="heroProduct ? productTo(heroProduct) : null"
        :aria-label="heroProduct ? `Ver ${heroProduct.name}` : null"
      >
        <span v-if="heroOffer != null" class="ci-hero-card-off">-{{ heroPct }}%</span>
        <img v-if="heroImage" :src="heroImage" :alt="heroProduct ? heroProduct.name : ''" loading="eager" decoding="async" fetchpriority="high" />
        <span v-else class="ci-hero-card-ph" aria-hidden="true">{{ initial }}</span>
        <span v-if="heroProduct" class="ci-hero-card-body">
          <strong class="ci-hero-card-name">{{ heroProduct.name }}</strong>
          <span v-if="heroPrice" class="ci-hero-card-price">{{ heroPrice }}</span>
        </span>
        <ul v-if="heroChips.length" class="ci-hero-chips">
          <li v-for="chip in heroChips" :key="chip">{{ chip }}</li>
        </ul>
      </component>
    </div>
  </section>
</template>
