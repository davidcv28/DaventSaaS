<script setup>
// Ficha de producto estilo MercadoLibre (/<slug>/producto/<id>): galería con
// riel de miniaturas, columna de compra en tarjetas (precio / envío / stock /
// tienda), ficha técnica cebra, opiniones y
// relacionados. Los datos salen del catálogo público (el backend solo
// devuelve productos activos de la tienda). Los estilos mc-pdp-* viven en
// la piel Mercado (otro archivo).
import { ref, computed, watch, inject, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeHostSlug } from '../../../config/env.js'
import { formatARS } from '../../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct, productDiscount, offerEndsLabel } from '../../../api/catalog.api.js'
import { storeContactLink, hasContactChannel } from '../../../api/stores.api.js'
import { paymentMethodsFromConfig } from '../../../api/storeCommerce.js'
import { useCartStore } from '../../../stores/cart.store.js'
import AppIcon from '../../../components/AppIcon.vue'
import ProductStars from '../../../components/ProductStars.vue'
import ProductReviews from '../../../components/ProductReviews.vue'
import { vReveal } from '../../../directives/reveal.js'
import TplProductCard from '../../../components/store/TplProductCard.vue'

const ctx = inject('storePage')
const { slug, custom, shopName, location, loadPublicCatalog } = ctx
const route = useRoute()
const router = useRouter()
const cartStore = useCartStore()

// Venta online efectiva (la calcula el backend: ecommerce_enabled + fiscal
// completo). Con orders_enabled la ficha suma "Comprar ahora" / "Agregar al
// carrito"; sin él queda el flujo de consulta de siempre.
const ordersEnabled = computed(() => Boolean(ctx?.ordersEnabled?.value ?? ctx?.ordersEnabled))
// Tarifa de envío a domicilio del payload público (StoreShippingConfig):
// home_price null = "a coordinar"; número >= 0 = precio fijo que el
// checkout cobra (0 = envío gratis). El retiro en el local siempre es
// sin cargo.
const storeData = computed(() => ctx?.store?.value || ctx?.store || null)
const homePrice = computed(() => {
  const raw = storeData.value?.shipping?.home_price
  if (raw === null || raw === undefined || raw === '') return null
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
})
const shipLine = computed(() => {
  if (!ordersEnabled.value) return null
  if (homePrice.value === null) return 'Envío a domicilio a coordinar'
  return homePrice.value > 0
    ? `Envío a domicilio ${formatARS(homePrice.value)}`
    : 'Envío a domicilio sin cargo'
})
// Cantidad del alta: el stepper alimenta los botones de compra y se cita en
// el mensaje de WhatsApp cuando es > 1.
const QTY_MAX = 99
const qty = ref(1)
const adding = ref(false)
const added = ref(false)
let addedTimer = 0

// Medios de pago reales del payload público (store.payments, mismo mapa que
// el checkout) en labels cortos para la fila de chips de la ficha.
const PAY_SHORT = { transfer: 'Transferencia', whatsapp: 'WhatsApp', cash: 'Efectivo', mp: 'Mercado Pago' }
const payMethods = computed(() => {
  if (!ordersEnabled.value) return []
  return paymentMethodsFromConfig(storeData.value?.payments)
    .map((m) => ({ ...m, short: PAY_SHORT[m.value] || m.label }))
})

// Compra directa: alta silenciosa al carrito y checkout — sin drawer. Si el
// comprador no tiene sesión, buyNow deja la acción pendiente y el `after`
// corre post-login desde el modal de auth.
const buying = ref(false)
async function buyNow() {
  if (buying.value || stockExhausted.value || !product.value) return
  buying.value = true
  try {
    await cartStore.buyNow(product.value.id, qty.value, product.value.name, () => router.push(cartStore.checkoutRoute()))
  } finally {
    buying.value = false
  }
}
async function addToCart() {
  if (adding.value || stockExhausted.value || !product.value) return
  adding.value = true
  try {
    const res = await cartStore.addToCart(product.value.id, qty.value, product.value.name)
    if (res?.ok) {
      added.value = true
      clearTimeout(addedTimer)
      addedTimer = setTimeout(() => { added.value = false }, 1600)
    }
  } finally {
    adding.value = false
  }
}

