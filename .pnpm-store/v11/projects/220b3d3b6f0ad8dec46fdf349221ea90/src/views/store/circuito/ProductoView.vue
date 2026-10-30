<script setup>
// Ficha de producto del diseño CIRCUITO (/<slug>/producto/<id>) como ficha
// técnica de laboratorio: galería con marco HUD, panel de compra premium
// (sticky en desktop), tabla de especificaciones ordenada por el
// feature_schema de la categoría, descripción, reseñas y relacionados.
// Los datos salen del catálogo público; la lógica de negocio no vive acá.
import { ref, computed, watch, inject, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeHostSlug } from '../../../config/env.js'
import { formatARS } from '../../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct, productDiscount, offerEndsLabel } from '../../../api/catalog.api.js'
import AppIcon from '../../../components/AppIcon.vue'
import ProductStars from '../../../components/ProductStars.vue'
import ProductReviews from '../../../components/ProductReviews.vue'
import TplProductCard from '../../../components/store/TplProductCard.vue'
import { vReveal } from '../../../directives/reveal.js'

const ctx = inject('storePage')
const { slug, custom, shopName, location, loadPublicCatalog } = ctx
const route = useRoute()
const router = useRouter()

const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${slug.value}` }))
const catalogTo = computed(() => ({ path: storeHostSlug ? '/catalogo' : `/${slug.value}/catalogo` }))
const contactTo = computed(() => ({ ...homeTo.value, hash: '#contacto' }))
const productTo = (p) => ({
  name: 'store-product',
  params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id }
})

// Catálogo opcional: si el dueño lo apagó no hay publicaciones activas.
watch(() => custom.value.show_catalog, (v) => {
  if (v === false) router.replace(homeTo.value)
}, { immediate: true })

const catalog = ref({ categories: [], brands: [], products: [] })
const status = ref('loading') // loading | ready | missing | error
const copied = ref(false)
const ratingIcon = computed(() => 'star')

const product = computed(() => catalog.value.products.find((p) => String(p.id) === String(route.params.productId)) || null)
const categoryName = computed(() => catalog.value.categories.find((c) => c.id === product.value?.category)?.name || '')
const brandName = computed(() => catalog.value.brands.find((b) => b.id === product.value?.brand)?.name || '')

const featureRows = computed(() => {
  const p = product.value
  if (!p?.features) return []
  const schema = catalog.value.categories.find((c) => c.id === p.category)?.feature_schema || []
  const order = new Map(schema.map((name, i) => [name.toLowerCase(), i]))
  return Object.entries(p.features).sort(
    (a, b) => (order.get(a[0].toLowerCase()) ?? schema.length) - (order.get(b[0].toLowerCase()) ?? schema.length)
  )
})
// Chips de specs del panel de compra: los primeros pares, en el mismo orden
// de la tabla (plantilla de la categoría primero).
const specChips = computed(() => featureRows.value.slice(0, 4))

const related = computed(() => {
  if (!product.value) return []
  const rest = catalog.value.products.filter((p) => p.id !== product.value.id)
  const sameCat = rest.filter((p) => p.category && p.category === product.value.category)
  const sameBrand = rest.filter((p) => p.brand && p.brand === product.value.brand && !sameCat.includes(p))
  const others = rest.filter((p) => !sameCat.includes(p) && !sameBrand.includes(p))
  return [...sameCat, ...sameBrand, ...others].slice(0, 4)
})

const whatsappUrl = computed(() => {
  const num = String(custom.value.whatsapp || '').replace(/\D/g, '')
  if (!num || !product.value) return ''
  const text = `Hola ${shopName.value}, me interesa "${product.value.name}" (${formatARS(effectivePrice(product.value))}) que vi en tu catálogo.`
  return `https://wa.me/${num}?text=${encodeURIComponent(text)}`
})

async function share() {
  try {
    await navigator.clipboard.writeText(window.location.href)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2500)
  } catch { /* el link ya está en la barra del navegador */ }
}

