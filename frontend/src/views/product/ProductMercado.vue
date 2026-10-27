<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStorePage } from '../../composables/useStorePage.js'
import AppIcon from '../../components/AppIcon.vue'
import ProductStars from '../../components/ProductStars.vue'
import ProductReviews from '../../components/ProductReviews.vue'
import SwipeGallery from '../../components/store/SwipeGallery.vue'
import StickyBuyBar from '../../components/store/StickyBuyBar.vue'
import StTag from '../../components/store/StTag.vue'
import OfferSeal from '../../components/store/OfferSeal.vue'
import '../../assets/store-mercado.css'

// Ficha COMESTIBLES: foto en arco, tags de dieta, precio por unidad,
// selector de cantidad + nota que viaja en el mensaje de WhatsApp,
// ingredientes/alérgenos en cards punteadas y "Combiná con…".
const p = useStorePage()
const route = useRoute()
const router = useRouter()
const variant = computed(() => (p.pageTemplate.value === 'carta' ? 'carta' : 'mercado'))

watch(() => p.custom.value.show_catalog, (v) => { if (v === false) router.replace(p.homeTo.value) }, { immediate: true })

const status = ref('loading')
const product = computed(() => p.products.value.find((x) => String(x.id) === String(route.params.productId)) || null)
const catName = computed(() => p.catOf(product.value))
const rows = computed(() => p.featureRows(product.value))

// Tags de dieta (porción, peso, vegano, sin TACC...) desde features.
const dietaTone = (v) => (/vegano|vegetariano/.test(v) ? 'veg' : /tacc|gluten/.test(v) ? 'tacc' : /az[uú]car|keto|light/.test(v) ? 'sin-azucar' : '')
const dietaIcon = (v) => (/vegano|vegetariano/.test(v) ? 'leaf' : 'check')
const dietTags = computed(() => rows.value
  .filter(([k]) => /dieta|porci|peso|vegano|tacc|gluten|tama|unidad/i.test(k))
  .flatMap(([, v]) => String(v).split(/[,\/·]/).map((s) => s.trim().toLowerCase()).filter(Boolean))
  .slice(0, 4)
  .map((v) => ({ label: v, icon: dietaIcon(v), tone: dietaTone(v) })))

// "por unidad / por porción" si el producto lo declara.
const unitLabel = computed(() => {
  const hit = rows.value.find(([k]) => /porci|unidad|peso|tama/i.test(k))
  return hit ? `por ${String(hit[1]).toLowerCase()}` : ''
})
const featureBlock = (re) => rows.value.filter(([k]) => re.test(k)).flatMap(([k, v]) => String(v).split(/[,\/·]/).map((s) => s.trim()).filter(Boolean))
const ingredients = computed(() => featureBlock(/ingrediente/i))
const allergens = computed(() => featureBlock(/alergen|alérgen/i))
const restRows = computed(() => rows.value.filter(([k]) => !/dieta|porci|peso|vegano|tacc|gluten|tama|unidad|ingrediente|alergen|alérgen/i.test(k)))

// Cantidad + nota -> mensaje de WhatsApp.
const qty = ref(1)
const note = ref('')
const dec = () => { if (qty.value > 1) qty.value-- }
const inc = () => { if (qty.value < 99) qty.value++ }
const total = computed(() => (product.value ? p.effectivePrice(product.value) * qty.value : 0))
const waOrder = computed(() => {
  if (!product.value) return ''
  const lines = [`quiero pedir ${qty.value} × "${product.value.name}" (${p.formatARS(total.value)}).`]
  if (note.value.trim()) lines.push(`Nota: ${note.value.trim()}`)
  return p.waLink(lines)
})
const contactTo = computed(() => ({ ...p.homeTo.value, hash: '#contacto' }))
const ctaRef = ref(null)
const rail = computed(() => p.related(product.value, 6))
const copied = ref(false)
async function share() {
  try { await navigator.clipboard.writeText(window.location.href); copied.value = true; setTimeout(() => { copied.value = false }, 2500) } catch { /* noop */ }
}