// Lightbox de la foto: vista ampliada (Esc/fondo/cierra).
const lightbox = ref(false)
let lbPrevFocus = null
const lbClose = ref(null)
function openLightbox() {
  if (!currentImage.value) return
  lbPrevFocus = document.activeElement
  lightbox.value = true
  document.documentElement.classList.add('sp-lock')
  nextTick(() => lbClose.value?.focus())
}
function closeLightbox() {
  if (!lightbox.value) return
  lightbox.value = false
  document.documentElement.classList.remove('sp-lock')
  lbPrevFocus?.focus?.()
  lbPrevFocus = null
}
function onLbKey(e) {
  if (e.key === 'Escape') closeLightbox()
}
watch(lightbox, (v) => {
  if (v) window.addEventListener('keydown', onLbKey)
  else window.removeEventListener('keydown', onLbKey)
})

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

const ratingIcon = computed(() => 'star')

const product = computed(() => catalog.value.products.find((p) => String(p.id) === String(route.params.productId)) || null)
// Galería: si el producto trae `images` se usa esa lista; si no, la foto
// única `image`. La miniatura activa cambia la imagen del marco y abre el
// lightbox con la foto elegida. OJO: vive DESPUÉS de `product` — el watch
// evalúa galleryImages en su creación y antes de la declaración rompía el
// setup por TDZ (página en blanco).
const galleryImages = computed(() => {
  const p = product.value
  if (!p) return []
  if (Array.isArray(p.images) && p.images.length) return p.images.filter(Boolean)
  return p.image ? [p.image] : []
})
const activeImage = ref(0)
const currentImage = computed(() => galleryImages.value[activeImage.value] || '')
watch(galleryImages, () => { activeImage.value = 0 })
const availableStock = computed(() => {
  const current = product.value
  if (!current || !Object.prototype.hasOwnProperty.call(current, 'available_stock')) return undefined
  const raw = current.available_stock
  if (raw === null) return null
  const stock = Number(raw)
  return Number.isFinite(stock) ? Math.max(0, Math.floor(stock)) : null
})
const stockExhausted = computed(() => ordersEnabled.value && availableStock.value === 0)
const stockLine = computed(() => {
  if (!ordersEnabled.value || !product.value) return null
  if (availableStock.value === undefined) return null
  if (availableStock.value === null) return 'Disponibilidad ilimitada'
  if (availableStock.value === 0) return 'Agotado · sin unidades disponibles'
  return `${availableStock.value} ${availableStock.value === 1 ? 'unidad' : 'unidades'} disponibles`
})
const qtyLimit = computed(() => Math.max(1, Math.min(QTY_MAX, availableStock.value ?? QTY_MAX)))
const setQty = (n) => { qty.value = Math.min(qtyLimit.value, Math.max(1, Math.round(Number(n)) || 1)) }
watch(availableStock, () => setQty(qty.value))
const categoryName = computed(() => catalog.value.categories.find((c) => c.id === product.value?.category)?.name || '')
const brandName = computed(() => catalog.value.brands.find((b) => b.id === product.value?.brand)?.name || '')
const hasOffer = computed(() => product.value != null && productOffer(product.value) != null)
// Características del producto: primero las de la plantilla de su categoría
// (en el orden que la definió el dueño), después las libres.
const featureRows = computed(() => {
  const p = product.value
  if (!p?.features) return []
  const schema = catalog.value.categories.find((c) => c.id === p.category)?.feature_schema || []
  const order = new Map(schema.map((name, i) => [name.toLowerCase(), i]))
  return Object.entries(p.features).sort(
    (a, b) => (order.get(a[0].toLowerCase()) ?? schema.length) - (order.get(b[0].toLowerCase()) ?? schema.length)
  )
})
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
// Lookup por producto para las tarjetas de "También te puede interesar".
const catNameOf = (p) => catalog.value.categories.find((c) => c.id === p.category)?.name || ''
const brandNameOf = (p) => catalog.value.brands.find((b) => b.id === p.brand)?.name || ''

