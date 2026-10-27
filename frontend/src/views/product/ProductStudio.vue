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
import '../../assets/store-studio.css'

// Ficha SERVICIOS: cabecera 16:10, Tag-Modalidad, "Qué incluye" y
// "Qué necesitás" desde features con checks, galería/reseñas, CTA doble
// (Consultar + Llamar) y riel de otros servicios/productos.
const p = useStorePage()
const route = useRoute()
const router = useRouter()
const variant = computed(() => (p.pageTemplate.value === 'proceso' ? 'proceso' : 'studio'))

watch(() => p.custom.value.show_catalog, (v) => { if (v === false) router.replace(p.homeTo.value) }, { immediate: true })

const status = ref('loading')
const product = computed(() => p.products.value.find((x) => String(x.id) === String(route.params.productId)) || null)
const catName = computed(() => p.catOf(product.value))
const rows = computed(() => p.featureRows(product.value))
const duration = computed(() => p.featureValues(product.value, 'duraci', 'tiempo')[0] || '')
const modalities = computed(() => (p.custom.value.service_ask_address !== false ? ['A domicilio', 'Presencial'] : ['Presencial']))

const featureBlock = (re) => rows.value.filter(([k]) => re.test(k)).flatMap(([k, v]) => String(v).split(/[,\/·]/).map((s) => s.trim()).filter(Boolean))
const includes = computed(() => featureBlock(/incluye|incluid|cubre/i))
const needs = computed(() => featureBlock(/necesit|requer|requisit/i))
const restRows = computed(() => rows.value.filter(([k]) => !/incluye|incluid|cubre|necesit|requer|requisit|duraci|tiempo/i.test(k)))

