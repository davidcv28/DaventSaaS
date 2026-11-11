<script setup>
import { ref, computed, watch, inject, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeHostSlug } from '../../../config/env.js'
import { formatARS } from '../../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct, productDiscount, offerEndsLabel } from '../../../api/catalog.api.js'
import { storeContactLink, hasContactChannel } from '../../../api/stores.api.js'
import { useCartStore } from '../../../stores/cart.store.js'
import AppIcon from '../../../components/AppIcon.vue'
import ProductStars from '../../../components/ProductStars.vue'
import ProductReviews from '../../../components/ProductReviews.vue'
import { vReveal } from '../../../directives/reveal.js'
import TplProductCard from '../../../components/store/TplProductCard.vue'

// Ficha de producto estilo marketplace (/<slug>/producto/<id>) con la
// dirección de arte Raíz v2: galería 7/5, panel de compra sticky, ficha
// técnica cebra, opiniones y relacionados. Los datos salen del catálogo
// público (el backend solo devuelve productos activos de la tienda).
const ctx = inject('storePage')
const { slug, custom, shopName, location, loadPublicCatalog } = ctx
const route = useRoute()
const router = useRouter()
const cartStore = useCartStore()

// Venta online efectiva (la calcula el backend: ecommerce_enabled + fiscal
// completo). Con orders_enabled la ficha suma "Agregar al carrito" como CTA
// principal; sin él queda el flujo de consulta de siempre. El stock NO se
// expone en el catálogo público: el cart valida y avisa si no alcanza.
const ordersEnabled = computed(() => Boolean(ctx?.ordersEnabled?.value ?? ctx?.ordersEnabled))
// Cantidad del alta: el stepper alimenta el botón "Agregar al carrito" (y la
// barra fija móvil) y se cita en el mensaje de WhatsApp cuando es > 1.
const QTY_MAX = 99
const qty = ref(1)
const setQty = (n) => { qty.value = Math.min(QTY_MAX, Math.max(1, Math.round(Number(n)) || 1)) }
const adding = ref(false)
const added = ref(false)
let addedTimer = 0
async function addToCart() {
  if (adding.value || !product.value) return
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

// Lightbox de la foto principal: la ficha solo tiene una imagen por
// producto, así que el zoom es una vista ampliada (Esc/fondo/cierra).
const lightbox = ref(false)
let lbPrevFocus = null
const lbClose = ref(null)
function openLightbox() {
  if (!product.value?.image) return
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

// El glifo de la valoración acompaña la identidad del diseño (Raíz: estrella).
const ratingIcon = computed(() => 'star')

const product = computed(() => catalog.value.products.find((p) => String(p.id) === String(route.params.productId)) || null)
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
const eyebrowParts = computed(() => [categoryName.value, brandName.value].filter(Boolean))
// Lookup por producto para las tarjetas de "También te puede interesar".
const catNameOf = (p) => catalog.value.categories.find((c) => c.id === p.category)?.name || ''
const brandNameOf = (p) => catalog.value.brands.find((b) => b.id === p.brand)?.name || ''

// CTA principal: consulta por WhatsApp con el producto ya citado en el
// mensaje (el comercio recibe el interés concreto, como en un marketplace).
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
  <div class="sp-page-root rz-pdp-page">
    <main class="rz-pdp-wrap rz-pdp-main">
      <nav v-reveal class="rz-pdp-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <span v-if="custom.site_mode !== 'catalog'" aria-hidden="true">/</span>
        <RouterLink :to="catalogTo">Catálogo</RouterLink>
        <template v-if="categoryName">
          <span aria-hidden="true">/</span>
          <span>{{ categoryName }}</span>
        </template>
        <template v-if="product">
          <span aria-hidden="true">/</span>
          <span class="rz-pdp-crumb-here" aria-current="page">{{ product.name }}</span>
        </template>
      </nav>

      <!-- Carga: esqueleto con la misma composición que la ficha -->
      <div v-if="status === 'loading'" class="rz-pdp-sheet" aria-busy="true">
        <div class="rz-pdp-top">
          <div class="rz-pdp-skel-media"></div>
          <div class="rz-pdp-skel-buy">
            <span class="rz-pdp-skel-line short"></span>
            <span class="rz-pdp-skel-line tall"></span>
            <span class="rz-pdp-skel-line"></span>
            <span class="rz-pdp-skel-line"></span>
            <span class="rz-pdp-skel-line short"></span>
          </div>
        </div>
      </div>

      <template v-else-if="status === 'ready' && product">
        <article v-reveal class="rz-pdp-sheet">
          <div class="rz-pdp-top">
            <!-- Galería -->
            <figure class="rz-pdp-gallery">
              <div
                class="rz-frame rz-pdp-frame" :class="{ 'is-zoomable': product.image }"
                :role="product.image ? 'button' : undefined" :tabindex="product.image ? 0 : undefined"
                :aria-label="product.image ? `Ampliar imagen de ${product.name}` : undefined"
                @click="openLightbox" @keydown.enter.prevent="openLightbox" @keydown.space.prevent="openLightbox"
              >
                <img v-if="product.image" :src="product.image" :alt="product.name" decoding="async" fetchpriority="high" />
                <span v-else class="rz-pdp-ph" aria-hidden="true"><AppIcon name="package" :size="64" /></span>
                <span v-if="product.image" class="rz-pdp-zoom-hint" aria-hidden="true">
                  <AppIcon name="maximize" :size="13" /> Ampliar
                </span>
              </div>
              <figcaption class="rz-pdp-caption">
                <span class="rz-pdp-caption-cat">{{ categoryName || 'Producto' }}</span>
                <span class="rz-pdp-caption-id">Ref. {{ product.id }}</span>
              </figcaption>
              <span class="rz-plate rz-pdp-seal">{{ isNewProduct(product) ? 'Recién llegado' : 'Disponible' }}</span>
            </figure>

            <!-- Panel de compra (sticky en desktop) -->
            <aside class="rz-pdp-buy" aria-label="Información del producto">
              <div class="rz-pdp-buy-head">
                <p class="rz-eyebrow rz-pdp-kicker">
                  <span class="rz-eyebrow-num">01</span>
                  <template v-if="eyebrowParts.length">{{ eyebrowParts.join(' · ') }}</template>
                  <template v-else>Producto</template>
                </p>
                <button
                  type="button" class="rz-pdp-share" :aria-label="copied ? 'Link copiado' : 'Compartir producto'"
                  :title="copied ? 'Link copiado' : 'Compartir'" @click="share"
                >
                  <AppIcon :name="copied ? 'check' : 'share-2'" :size="16" />
                </button>
              </div>
              <h1 class="rz-pdp-name">{{ product.name }}</h1>
              <ProductStars
                v-if="custom.show_reviews && product.rating_count" class="rz-pdp-stars"
                :avg="product.rating_avg" :count="product.rating_count" :icon="ratingIcon" :size="15" show-value
              />

              <div class="rz-pdp-pricebox">
                <p class="rz-pdp-price-row">
                  <strong class="rz-pdp-price">{{ formatARS(effectivePrice(product)) }}</strong>
                  <span v-if="hasOffer" class="rz-tag rz-pdp-off">-{{ offerPct(product) }}%</span>
                </p>
                <p v-if="hasOffer" class="rz-pdp-old">Antes <s>{{ formatARS(product.price) }}</s></p>
                <p v-if="productDiscount(product)" class="rz-pdp-promo">
                  <AppIcon name="tag" :size="14" aria-hidden="true" />
                  <span>
                    Promo {{ productDiscount(product).name }}<span v-if="offerEndsLabel(productDiscount(product))" class="rz-pdp-promo-ends"> · {{ offerEndsLabel(productDiscount(product)) }}</span>
                  </span>
                </p>
                <img
                  v-if="productDiscount(product)?.campaign?.label_url" class="rz-pdp-campaign"
                  :src="productDiscount(product).campaign.label_url"
                  :alt="productDiscount(product).campaign.label_alt || productDiscount(product).campaign.name"
                  :width="productDiscount(product).campaign.label_width || undefined"
                  :height="productDiscount(product).campaign.label_height || undefined"
                  loading="lazy" decoding="async"
                />
                <p class="rz-pdp-stock">
                  <i aria-hidden="true"></i> En stock
                </p>
                <p class="rz-pdp-pay">
                  <AppIcon name="credit-card" :size="15" aria-hidden="true" />
                  Medios de pago, cuotas y envío se coordinan con el vendedor
                </p>
              </div>

              <div v-if="ordersEnabled" class="rz-pdp-qty" role="group" aria-label="Cantidad">
                <span class="rz-pdp-qty-lbl">Cantidad</span>
                <div class="rz-pdp-qty-ctl">
                  <button type="button" :disabled="qty <= 1" aria-label="Disminuir cantidad" @click="setQty(qty - 1)">
                    <AppIcon name="minus" :size="14" aria-hidden="true" />
                  </button>
                  <output class="rz-pdp-qty-num" aria-live="polite">{{ qty }}</output>
                  <button type="button" :disabled="qty >= QTY_MAX" aria-label="Aumentar cantidad" @click="setQty(qty + 1)">
                    <AppIcon name="plus" :size="14" aria-hidden="true" />
                  </button>
                </div>
              </div>

              <div class="rz-pdp-ctas">
                <button
                  v-if="ordersEnabled" type="button"
                  class="rz-btn rz-pdp-buy-btn rz-pdp-cart" :disabled="adding"
                  @click="addToCart"
                >
                  <AppIcon :name="added ? 'check' : 'shopping-cart'" :size="17" aria-hidden="true" />
                  {{ added ? 'Agregado al carrito' : 'Agregar al carrito' }}
                </button>
                <a
                  v-if="whatsappUrl" class="rz-btn rz-pdp-buy-btn" :class="{ 'rz-btn--ghost': ordersEnabled }"
                  :href="whatsappUrl" target="_blank" rel="noopener"
                >
                  <AppIcon name="whatsapp" :size="17" aria-hidden="true" /> Consultar por WhatsApp
                </a>
                <RouterLink v-else class="rz-btn rz-pdp-buy-btn" :to="contactTo">
                  <AppIcon name="message-circle" :size="17" aria-hidden="true" /> Consultar al vendedor
                </RouterLink>
                <RouterLink v-if="whatsappUrl && !ordersEnabled" class="rz-btn rz-btn--ghost" :to="contactTo">
                  <AppIcon name="mail" :size="15" aria-hidden="true" /> Enviar un mensaje
                </RouterLink>
                <RouterLink class="rz-pdp-backlink" :to="catalogTo">
                  <AppIcon name="arrow-left" :size="14" aria-hidden="true" /> Seguir explorando el catálogo
                </RouterLink>
              </div>

              <ul class="rz-pdp-seller">
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

          <!-- Ficha técnica: tabla cebra con hairlines -->
          <section v-if="featureRows.length" class="rz-pdp-sec" aria-labelledby="rz-pdp-specs-title">
            <div class="rz-pdp-sec-head">
              <p class="rz-eyebrow"><span class="rz-eyebrow-num">02</span> Ficha técnica</p>
              <h2 id="rz-pdp-specs-title" class="rz-pdp-sec-title">Características principales</h2>
            </div>
            <div class="rz-pdp-specs-wrap">
              <table class="rz-pdp-specs">
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
          <section v-if="product.description" class="rz-pdp-sec" aria-labelledby="rz-pdp-desc-title">
            <div class="rz-pdp-sec-head">
              <p class="rz-eyebrow"><span class="rz-eyebrow-num">03</span> Descripción</p>
              <h2 id="rz-pdp-desc-title" class="rz-pdp-sec-title">Sobre este producto</h2>
            </div>
            <p class="rz-pdp-desc">{{ product.description }}</p>
          </section>

          <!-- Opiniones de visitantes (valoraciones y/o comentarios premium) -->
          <div v-if="custom.show_reviews || custom.show_comments" class="rz-pdp-reviews">
            <ProductReviews
              :slug="slug"
              :product-id="product.id"
              :can-rate="custom.show_reviews"
              :can-comment="custom.show_comments"
              :avg="product.rating_avg"
              :count="product.rating_count || 0"
              :icon="ratingIcon"
            />
          </div>
        </article>

        <!-- CTA fija en móvil: precio + consulta siempre a mano -->
        <div class="rz-pdp-stick">
          <span class="rz-pdp-stick-info">
            <s v-if="hasOffer">{{ formatARS(product.price) }}</s>
            <strong>{{ formatARS(effectivePrice(product)) }}</strong>
          </span>
          <button
            v-if="ordersEnabled" type="button" class="rz-btn rz-pdp-stick-btn rz-pdp-stick-cart"
            :disabled="adding" :aria-label="added ? 'Agregado al carrito' : 'Agregar al carrito'" @click="addToCart"
          >
            <AppIcon :name="added ? 'check' : 'shopping-cart'" :size="16" aria-hidden="true" />
          </button>
          <a v-if="whatsappUrl" class="rz-btn rz-pdp-stick-btn" :href="whatsappUrl" target="_blank" rel="noopener">
            <AppIcon name="whatsapp" :size="16" aria-hidden="true" /> Consultar
          </a>
          <RouterLink v-else class="rz-btn rz-pdp-stick-btn" :to="contactTo">
            <AppIcon name="message-circle" :size="16" aria-hidden="true" /> Consultar
          </RouterLink>
        </div>

        <!-- Relacionados -->
        <section v-if="related.length" v-reveal="80" class="rz-pdp-related" aria-labelledby="rz-pdp-rel-title">
          <div class="rz-pdp-related-head">
            <p class="rz-eyebrow"><span class="rz-eyebrow-num">04</span> Seguir explorando</p>
            <h2 id="rz-pdp-rel-title" class="rz-pdp-sec-title">También te puede interesar</h2>
          </div>
          <div class="rz-pdp-rel-grid">
            <TplProductCard
              v-for="r in related" :key="r.id" class="rz-pdp-rel-card" :p="r"
              :cat="catNameOf(r)" :brand="brandNameOf(r)"
              seal-shape="" :ph-size="24" :go="false" @open="(r2) => router.push(productTo(r2))"
            />
          </div>
        </section>
      </template>

      <!-- Producto dado de baja / error de red -->
      <div v-else class="rz-pdp-empty">
        <span class="rz-pdp-empty-ico" aria-hidden="true">
          <AppIcon :name="status === 'error' ? 'circle-alert' : 'package'" :size="26" />
        </span>
        <strong>{{ status === 'error' ? 'No pudimos cargar el producto' : 'Este producto ya no está disponible' }}</strong>
        <p>{{ status === 'error' ? 'Revisá tu conexión e intentá de nuevo.' : 'Puede que el comercio lo haya dado de baja del catálogo.' }}</p>
        <button v-if="status === 'error'" type="button" class="rz-btn rz-btn--ghost" @click="load">
          <AppIcon name="refresh" :size="16" aria-hidden="true" /> Reintentar
        </button>
        <RouterLink v-else class="rz-btn rz-btn--ghost" :to="catalogTo">
          <AppIcon name="arrow-left" :size="15" aria-hidden="true" /> Volver al catálogo
        </RouterLink>
      </div>
    </main>

    <!-- Lightbox de la foto: teleport a body para que position:fixed no
         quede atrapado por transforms de las animaciones de reveal. Colores
         neutros propios: fuera del árbol .store-page no heredan tokens. -->
    <Teleport to="body">
      <Transition name="rz-pdp-lb">
        <div
          v-if="lightbox" class="rz-pdp-lb" role="dialog" aria-modal="true"
          :aria-label="product ? `Imagen de ${product.name}` : 'Imagen del producto'" @click.self="closeLightbox"
        >
          <button ref="lbClose" type="button" class="rz-pdp-lb-close" aria-label="Cerrar imagen" @click="closeLightbox">
            <AppIcon name="x" :size="20" aria-hidden="true" />
          </button>
          <img class="rz-pdp-lb-img" :src="product?.image" :alt="product?.name || ''" />
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
/* Zoom de la foto principal: la ficha solo tiene una imagen, así que el
   frame entero abre el lightbox (rol=button solo cuando hay foto). */
.rz-pdp-frame.is-zoomable { cursor: zoom-in; }
.rz-pdp-frame.is-zoomable:focus-visible {
  outline: 2px solid var(--rz-focus, var(--rz-ink, #0f172a));
  outline-offset: 3px;
}
.rz-pdp-zoom-hint {
  position: absolute;
  right: 12px;
  bottom: 12px;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 11px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--rz-ink, #0f172a) 78%, transparent);
  color: var(--rz-bg, #fff);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .05em;
  text-transform: uppercase;
  pointer-events: none;
  opacity: 0;
  translate: 0 6px;
  transition: opacity .18s ease-out, translate .18s ease-out;
}
@media (hover: hover) and (pointer: fine) {
  .rz-pdp-frame.is-zoomable:hover .rz-pdp-zoom-hint,
  .rz-pdp-frame.is-zoomable:focus-visible .rz-pdp-zoom-hint { opacity: 1; translate: 0 0; }
}
@media (hover: none) { .rz-pdp-zoom-hint { display: none; } }

/* Stepper de cantidad: misma retícula que el resto del panel de compra. */
.rz-pdp-qty {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-block: 12px;
  border-block: 1px solid var(--rz-line, var(--sp-line, #e2e8f0));
}
.rz-pdp-qty-lbl {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--rz-muted, var(--sp-muted, #64748b));
}
.rz-pdp-qty-ctl {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--rz-line, var(--sp-line, #e2e8f0));
  border-radius: var(--rz-rad-sm, 8px);
  background: var(--rz-surface, var(--sp-card, #fff));
  overflow: hidden;
}
.rz-pdp-qty-ctl button {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border: 0;
  background: transparent;
  color: var(--rz-ink, var(--sp-ink, #0f172a));
  cursor: pointer;
  transition: background .15s ease-out;
}
.rz-pdp-qty-ctl button:hover:not(:disabled) { background: var(--rz-surface-2, var(--sp-soft, #f1f5f9)); }
.rz-pdp-qty-ctl button:disabled { opacity: .35; cursor: default; }
.rz-pdp-qty-num {
  min-width: 44px;
  text-align: center;
  font-family: var(--rz-display, inherit);
  font-size: 16px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--rz-ink, var(--sp-ink, #0f172a));
}

/* Lightbox (teleport a body): neutro propio, no depende de tokens --rz-*. */
.rz-pdp-lb {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgb(8 10 16 / .88);
  backdrop-filter: blur(6px);
}
.rz-pdp-lb-img {
  max-width: min(92vw, 1100px);
  max-height: 88dvh;
  width: auto;
  height: auto;
  object-fit: contain;
  border-radius: 10px;
  box-shadow: 0 30px 80px -20px rgb(0 0 0 / .6);
}
.rz-pdp-lb-close {
  position: absolute;
  top: max(16px, env(safe-area-inset-top, 0px));
  right: max(16px, env(safe-area-inset-right, 0px));
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border: 1px solid rgb(255 255 255 / .25);
  border-radius: 50%;
  background: rgb(255 255 255 / .1);
  color: #fff;
  cursor: pointer;
  transition: background .15s ease-out;
}
.rz-pdp-lb-close:hover { background: rgb(255 255 255 / .22); }
.rz-pdp-lb-enter-active, .rz-pdp-lb-leave-active { transition: opacity .2s ease-out; }
.rz-pdp-lb-enter-from, .rz-pdp-lb-leave-to { opacity: 0; }
.rz-pdp-lb-enter-active .rz-pdp-lb-img, .rz-pdp-lb-leave-active .rz-pdp-lb-img { transition: scale .25s var(--rz-ease-out, ease); }
.rz-pdp-lb-enter-from .rz-pdp-lb-img, .rz-pdp-lb-leave-to .rz-pdp-lb-img { scale: .96; }
@media (prefers-reduced-motion: reduce) {
  .rz-pdp-lb-enter-active, .rz-pdp-lb-leave-active,
  .rz-pdp-lb-enter-active .rz-pdp-lb-img, .rz-pdp-lb-leave-active .rz-pdp-lb-img { transition: none; }
  .rz-pdp-zoom-hint { transition: none; }
}
</style>