// CTA de consulta: WhatsApp con el producto ya citado en el mensaje (el
// comercio recibe el interés concreto, como en un marketplace).
const whatsappUrl = computed(() => {
  if (!hasContactChannel(custom.value, 'whatsapp') || !product.value) return ''
  const qtyNote = qty.value > 1 ? ` · ${qty.value} unidades` : ''
  const text = `Hola ${shopName.value}, me interesa "${product.value.name}" (${formatARS(effectivePrice(product.value))}${qtyNote}) que vi en tu catálogo.`
  return storeContactLink(slug.value, 'whatsapp', text)
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

// Monograma de la tienda: si no hay logo, la inicial del nombre.
const storeMonogram = computed(() => (shopName.value || '?').trim().charAt(0).toUpperCase())

async function load() {
  status.value = 'loading'
  try {
    catalog.value = await loadPublicCatalog()
    status.value = product.value ? 'ready' : 'missing'
    if (product.value) {
      document.title = `${product.value.name} · ${shopName.value}`
      // Re-emite OG/JSON-LD del layout con el título del producto (el
      // syncSeo del layout leyó el título de la tienda antes de esta carga).
      ctx.refreshSeo?.()
    }
  } catch {
    status.value = 'error'
  }
}

onMounted(() => {
  if (custom.value.show_catalog !== false) load()
})
onBeforeUnmount(() => {
  clearTimeout(addedTimer)
  window.removeEventListener('keydown', onLbKey)
  document.documentElement.classList.remove('sp-lock')
})
</script>

<template>
  <div class="store-page mc-skin mc-product" data-template="mercado">
    <div class="sp-page-root mc-pdp-page">
      <main class="mc-pdp-wrap">
        <nav class="mc-pdp-crumbs" aria-label="Ruta">
          <button type="button" class="mc-pdp-back" @click="router.back()">
            <AppIcon name="arrow-left" :size="14" aria-hidden="true" /> Volver
          </button>
          <span class="mc-pdp-crumbs-sep" aria-hidden="true">|</span>
          <RouterLink :to="homeTo">Inicio</RouterLink>
          <span aria-hidden="true">/</span>
          <RouterLink :to="catalogTo">Catálogo</RouterLink>
          <template v-if="categoryName">
            <span aria-hidden="true">/</span>
            <span>{{ categoryName }}</span>
          </template>
          <template v-if="product">
            <span aria-hidden="true">/</span>
            <span class="mc-pdp-crumb-here" aria-current="page">{{ product.name }}</span>
          </template>
        </nav>

        <!-- Carga: esqueleto con la misma composición que la ficha -->
        <div v-if="status === 'loading'" class="mc-pdp-sheet is-loading" aria-busy="true">
          <div class="mc-pdp-top">
            <div class="mc-pdp-rail">
              <span v-for="i in 4" :key="i" class="mc-pdp-skel-thumb"></span>
            </div>
            <div class="mc-pdp-skel-media"></div>
            <div class="mc-pdp-skel-buy">
              <span class="mc-pdp-skel-line short"></span>
              <span class="mc-pdp-skel-line tall"></span>
              <span class="mc-pdp-skel-line"></span>
              <span class="mc-pdp-skel-line"></span>
              <span class="mc-pdp-skel-line short"></span>
            </div>
          </div>
        </div>

        <template v-else-if="status === 'ready' && product">
          <article v-reveal class="mc-pdp-sheet">
            <div class="mc-pdp-top">
              <!-- Riel de miniaturas -->
              <div v-if="galleryImages.length" class="mc-pdp-rail" role="group" aria-label="Fotos del producto">
                <button
                  v-for="(img, i) in galleryImages" :key="i" type="button"
                  class="mc-pdp-thumb" :class="{ 'is-on': i === activeImage }"
                  :aria-label="`Ver foto ${i + 1}`" :aria-current="i === activeImage ? 'true' : undefined"
                  @click="activeImage = i"
                >
                  <img :src="img" :alt="`${product.name} foto ${i + 1}`" loading="lazy" decoding="async" />
                </button>
              </div>

              <!-- Foto principal -->
              <figure
                class="mc-pdp-media" :class="{ 'is-zoomable': currentImage }"
                :role="currentImage ? 'button' : undefined" :tabindex="currentImage ? 0 : undefined"
                :aria-label="currentImage ? `Ampliar imagen de ${product.name}` : undefined"
                @click="openLightbox" @keydown.enter.prevent="openLightbox" @keydown.space.prevent="openLightbox"
              >
                <img v-if="currentImage" :src="currentImage" :alt="product.name" decoding="async" fetchpriority="high" />
                <span v-else class="mc-pdp-ph" aria-hidden="true"><AppIcon name="package" :size="64" /></span>
                <button type="button" class="mc-pdp-fav" aria-label="Guardar en favoritos" @click.stop>
                  <AppIcon name="heart" :size="18" aria-hidden="true" />
                </button>
                <span v-if="currentImage" class="mc-pdp-zoom-hint" aria-hidden="true">
                  <AppIcon name="maximize" :size="13" /> Ampliar
                </span>
              </figure>

              <!-- Columna de compra en tarjetas -->
              <aside class="mc-pdp-buy" aria-label="Información del producto">
                <section class="mc-pdp-card mc-pdp-price-card">
                  <p class="mc-pdp-cond">{{ isNewProduct(product) ? 'Nuevo' : 'Disponible' }}</p>
                  <h1 class="mc-pdp-name">{{ product.name }}</h1>
                  <ProductStars
                    v-if="custom.show_reviews && product.rating_count" class="mc-pdp-stars"
                    :avg="product.rating_avg" :count="product.rating_count" :icon="ratingIcon" :size="15" show-value
                  />
                  <p class="mc-pdp-price-row">
                    <s v-if="hasOffer" class="mc-pdp-old">{{ formatARS(product.price) }}</s>
                    <strong class="mc-pdp-price">{{ formatARS(effectivePrice(product)) }}</strong>
                    <span v-if="hasOffer" class="mc-pdp-off">{{ offerPct(product) }}% OFF</span>
                  </p>
                  <p v-if="productDiscount(product)" class="mc-pdp-promo">
                    <AppIcon name="tag" :size="14" aria-hidden="true" />
                    <span>
                      Promo {{ productDiscount(product).name }}<span v-if="offerEndsLabel(productDiscount(product))" class="mc-pdp-promo-ends"> · {{ offerEndsLabel(productDiscount(product)) }}</span>
                    </span>
                  </p>
                  <img
                    v-if="productDiscount(product)?.campaign?.label_url" class="mc-pdp-campaign"
                    :src="productDiscount(product).campaign.label_url"
                    :alt="productDiscount(product).campaign.label_alt || productDiscount(product).campaign.name"
                    :width="productDiscount(product).campaign.label_width || undefined"
                    :height="productDiscount(product).campaign.label_height || undefined"
                    loading="lazy" decoding="async"
                  />
                  <ul v-if="payMethods.length" class="mc-pdp-paylist" aria-label="Medios de pago aceptados">
                    <li v-for="m in payMethods" :key="m.value" class="mc-pdp-paychip" :title="m.hint">
                      <AppIcon :name="m.icon" :size="13" aria-hidden="true" />
                      <span>{{ m.short }}</span>
                    </li>
                  </ul>
                  <p v-else class="mc-pdp-pay-line">Medios de pago y cuotas se coordinan con el vendedor</p>
                  <p class="mc-pdp-seller">
                    Vendido por <strong>{{ shopName }}</strong>
                    <AppIcon name="shield-check" :size="14" aria-hidden="true" />
                  </p>
                </section>

                <section v-if="ordersEnabled" class="mc-pdp-card mc-pdp-ship-card">
                  <p v-if="shipLine" class="mc-pdp-ship">
                    <AppIcon name="truck" :size="16" aria-hidden="true" />
                    <span>{{ shipLine }}</span>
                  </p>
                  <p class="mc-pdp-pickup">
                    <AppIcon name="store" :size="16" aria-hidden="true" />
                    <span>Retirá gratis en el local</span>
                  </p>
                  <p v-if="location" class="mc-pdp-loc">
                    <AppIcon name="map-pin" :size="14" aria-hidden="true" />
                    <span>{{ location }}</span>
                  </p>
                </section>

                <section class="mc-pdp-card mc-pdp-stock-card">
                  <p
                    v-if="stockLine" class="mc-pdp-stock"
                    :class="{ 'is-exhausted': stockExhausted }" role="status"
                  >
                    <strong v-if="!stockExhausted">Stock disponible</strong>
                    <span>{{ stockLine }}</span>
                  </p>
                  <div v-if="ordersEnabled" class="mc-pdp-qty" role="group" aria-label="Cantidad">
                    <span class="mc-pdp-qty-lbl">Cantidad:</span>
                    <div class="mc-pdp-qty-ctl">
                      <button type="button" :disabled="qty <= 1 || stockExhausted" aria-label="Disminuir cantidad" @click="setQty(qty - 1)">
                        <AppIcon name="minus" :size="14" aria-hidden="true" />
                      </button>
                      <output class="mc-pdp-qty-num" aria-live="polite">{{ qty }}</output>
                      <button type="button" :disabled="qty >= qtyLimit || stockExhausted" aria-label="Aumentar cantidad" @click="setQty(qty + 1)">
                        <AppIcon name="plus" :size="14" aria-hidden="true" />
                      </button>
                    </div>
                    <span class="mc-pdp-qty-note">({{ qtyLimit }} disponibles)</span>
                  </div>
                  <div class="mc-pdp-ctas">
                    <button
                      v-if="ordersEnabled" type="button"
                      class="mc-pdp-btn mc-pdp-btn-primary"
                      :disabled="buying || stockExhausted" @click="buyNow"
                    >
                      {{ stockExhausted ? 'Agotado' : buying ? 'Procesando…' : 'Comprar ahora' }}
                    </button>
                    <button
                      v-if="ordersEnabled" type="button"
                      class="mc-pdp-btn mc-pdp-btn-soft"
                      :disabled="adding || stockExhausted" @click="addToCart"
                    >
                      <AppIcon :name="added ? 'check' : 'shopping-cart'" :size="16" aria-hidden="true" />
                      {{ stockExhausted ? 'Sin stock' : added ? 'Agregado' : 'Agregar al carrito' }}
                    </button>
                    <a
                      v-if="whatsappUrl" class="mc-pdp-btn mc-pdp-btn-ghost"
                      :href="whatsappUrl" target="_blank" rel="noopener"
                    >
                      <AppIcon name="whatsapp" :size="16" aria-hidden="true" /> Consultar por WhatsApp
                    </a>
                    <RouterLink v-else class="mc-pdp-btn mc-pdp-btn-ghost" :to="contactTo">
                      <AppIcon name="message-circle" :size="16" aria-hidden="true" /> Consultar al vendedor
                    </RouterLink>
                  </div>
                </section>

                <section class="mc-pdp-card mc-pdp-store-card">
                  <div class="mc-pdp-store-head">
                    <span class="mc-pdp-store-logo" aria-hidden="true">
                      <img v-if="custom.logo" :src="custom.logo" alt="" />
                      <template v-else>{{ storeMonogram }}</template>
                    </span>
                    <div class="mc-pdp-store-info">
                      <p class="mc-pdp-store-name">
                        Tienda oficial {{ shopName }}
                        <AppIcon name="shield-check" :size="14" aria-hidden="true" />
                      </p>
                      <p v-if="location" class="mc-pdp-store-loc">{{ location }}</p>
                    </div>
                  </div>
                  <button type="button" class="mc-pdp-btn mc-pdp-btn-ghost mc-pdp-share" @click="share">
                    <AppIcon :name="copied ? 'check' : 'share-2'" :size="15" aria-hidden="true" />
                    {{ copied ? 'Enlace copiado' : 'Copiar enlace' }}
                  </button>
                </section>
              </aside>
            </div>

            <!-- Ficha técnica cebra: nombre / valor de todas las features -->
            <section v-if="featureRows.length" id="mc-pdp-specs" class="mc-pdp-specs" aria-labelledby="mc-pdp-specs-title">
              <h2 id="mc-pdp-specs-title">Características de {{ product.name }}</h2>
              <dl class="mc-pdp-specs-list">
                <div v-for="[key, value] in featureRows" :key="key" class="mc-pdp-spec-row">
                  <dt>{{ key }}</dt>
                  <dd>{{ value }}</dd>
                </div>
              </dl>
            </section>

            <!-- Descripción -->
            <section v-if="product.description" class="mc-pdp-desc" aria-labelledby="mc-pdp-desc-title">
              <h2 id="mc-pdp-desc-title">Descripción</h2>
              <p>{{ product.description }}</p>
            </section>

            <!-- Opiniones de visitantes -->
            <section v-if="custom.show_reviews || custom.show_comments" class="mc-pdp-reviews">
              <ProductReviews
                :slug="slug"
                :product-id="product.id"
                :can-rate="custom.show_reviews"
                :can-comment="custom.show_comments"
                :avg="product.rating_avg"
                :count="product.rating_count || 0"
                :icon="ratingIcon"
              />
            </section>

            <!-- Relacionados -->
            <section v-if="related.length" class="mc-pdp-related" aria-labelledby="mc-pdp-rel-title">
              <h2 id="mc-pdp-rel-title">También te puede interesar</h2>
              <div class="mc-pdp-rel-grid">
                <TplProductCard
                  v-for="r in related" :key="r.id" class="mc-pdp-rel-card" :p="r"
                  :cat="catNameOf(r)" :brand="brandNameOf(r)" :desc="r.description || ''"
                  seal-shape="" :ph-size="24" @open="(r2) => router.push(productTo(r2))"
                />
              </div>
            </section>
          </article>
        </template>

        <!-- Producto dado de baja / error de red -->
        <div v-else class="mc-pdp-empty">
          <span class="mc-pdp-empty-ico" aria-hidden="true">
            <AppIcon :name="status === 'error' ? 'circle-alert' : 'package'" :size="26" />
          </span>
          <strong>{{ status === 'error' ? 'No pudimos cargar el producto' : 'Este producto ya no está disponible' }}</strong>
          <p>{{ status === 'error' ? 'Revisá tu conexión e intentá de nuevo.' : 'Puede que el comercio lo haya dado de baja del catálogo.' }}</p>
          <button v-if="status === 'error'" type="button" class="mc-pdp-btn mc-pdp-btn-ghost" @click="load">
            <AppIcon name="refresh" :size="16" aria-hidden="true" /> Reintentar
          </button>
          <RouterLink v-else class="mc-pdp-btn mc-pdp-btn-ghost" :to="catalogTo">
            <AppIcon name="arrow-left" :size="15" aria-hidden="true" /> Volver al catálogo
          </RouterLink>
        </div>
      </main>

      <!-- Lightbox de la foto: teleport a body para que position:fixed no
           quede atrapado por transforms de las animaciones de reveal. -->
      <Teleport to="body">
        <Transition name="mc-pdp-lb">
          <div
            v-if="lightbox" class="mc-pdp-lb" role="dialog" aria-modal="true"
            :aria-label="product ? `Imagen de ${product.name}` : 'Imagen del producto'" @click.self="closeLightbox"
          >
            <button ref="lbClose" type="button" class="mc-pdp-lb-close" aria-label="Cerrar imagen" @click="closeLightbox">
              <AppIcon name="x" :size="20" aria-hidden="true" />
            </button>
            <img class="mc-pdp-lb-img" :src="currentImage" :alt="product?.name || ''" />
          </div>
        </Transition>
      </Teleport>
    </div>
  </div>
</template>