async function load() {
  status.value = 'loading'
  try {
    catalog.value = await loadPublicCatalog()
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
  <div class="sp-page-root ci-product">
    <main class="ci-container ci-pd-main">
      <nav v-reveal class="ci-crumbs is-dark" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="12" aria-hidden="true" />
        <RouterLink :to="catalogTo">Catálogo</RouterLink>
        <template v-if="categoryName">
          <AppIcon name="chevron-right" :size="12" aria-hidden="true" />
          <span>{{ categoryName }}</span>
        </template>
        <template v-if="product">
          <AppIcon name="chevron-right" :size="12" aria-hidden="true" />
          <span class="ci-crumb-here" aria-current="page">{{ product.name }}</span>
        </template>
      </nav>

      <!-- Carga -->
      <div v-if="status === 'loading'" class="ci-pd-sheet" aria-busy="true">
        <div class="ci-pd-top">
          <div class="ci-pd-gallery ci-skel-block"></div>
          <div class="ci-pd-buy">
            <span class="ci-sk-line short"></span>
            <span class="ci-sk-line"></span>
            <span class="ci-sk-line"></span>
            <span class="ci-sk-line short"></span>
          </div>
        </div>
      </div>

      <template v-else-if="status === 'ready' && product">
        <article v-reveal class="ci-pd-sheet">
          <div class="ci-pd-top">
            <!-- Galería con marco HUD -->
            <div class="ci-pd-media-col">
              <figure class="ci-pd-gallery">
                <span class="ci-pd-tag" aria-hidden="true">IMG <span>// 01</span></span>
                <img v-if="product.image" :src="product.image" :alt="product.name" decoding="async" fetchpriority="high">
                <span v-else class="ci-pd-ph" aria-hidden="true"><AppIcon name="package" :size="56" /></span>
                <figcaption class="sr-only">Fotografía del producto {{ product.name }}</figcaption>
              </figure>
              <ul class="ci-pd-meta" aria-label="Datos del producto">
                <li>
                  <span class="ci-pd-meta-k">ID</span>
                  <strong class="ci-pd-meta-v">#{{ product.id }}</strong>
                </li>
                <li>
                  <span class="ci-pd-meta-k">Categoría</span>
                  <strong class="ci-pd-meta-v">{{ categoryName || 'General' }}</strong>
                </li>
                <li>
                  <span class="ci-pd-meta-k">Estado</span>
                  <strong class="ci-pd-meta-v is-ok">{{ isNewProduct(product) ? 'Nuevo' : 'Disponible' }}</strong>
                </li>
              </ul>
            </div>

            <!-- Panel de compra (sticky en desktop) -->
            <aside class="ci-pd-buy" aria-label="Información del producto">
              <div class="ci-pd-buy-head">
                <p class="ci-pd-cond"><span aria-hidden="true"></span>{{ isNewProduct(product) ? 'Nuevo' : 'Disponible' }}</p>
                <button type="button" class="ci-iconbtn" :aria-label="copied ? 'Link copiado' : 'Compartir producto'" :title="copied ? 'Link copiado' : 'Compartir'" @click="share">
                  <AppIcon :name="copied ? 'check' : 'share-2'" :size="16" />
                </button>
              </div>
              <p v-if="categoryName || brandName" class="ci-pd-eyebrow"><span aria-hidden="true">//</span> {{ [categoryName, brandName].filter(Boolean).join(' · ') }}</p>
              <h1 class="ci-pd-name">{{ product.name }}</h1>
              <ProductStars v-if="custom.show_reviews && product.rating_count" class="ci-pd-stars" :avg="product.rating_avg" :count="product.rating_count" :icon="ratingIcon" :size="14" show-value />

              <ul v-if="specChips.length" class="ci-pd-chips" aria-label="Especificaciones destacadas">
                <li v-for="[k, v] in specChips" :key="k">{{ k }} <span>{{ v }}</span></li>
              </ul>

              <div class="ci-pd-pricebox">
                <p class="ci-pd-price-label">Precio efectivo</p>
                <s v-if="productOffer(product) != null" class="ci-pd-price-old">{{ formatARS(product.price) }}</s>
                <div class="ci-pd-price-row">
                  <span class="ci-pd-price">{{ formatARS(effectivePrice(product)) }}</span>
                  <span v-if="productOffer(product) != null" class="ci-pd-offer">-{{ offerPct(product) }}%</span>
                </div>
                <p v-if="productDiscount(product)" class="ci-pd-promo">
                  <AppIcon name="tag" :size="13" aria-hidden="true" />
                  <span>Promo {{ productDiscount(product).name }}<span v-if="offerEndsLabel(productDiscount(product))"> · {{ offerEndsLabel(productDiscount(product)) }}</span></span>
                </p>
                <p class="ci-pd-pay">
                  <AppIcon name="credit-card" :size="14" aria-hidden="true" />
                  Medios de pago, cuotas y envío se coordinan con el vendedor
                </p>
              </div>

              <div class="ci-pd-ctas">
                <a v-if="whatsappUrl" class="ci-btn" :href="whatsappUrl" target="_blank" rel="noopener">
                  <AppIcon name="whatsapp" :size="16" /> Consultar por WhatsApp
                </a>
                <RouterLink v-else class="ci-btn" :to="contactTo">
                  <AppIcon name="message-circle" :size="16" /> Consultar al vendedor
                </RouterLink>
                <RouterLink v-if="whatsappUrl" class="ci-btn is-ghost" :to="contactTo">
                  <AppIcon name="mail" :size="15" /> Enviar un mensaje
                </RouterLink>
                <RouterLink class="ci-pd-backlink" :to="catalogTo">
                  <AppIcon name="arrow-left" :size="13" /> Seguir explorando el catálogo
                </RouterLink>
              </div>

              <ul class="ci-pd-seller">
                <li>
                  <AppIcon name="store" :size="14" aria-hidden="true" />
                  <span>Vendido por <strong>{{ shopName }}</strong></span>
                </li>
                <li v-if="location">
                  <AppIcon name="map-pin" :size="14" aria-hidden="true" />
                  <span>{{ location }}</span>
                </li>
                <li>
                  <AppIcon name="shield-check" :size="14" aria-hidden="true" />
                  <span>Tu consulta llega directo al comercio, sin intermediarios</span>
                </li>
              </ul>
            </aside>
          </div>

          <!-- Especificaciones -->
          <section v-if="featureRows.length" class="ci-pd-sec" aria-labelledby="ci-specs-title">
            <div class="ci-pd-sec-head">
              <h2 id="ci-specs-title" class="ci-pd-sec-title">Especificaciones</h2>
              <span class="ci-pd-sec-count">{{ featureRows.length }} {{ featureRows.length === 1 ? 'parámetro' : 'parámetros' }}</span>
            </div>
            <div class="ci-pd-specs-wrap">
              <table class="ci-pd-specs">
                <caption class="sr-only">Especificaciones técnicas de {{ product.name }}</caption>
                <thead>
                  <tr><th scope="col">Parámetro</th><th scope="col">Valor</th></tr>
                </thead>
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
          <section v-if="product.description" class="ci-pd-sec" aria-labelledby="ci-desc-title">
            <div class="ci-pd-sec-head">
              <h2 id="ci-desc-title" class="ci-pd-sec-title">Descripción</h2>
            </div>
            <p class="ci-pd-desc">{{ product.description }}</p>
          </section>

          <!-- Opiniones y valoraciones -->
          <ProductReviews
            v-if="custom.show_reviews || custom.show_comments"
            :slug="slug"
            :product-id="product.id"
            :can-rate="custom.show_reviews"
            :can-comment="custom.show_comments"
            :avg="product.rating_avg"
            :count="product.rating_count || 0"
            :icon="ratingIcon"
          />
        </article>

        <!-- CTA fija en móvil -->
        <div class="ci-pd-stick">
          <span class="ci-pd-stick-info">
            <s v-if="productOffer(product) != null">{{ formatARS(product.price) }}</s>
            <strong>{{ formatARS(effectivePrice(product)) }}</strong>
          </span>
          <a v-if="whatsappUrl" class="ci-btn ci-pd-stick-btn" :href="whatsappUrl" target="_blank" rel="noopener">
            <AppIcon name="whatsapp" :size="15" /> Consultar
          </a>
          <RouterLink v-else class="ci-btn ci-pd-stick-btn" :to="contactTo">
            <AppIcon name="message-circle" :size="15" /> Consultar
          </RouterLink>
        </div>

        <!-- Relacionados -->
        <section v-if="related.length" v-reveal="80" class="ci-pd-related" aria-labelledby="ci-rel-title">
          <div class="ci-pd-sec-head">
            <h2 id="ci-rel-title" class="ci-pd-sec-title">También te puede interesar</h2>
          </div>
          <div class="ci-pd-rel-grid">
            <TplProductCard v-for="r in related" :key="r.id" class="ci-card" :p="r"
              seal-shape="" :ph-size="24" :go="false" @open="(r2) => router.push(productTo(r2))" />
          </div>
        </section>
      </template>

      <!-- Producto dado de baja / error de red -->
      <div v-else class="ci-empty">
        <AppIcon :name="status === 'error' ? 'circle-alert' : 'package'" :size="26" />
        <strong>{{ status === 'error' ? 'No pudimos cargar el producto' : 'Este producto ya no está disponible' }}</strong>
        <p>{{ status === 'error' ? 'Revisá tu conexión e intentá de nuevo.' : 'Puede que el comercio lo haya dado de baja del catálogo.' }}</p>
        <button v-if="status === 'error'" type="button" class="ci-btn is-ghost" @click="load"><AppIcon name="refresh" :size="15" /> Reintentar</button>
        <RouterLink v-else class="ci-btn is-ghost" :to="catalogTo"><AppIcon name="arrow-left" :size="14" /> Volver al catálogo</RouterLink>
      </div>
    </main>
  </div>
</template>