const waConsult = computed(() => (product.value ? p.waProduct(product.value, ['me gustaría un presupuesto.']) : ''))
const phone = computed(() => (p.waNumber.value ? `tel:+${p.waNumber.value}` : ''))
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
<div class="sp-page-root sd" :data-var="variant">
  <main class="sd-pd">
    <nav class="sd-crumbs" aria-label="Ruta">
      <RouterLink :to="p.homeTo.value">Inicio</RouterLink>
      <AppIcon name="chevron-right" :size="13" aria-hidden="true" />
      <RouterLink :to="p.catalogTo.value">Catálogo</RouterLink>
      <template v-if="product"><AppIcon name="chevron-right" :size="13" aria-hidden="true" /><span aria-current="page">{{ product.name }}</span></template>
    </nav>

    <div v-if="status === 'loading'" class="sd-pd-sheet" aria-busy="true">
      <div class="sd-pd-gal sp-sk-block"></div>
      <div class="sd-pd-info"><span class="sp-sk-line short"></span><span class="sp-sk-line"></span><span class="sp-sk-line short"></span></div>
    </div>

    <template v-else-if="status === 'ready' && product">
      <article class="sd-pd-sheet">
        <SwipeGallery class="sd-pd-gal" :images="product.image ? [product.image] : []" :alt="product.name" ratio="16 / 10" />

        <div class="sd-pd-info">
          <p class="sd-pd-cat">{{ catName || 'Servicio' }}</p>
          <h1 class="sd-pd-name">{{ product.name }}</h1>
          <div class="sd-pd-tags">
            <StTag v-for="m in modalities" :key="m" kind="modalidad" :label="m" :icon="m === 'A domicilio' ? 'truck' : 'map-pin'" />
            <StTag v-if="duration" kind="modalidad" :label="duration" icon="clock" />
          </div>
          <ProductStars v-if="p.custom.value.show_reviews && product.rating_count" :avg="product.rating_avg" :count="product.rating_count" icon="star" :size="14" show-value />

          <div class="sd-pd-price">
            <s v-if="p.productOffer(product) != null">{{ p.formatARS(product.price) }}</s>
            <strong>{{ p.formatARS(p.effectivePrice(product)) }}</strong>
            <OfferSeal v-if="p.productOffer(product) != null" :pct="p.offerPct(product)" shape="ribbon" small />
          </div>

          <div ref="ctaRef" class="sd-pd-ctas">
            <a v-if="waConsult" class="sd-cta" :href="waConsult" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" /> Consultar</a>
            <RouterLink v-else class="sd-cta" :to="contactTo"><AppIcon name="message-circle" :size="16" /> Consultar</RouterLink>
            <a v-if="phone" class="sd-cta ghost" :href="phone"><AppIcon name="phone" :size="15" /> Llamar</a>
            <button type="button" class="sd-cta ghost icon" :aria-label="copied ? 'Link copiado' : 'Compartir'" @click="share"><AppIcon :name="copied ? 'check' : 'share-2'" :size="16" /></button>
          </div>

          <!-- Qué incluye / Qué necesitás -->
          <section v-if="includes.length" class="sd-pd-block" aria-labelledby="sd-inc-t">
            <h2 id="sd-inc-t">Qué incluye</h2>
            <ul><li v-for="it in includes" :key="it"><AppIcon name="check" :size="18" /> {{ it }}</li></ul>
          </section>
          <section v-if="needs.length" class="sd-pd-block" aria-labelledby="sd-need-t">
            <h2 id="sd-need-t">Qué necesitás</h2>
            <ul><li v-for="it in needs" :key="it"><AppIcon name="dot" :size="12" /> {{ it }}</li></ul>
          </section>
          <section v-if="restRows.length" class="sd-pd-block" aria-labelledby="sd-det-t">
            <h2 id="sd-det-t">Detalles</h2>
            <dl><template v-for="[k, v] in restRows" :key="k"><dt>{{ k }}</dt><dd>{{ v }}</dd></template></dl>
          </section>
          <p v-if="product.description" class="sd-pd-desc">{{ product.description }}</p>
        </div>
      </article>

      <ProductReviews
        v-if="p.custom.value.show_reviews || p.custom.value.show_comments"
        :slug="p.slug.value" :product-id="product.id"
        :can-rate="p.custom.value.show_reviews" :can-comment="p.custom.value.show_comments"
        :avg="product.rating_avg" :count="product.rating_count || 0" icon="star"
      />

      <section v-if="rail.length" class="sd-pd-rail" aria-labelledby="sd-rel-t">
        <h2 id="sd-rel-t">Otros servicios</h2>
        <ul class="sd-svc-list">
          <li v-for="r in rail" :key="r.id">
            <RouterLink class="sd-svc" :to="p.productTo(r)">
              <span class="sd-svc-icon"><img v-if="r.image" :src="r.image" alt="" loading="lazy" class="sd-svc-thumb" /><AppIcon v-else name="wrench" :size="22" /></span>
              <span class="sd-svc-body"><strong>{{ r.name }}</strong><span v-if="r.description" class="sd-svc-desc">{{ r.description }}</span></span>
              <span class="sd-svc-price">{{ p.formatARS(p.effectivePrice(r)) }}</span>
            </RouterLink>
          </li>
        </ul>
      </section>

      <StickyBuyBar :target="ctaRef">
        <template #info>
          <span class="sd-sbb"><strong>{{ p.formatARS(p.effectivePrice(product)) }}</strong><em>Presupuesto sin cargo</em></span>
        </template>
        <a v-if="waConsult" class="sd-cta sd-sbb-cta" :href="waConsult" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="15" /> Consultar</a>
        <RouterLink v-else class="sd-cta sd-sbb-cta" :to="contactTo"><AppIcon name="message-circle" :size="15" /> Consultar</RouterLink>
        <a v-if="phone" class="sd-cta ghost sd-sbb-cta" :href="phone"><AppIcon name="phone" :size="15" /> Llamar</a>
      </StickyBuyBar>
    </template>

    <div v-else class="sd-empty">
      <span class="sd-empty-mark"><AppIcon :name="status === 'error' ? 'circle-alert' : 'wrench'" :size="26" /></span>
      <h2>{{ status === 'error' ? 'No pudimos cargar la ficha' : 'Esta ficha ya no está disponible' }}</h2>
      <p>{{ status === 'error' ? 'Revisá tu conexión e intentá de nuevo.' : 'Puede que la hayan dado de baja.' }}</p>
      <button v-if="status === 'error'" type="button" class="sd-cta" style="margin-top:12px" @click="load">Reintentar</button>
      <RouterLink v-else class="sd-cta" style="margin-top:12px" :to="p.catalogTo.value">Volver al catálogo</RouterLink>
    </div>
  </main>
</div>
</template>
