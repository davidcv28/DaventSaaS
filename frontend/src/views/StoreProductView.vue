<script setup>
import { ref, computed, watch, inject, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storesApi } from '../api/stores.api.js'
import { storeHostSlug } from '../config/env.js'
import { formatARS } from '../api/billing.api.js'
import AppIcon from '../components/AppIcon.vue'
import { vReveal } from '../directives/reveal.js'

// Página de producto estilo marketplace (/<slug>/producto/<id>): migas,
// galería a la izquierda y panel de compra a la derecha (precio, CTA de
// contacto, vendedor), tabla de características, descripción y
// relacionados. Los datos salen del catálogo público (el backend solo
// devuelve productos activos de la tienda).
const ctx = inject('storePage')
const { slug, custom, shopName, location } = ctx
const route = useRoute()
const router = useRouter()

const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${slug.value}` }))
const catalogTo = computed(() => ({ path: storeHostSlug ? '/catalogo' : `/${slug.value}/catalogo` }))
const contactTo = computed(() => ({ ...homeTo.value, hash: '#contacto' }))
const productTo = (p) => ({
  name: 'store-product',
  params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id }
})

// Catálogo opcional: si el dueño lo apagó no hay publicaciones activas (el
// endpoint también devuelve 404) y esta página no existe.
watch(() => custom.value.show_catalog, (v) => {
  if (v === false) router.replace(homeTo.value)
}, { immediate: true })

const catalog = ref({ categories: [], brands: [], products: [] })
const status = ref('loading') // loading | ready | missing | error
const copied = ref(false)

const product = computed(() => catalog.value.products.find((p) => String(p.id) === String(route.params.productId)) || null)
const categoryName = computed(() => catalog.value.categories.find((c) => c.id === product.value?.category)?.name || '')
const brandName = computed(() => catalog.value.brands.find((b) => b.id === product.value?.brand)?.name || '')
const featureRows = computed(() => Object.entries(product.value?.features || {}))
// Relacionados: primero los de la misma categoría, luego la misma marca y
// después el resto, hasta 4 — mismo criterio de sugerencia de un marketplace.
const related = computed(() => {
  if (!product.value) return []
  const rest = catalog.value.products.filter((p) => p.id !== product.value.id)
  const sameCat = rest.filter((p) => p.category && p.category === product.value.category)
  const sameBrand = rest.filter((p) => p.brand && p.brand === product.value.brand && !sameCat.includes(p))
  const others = rest.filter((p) => !sameCat.includes(p) && !sameBrand.includes(p))
  return [...sameCat, ...sameBrand, ...others].slice(0, 4)
})

// CTA principal: consulta por WhatsApp con el producto ya citado en el
// mensaje (el comercio recibe el interés concreto, como en un marketplace).
const whatsappUrl = computed(() => {
  const num = String(custom.value.whatsapp || '').replace(/\D/g, '')
  if (!num || !product.value) return ''
  const text = `Hola ${shopName.value}, me interesa "${product.value.name}" (${formatARS(product.value.price)}) que vi en tu catálogo.`
  return `https://wa.me/${num}?text=${encodeURIComponent(text)}`
})

async function share() {
  try {
    await navigator.clipboard.writeText(window.location.href)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2500)
  } catch {
    // Sin clipboard disponible: el link ya está en la barra del navegador.
  }
}

async function load() {
  status.value = 'loading'
  try {
    catalog.value = await storesApi.publicCatalog(slug.value, {})
    status.value = product.value ? 'ready' : 'missing'
    if (product.value) document.title = `${product.value.name} · ${shopName.value}`
  } catch {
    status.value = 'error'
  }
}

onMounted(() => {
  if (custom.value.show_catalog !== false) load()
})
</script>