async function load() {
  status.value = 'loading'
  try {
    await p.loadCatalog()
    status.value = product.value ? 'ready' : 'missing'
    if (product.value) document.title = `${product.value.name} · ${p.shopName.value}`
  } catch { status.value = 'error' }
}
onMounted(() => { if (p.custom.value.show_catalog !== false) load() })
</script>

<template>
<div class="sp-page-root mc" :data-var="variant">
  <main class="mc-pd">
    <nav class="mc-crumbs" aria-label="Ruta">
      <RouterLink :to="p.homeTo.value">Inicio</RouterLink>
      <AppIcon name="chevron-right" :size="13" aria-hidden="true" />
      <RouterLink :to="p.catalogTo.value">La carta</RouterLink>
      <template v-if="product"><AppIcon name="chevron-right" :size="13" aria-hidden="true" /><span aria-current="page">{{ product.name }}</span></template>
    </nav>

    <div v-if="status === 'loading'" class="mc-pd-sheet" aria-busy="true">
      <div class="mc-pd-gal sp-sk-block"></div>
      <div class="mc-pd-info"><span class="sp-sk-line short"></span><span class="sp-sk-line"></span><span class="sp-sk-line short"></span></div>
    </div>

    <template v-else-if="status === 'ready' && product">
      <article class="mc-pd-sheet">
        <div class="mc-pd-media">
          <span class="mc-pd-blob" aria-hidden="true"></span>
          <SwipeGallery class="mc-pd-gal" :images="product.image ? [product.image] : []" :alt="product.name" ratio="1 / 1" />
          <OfferSeal v-if="p.productOffer(product) != null" :pct="p.offerPct(product)" shape="circle" class="mc-pd-seal" />
        </div>

        <div class="mc-pd-info">
          <p class="mc-pd-cat">{{ catName || 'De la carta' }}</p>
          <h1 class="mc-pd-name">{{ product.name }}</h1>
          <ProductStars v-if="p.custom.value.show_reviews && product.rating_count" :avg="product.rating_avg" :count="product.rating_count" icon="heart" :size="14" show-value />
          <div v-if="dietTags.length" class="mc-pd-tags"><StTag v-for="t in dietTags" :key="t.label" kind="dieta" :label="t.label" :icon="t.icon" :tone="t.tone" /></div>

          <div class="mc-pd-price">
            <s v-if="p.productOffer(product) != null">{{ p.formatARS(product.price) }}</s>
            <strong>{{ p.formatARS(p.effectivePrice(product)) }}</strong>
            <em v-if="unitLabel">{{ unitLabel }}</em>
          </div>

          <!-- Cantidad + nota -->
          <div class="mc-qty" aria-live="polite">
            <button type="button" class="mc-qty-btn" aria-label="Quitar uno" @click="dec">−</button>
            <span class="mc-qty-n">{{ qty }}</span>
            <button type="button" class="mc-qty-btn" aria-label="Agregar uno" @click="inc">+</button>
            <span class="mc-qty-total">= {{ p.formatARS(total) }}</span>
          </div>
          <label class="mc-note">
            <span>Nota para tu pedido <em>(opcional)</em></span>
            <textarea v-model="note" maxlength="200" rows="2" placeholder="Sin cebolla, punto de cocción, para llevar…"></textarea>
            <small>{{ note.length }}/200</small>
          </label>

          <div ref="ctaRef" class="mc-pd-ctas">
            <a v-if="waOrder" class="mc-quick solid mc-pd-buy" :href="waOrder" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="17" /> Pedir · {{ p.formatARS(total) }}</a>
            <RouterLink v-else class="mc-quick mc-pd-buy" :to="contactTo"><AppIcon name="message-circle" :size="16" /> Consultar</RouterLink>
            <button type="button" class="mc-quick mc-pd-share" @click="share"><AppIcon :name="copied ? 'check' : 'share-2'" :size="15" /></button>
          </div>

          <!-- Ingredientes / alérgenos -->
          <div class="mc-pd-blocks">
            <section v-if="ingredients.length" class="mc-pd-block" aria-labelledby="mc-ing-t">
              <h2 id="mc-ing-t"><AppIcon name="checklist" :size="15" /> Ingredientes</h2>
              <p>{{ ingredients.join(' · ') }}</p>
            </section>
            <section v-if="allergens.length" class="mc-pd-block warn" aria-labelledby="mc-ale-t">
              <h2 id="mc-ale-t"><AppIcon name="triangle-alert" :size="15" /> Alérgenos</h2>
              <p>{{ allergens.join(' · ') }}</p>
            </section>
            <section v-if="restRows.length" class="mc-pd-block" aria-labelledby="mc-det-t">
              <h2 id="mc-det-t"><AppIcon name="info" :size="15" /> Detalles</h2>
              <dl><template v-for="[k, v] in restRows" :key="k"><dt>{{ k }}</dt><dd>{{ v }}</dd></template></dl>
            </section>
            <p v-if="product.description" class="mc-pd-desc">{{ product.description }}</p>
          </div>
        </div>
      </article>

      <ProductReviews
        v-if="p.custom.value.show_reviews || p.custom.value.show_comments"
        :slug="p.slug.value" :product-id="product.id"
        :can-rate="p.custom.value.show_reviews" :can-comment="p.custom.value.show_comments"
        :avg="product.rating_avg" :count="product.rating_count || 0" icon="heart"
      />

      <section v-if="rail.length" class="mc-pd-rail" aria-labelledby="mc-rel-t">
        <h2 id="mc-rel-t"><span>Combiná con…</span></h2>
        <div class="mc-today-track">
          <RouterLink v-for="r in rail" :key="r.id" class="mc-today-card" :to="p.productTo(r)">
            <span class="mc-today-media"><img v-if="r.image" :src="r.image" :alt="r.name" loading="lazy" /><span v-else class="mc-card-ph"><AppIcon name="coffee" :size="24" /></span></span>
            <span class="mc-today-info"><strong>{{ r.name }}</strong><span class="mc-today-price">{{ p.formatARS(p.effectivePrice(r)) }}</span></span>
          </RouterLink>
        </div>
      </section>

      <StickyBuyBar :target="ctaRef">
        <template #info>
          <span class="mc-sbb"><strong>{{ p.formatARS(total) }}</strong><em>{{ qty }} {{ qty === 1 ? 'unidad' : 'unidades' }}</em></span>
        </template>
        <a v-if="waOrder" class="mc-quick solid mc-sbb-cta" :href="waOrder" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" /> Pedir</a>
        <RouterLink v-else class="mc-quick mc-sbb-cta" :to="contactTo"><AppIcon name="message-circle" :size="16" /> Pedir</RouterLink>
      </StickyBuyBar>
    </template>

    <div v-else class="mc-empty">
      <span class="mc-empty-mark"><AppIcon :name="status === 'error' ? 'circle-alert' : 'coffee'" :size="26" /></span>
      <h2>{{ status === 'error' ? 'No pudimos cargar el producto' : 'Este plato ya no está en la carta' }}</h2>
      <p>{{ status === 'error' ? 'Revisá tu conexión e intentá de nuevo.' : 'Puede que lo hayan dado de baja.' }}</p>
      <button v-if="status === 'error'" type="button" class="mc-quick solid" style="margin-top:12px;height:50px" @click="load">Reintentar</button>
      <RouterLink v-else class="mc-quick" style="margin-top:12px;height:50px" :to="p.catalogTo.value">Volver a la carta</RouterLink>
    </div>
  </main>
</div>
</template>