<template>
<div class="sp-page-root">
  <main class="sp-container spd-main">
    <nav v-reveal class="spd-crumbs" aria-label="Ruta">
      <RouterLink :to="homeTo">Inicio</RouterLink>
      <AppIcon name="chevron-right" :size="13" aria-hidden="true" />
      <RouterLink :to="catalogTo">Catálogo</RouterLink>
      <template v-if="categoryName">
        <AppIcon name="chevron-right" :size="13" aria-hidden="true" />
        <span>{{ categoryName }}</span>
      </template>
      <template v-if="product">
        <AppIcon name="chevron-right" :size="13" aria-hidden="true" />
        <span class="spd-crumb-here" aria-current="page">{{ product.name }}</span>
      </template>
    </nav>

    <!-- Carga: esqueleto de la ficha -->
    <div v-if="status === 'loading'" class="spd-sheet" aria-busy="true">
      <div class="spd-top">
        <div class="spd-gallery spd-sk-block"></div>
        <div class="spd-buy">
          <span class="sp-sk-line short"></span>
          <span class="sp-sk-line"></span>
          <span class="sp-sk-line"></span>
          <span class="sp-sk-line short"></span>
        </div>
      </div>
    </div>

    <template v-else-if="status === 'ready' && product">
      <article v-reveal class="spd-sheet">
        <div class="spd-top">
          <!-- Galería -->
          <div class="spd-gallery">
            <img v-if="product.image" :src="product.image" :alt="product.name" />
            <span v-else class="sp-card-placeholder"><AppIcon name="package" :size="64" /></span>
          </div>

          <!-- Panel de compra -->
          <aside class="spd-buy" aria-label="Información del producto">
            <div class="spd-buy-head">
              <p class="spd-cond">Disponible</p>
              <button type="button" class="sp-icon-btn spd-share" :aria-label="copied ? 'Link copiado' : 'Compartir producto'" :title="copied ? 'Link copiado' : 'Compartir'" @click="share">
                <AppIcon :name="copied ? 'check' : 'share-2'" :size="16" />
              </button>
            </div>
            <h1 class="spd-name">{{ product.name }}</h1>
            <p v-if="brandName" class="spd-brand">Marca: {{ brandName }}</p>

            <div class="spd-pricebox">
              <span class="spd-price">{{ formatARS(product.price) }}</span>
              <p class="spd-pay">
                <AppIcon name="credit-card" :size="15" aria-hidden="true" />
                Medios de pago, cuotas y envío se coordinan con el vendedor
              </p>
            </div>

            <div class="spd-ctas">
              <a v-if="whatsappUrl" class="sp-btn spd-buy-btn" :href="whatsappUrl" target="_blank" rel="noopener">
                <AppIcon name="whatsapp" :size="17" /> Consultar por WhatsApp
              </a>
              <RouterLink v-else class="sp-btn spd-buy-btn" :to="contactTo">
                <AppIcon name="message-circle" :size="17" /> Consultar al vendedor
              </RouterLink>
              <RouterLink v-if="whatsappUrl" class="sp-btn ghost" :to="contactTo">
                <AppIcon name="mail" :size="15" /> Enviar un mensaje
              </RouterLink>
              <RouterLink class="spd-backlink" :to="catalogTo">
                <AppIcon name="arrow-left" :size="14" /> Seguir explorando el catálogo
              </RouterLink>
            </div>

            <ul class="spd-seller">
              <li>
                <AppIcon name="store" :size="15" aria-hidden="true" />
                <span>Vendido por <strong>{{ shopName }}</strong></span>
              </li>
              <li v-if="location">
                <AppIcon name="map-pin" :size="15" aria-hidden="true" />
                <span>{{ location }}</span>
              </li>
              <li>
                <AppIcon name="shield-check" :size="15" aria-hidden="true" />
                <span>Tu consulta llega directo al comercio, sin intermediarios</span>
              </li>
            </ul>
          </aside>
        </div>

        <!-- Características -->
        <section v-if="featureRows.length" class="spd-sec" aria-labelledby="spd-specs-title">
          <h2 id="spd-specs-title" class="spd-sec-title">Características principales</h2>
          <div class="spd-specs-wrap">
            <table class="spd-specs">
              <tbody>
                <tr v-for="[key, value] in featureRows" :key="key">
                  <th scope="row">{{ key }}</th>
                  <td>{{ value }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- Descripción -->
        <section v-if="product.description" class="spd-sec" aria-labelledby="spd-desc-title">
          <h2 id="spd-desc-title" class="spd-sec-title">Descripción</h2>
          <p class="spd-desc">{{ product.description }}</p>
        </section>
      </article>

      <!-- Relacionados -->
      <section v-if="related.length" v-reveal="80" class="spd-related" aria-labelledby="spd-rel-title">
        <h2 id="spd-rel-title" class="spd-sec-title">También te puede interesar</h2>
        <div class="spd-rel-grid">
          <RouterLink v-for="p in related" :key="p.id" class="spd-rel" :to="productTo(p)">
            <span class="spd-rel-img">
              <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
              <AppIcon v-else name="package" :size="24" aria-hidden="true" />
            </span>
            <span class="spd-rel-name">{{ p.name }}</span>
            <span class="spd-rel-price">{{ formatARS(p.price) }}</span>
          </RouterLink>
        </div>
      </section>
    </template>

    <!-- Producto dado de baja / error de red -->
    <div v-else class="sp-empty">
      <span class="sp-empty-icon"><AppIcon :name="status === 'error' ? 'circle-alert' : 'package'" :size="26" /></span>
      <strong>{{ status === 'error' ? 'No pudimos cargar el producto' : 'Este producto ya no está disponible' }}</strong>
      <p>{{ status === 'error' ? 'Revisá tu conexión e intentá de nuevo.' : 'Puede que el comercio lo haya dado de baja del catálogo.' }}</p>
      <button v-if="status === 'error'" type="button" class="sp-btn ghost" @click="load"><AppIcon name="refresh" :size="16" /> Reintentar</button>
      <RouterLink v-else class="sp-btn ghost" :to="catalogTo"><AppIcon name="arrow-left" :size="15" /> Volver al catálogo</RouterLink>
    </div>
  </main>
</div>
</template>
