<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useStorePage } from '../composables/useStorePage.js'
import AppIcon from '../components/AppIcon.vue'
import MarqueeBand from '../components/store/MarqueeBand.vue'
import BentoGrid from '../components/store/BentoGrid.vue'
import SpecStrip from '../components/store/SpecStrip.vue'
import TrustBar from '../components/store/TrustBar.vue'
import StTag from '../components/store/StTag.vue'
import OfferSeal from '../components/store/OfferSeal.vue'
import { vReveal } from '../directives/reveal.js'
import '../assets/store-circuit.css'

// Familia TECNOLOGÍA — "Circuit". Ficha técnica viva: el producto flota
// sobre una grilla de ingeniería con halo de acento y los datos hablan —
// callouts conectados al hardware, specs en mono, bento rígido y
// comparador. Variantes: 'circuit' (densidad dark, halo fuerte) y 'lab'
// (claro minimal: mismo esqueleto, halo suave, menos brillo).
const p = useStorePage()
const { custom, shopName, location, pageTemplate, hasAbout, showContact, showCatalog, heroTitle } = p
const variant = computed(() => (pageTemplate.value === 'lab' ? 'lab' : 'circuit'))

// El producto "héroe" del visor: el primero con foto y features — sus
// atributos alimentan los callouts conectados (nunca se inventan specs).
const heroProduct = computed(() =>
  productsTop.value.find((x) => x.image && p.featureRows(x).length)
  || productsTop.value.find((x) => x.image)
  || null)
const heroImg = computed(() => heroProduct.value?.image || p.heroImage.value)

// Callouts: hasta 3 atributos reales del producto destacado, con línea
// conectora. En mobile pasan a SpecStrip bajo el visor.
const SPEC_ICONS = [/procesador|cpu|chip|ram|memoria|almacen/, /bateria|carga|autonom/, /pantalla|display|camara|resol/]
const SPEC_ICON_OF = (k) => (/bateria|carga|autonom/.test(k) ? 'zap' : /pantalla|display|camara|resol/.test(k) ? 'monitor' : 'gem')
const callouts = computed(() => p.featureRows(heroProduct.value).slice(0, 3).map(([k, v], i) => ({ key: k, value: v, icon: SPEC_ICON_OF(k.toLowerCase()), pos: i })))

// Titular en 2 líneas con una palabra en gradiente de acento.
const titleWords = computed(() => heroTitle.value.split(/\s+/).filter(Boolean))

// Contadores técnicos (datos reales; "garantía" solo si hay años).
const counters = computed(() => {
  const out = [
    { icon: 'package', value: `+${p.products.value.length}`, label: p.products.value.length === 1 ? 'producto' : 'productos' },
    { icon: 'terminal', value: String(p.brands.value.length), label: p.brands.value.length === 1 ? 'marca' : 'marcas' }
  ]
  if (custom.value.about_years) out.push({ icon: 'shield-check', value: `${custom.value.about_years}`, label: 'años de garantía' })
  else if (location.value) out.push({ icon: 'map-pin', value: '1', label: location.value })
  return out.slice(0, 3)
})

// Bento: destacado 2x2 = primer producto con oferta; specs overlay.
const bentoItems = computed(() => p.products.value.slice(0, 9))
const isOffer = (x) => p.productOffer(x) != null
const isFeatured = (x) => p.isNewProduct(x) || x.id === heroProduct.value?.id
const specsOf = (x) => p.featureRows(x).slice(0, 3).map(([k, v]) => `${v}`)

// Comparador: necesita 2+ productos que compartan al menos 2 claves de
// features (schema de la misma categoría, si existe).
const compare = computed(() => {
  const withFeat = p.products.value.filter((x) => p.featureRows(x).length >= 2)
  if (withFeat.length < 2) return null
  const prods = withFeat.slice(0, 3)
  const keys = [...new Set(prods.flatMap((x) => p.featureRows(x).map(([k]) => k)))].slice(0, 6)
  if (!keys.length) return null
  const cell = (x, k) => p.featureRows(x).find(([fk]) => fk === k)?.[1] || '—'
  return { prods, keys, cell }
})

// Eyebrow del hero: marca o categoría real del producto destacado.
const catEyebrow = computed(() => p.brandOf(heroProduct.value) || p.catOf(heroProduct.value) || 'Hardware')

const bandItems = computed(() => {
  const items = [{ icon: 'terminal', text: shopName.value }]
  p.brands.value.slice(0, 6).forEach((b) => items.push({ icon: 'dot', text: b.name }))
  if (p.offerCount.value) items.push({ icon: 'percent', text: `${p.offerCount.value} ${p.offerCount.value === 1 ? 'oferta' : 'ofertas'}` })
  return items.length > 2 ? items : []
})
const productsTop = computed(() => p.products.value)

// Scan-line del panel nocturno (circuit): se pausa cuando el hero sale
// de pantalla — la clase .off corta la animación decorativa.
const heroEl = ref(null)
let heroIO = null

onMounted(() => {
  p.loadCatalog()
  if (typeof IntersectionObserver !== 'undefined' && heroEl.value) {
    heroIO = new IntersectionObserver(([e]) => heroEl.value?.classList.toggle('off', !e.isIntersecting))
    heroIO.observe(heroEl.value)
  }
})
onBeforeUnmount(() => heroIO?.disconnect())
</script>

<template>
<div class="sp-page-root ci" :data-var="variant">
  <!-- ===== Hero técnico: producto flotando + callouts conectados ===== -->
  <header ref="heroEl" class="ci-hero">
    <div class="ci-hero-grid-bg" aria-hidden="true"></div>
    <div class="ci-hero-stage">
      <div v-if="heroImg" class="ci-hero-product" v-reveal>
        <img :src="heroImg" :alt="heroProduct ? heroProduct.name : `Producto de ${shopName}`" fetchpriority="high" decoding="async" />
        <!-- Líneas conectoras (solo desktop): punto → línea → etiqueta -->
        <svg class="ci-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <line v-for="(c, i) in callouts" :key="c.key" :x1="i === 1 ? 82 : 18" :y1="20 + i * 28" :x2="i === 1 ? 62 : 38" :y2="32 + i * 18" pathLength="1" />
        </svg>
        <span v-for="(c, i) in callouts" :key="`dot-${c.key}`" class="ci-dot" :style="{ left: `${i === 1 ? 62 : 38}%`, top: `${32 + i * 18}%` }"></span>
        <div v-for="(c, i) in callouts" :key="`lb-${c.key}`" class="ci-callout" :class="{ right: i === 1 }" :style="{ top: `${14 + i * 28}%` }">
          <AppIcon :name="c.icon" :size="13" /><strong>{{ c.key }}</strong><em>{{ c.value }}</em>
        </div>
      </div>
      <div class="ci-hero-copy">
        <p class="ci-eyebrow"><AppIcon name="terminal" :size="13" /> {{ catEyebrow }}</p>
        <h1 class="ci-title">
          <span v-for="(w, i) in titleWords" :key="i" :class="{ acc: i === titleWords.length - 1 && titleWords.length > 1 }">{{ w + (i < titleWords.length - 1 ? ' ' : '') }}</span>
        </h1>
        <p v-if="custom.description" class="ci-lede">{{ custom.description.slice(0, 90) }}{{ custom.description.length > 90 ? '…' : '' }}</p>
        <div class="ci-hero-ctas">
          <RouterLink v-if="showCatalog" class="ci-cta" :to="p.catalogTo.value">Ver catálogo <AppIcon name="arrow-right" :size="15" /></RouterLink>
          <a v-if="p.waBase.value" class="ci-cta ghost" :href="p.waGeneral.value" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="15" /> Consultar</a>
        </div>
      </div>
      <!-- En mobile los callouts se vuelven SpecStrip bajo el producto -->
      <SpecStrip v-if="callouts.length" class="ci-hero-strip" :items="callouts.map((c) => ({ icon: c.icon, value: c.value, label: c.key }))" />
    </div>
    <TrustBar v-if="counters.length" class="ci-trust" :items="counters" />
  </header>

  <MarqueeBand v-if="bandItems.length" :items="bandItems" :speed="24" />

  <!-- ===== Marcas en riel ===== -->
  <nav v-if="p.brands.value.length" class="ci-brands" aria-label="Marcas">
    <span class="ci-brands-label">Marcas</span>
    <ul>
      <li v-for="b in p.brands.value" :key="b.id">{{ b.name }}</li>
    </ul>
  </nav>

  <main class="ci-main">
    <!-- ===== Bento de productos: destacado 2x2 con spec overlay ===== -->
    <section v-if="bentoItems.length" class="ci-bento" aria-label="Productos">
      <BentoGrid :items="bentoItems" :is-offer="isOffer" :is-featured="isFeatured" v-slot="{ item, span }">
        <RouterLink class="ci-cell" :to="p.productTo(item)" :aria-label="`${item.name} — ${p.formatARS(p.effectivePrice(item))}`">
          <img v-if="item.image" :src="item.image" :alt="item.name" loading="lazy" decoding="async" />
          <span v-else class="ci-cell-ph"><AppIcon name="package" :size="30" /></span>
          <OfferSeal v-if="p.productOffer(item) != null" :pct="p.offerPct(item)" shape="corner" />
          <span class="ci-cell-info">
            <span class="ci-cell-name">{{ item.name }}</span>
            <span class="ci-cell-row">
              <span class="ci-cell-specs"><StTag v-for="s in specsOf(item)" :key="s" kind="spec" :label="s" /></span>
              <span class="ci-cell-price"><s v-if="p.productOffer(item) != null">{{ p.formatARS(item.price) }}</s>{{ p.formatARS(p.effectivePrice(item)) }}</span>
            </span>
          </span>
          <span v-if="span === 'b22' && specsOf(item).length" class="ci-cell-overlay">
            <em v-for="s in specsOf(item)" :key="s">{{ s }}</em>
          </span>
        </RouterLink>
      </BentoGrid>
    </section>

    <section v-else-if="showCatalog" class="ci-empty">
      <span class="ci-empty-mark"><AppIcon name="monitor" :size="26" /></span>
      <h2>Sistema en espera</h2>
      <p>{{ shopName }} está cargando su inventario. Consultanos por el equipo que buscás.</p>
      <a v-if="p.waBase.value" class="ci-cta" :href="p.waGeneral.value" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="15" /> Consultar stock</a>
    </section>

    <!-- ===== Comparador ===== -->
    <section v-if="compare" v-reveal class="ci-compare" aria-labelledby="ci-cmp-t">
      <h2 id="ci-cmp-t">Comparar</h2>
      <div class="ci-compare-scroll">
        <table>
          <thead>
            <tr><th class="ci-cmp-key">Spec</th><th v-for="x in compare.prods" :key="x.id"><RouterLink :to="p.productTo(x)">{{ x.name }}</RouterLink></th></tr>
          </thead>
          <tbody>
            <tr v-for="k in compare.keys" :key="k">
              <th class="ci-cmp-key">{{ k }}</th>
              <td v-for="x in compare.prods" :key="x.id">{{ compare.cell(x, k) }}</td>
            </tr>
            <tr>
              <th class="ci-cmp-key">Precio</th>
              <td v-for="x in compare.prods" :key="x.id" class="ci-cmp-price">{{ p.formatARS(p.effectivePrice(x)) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ===== Soporte / contacto en cards ===== -->
    <section v-if="showContact || p.waBase.value || p.hours.value.length" v-reveal id="contacto" class="ci-support" aria-labelledby="ci-sup-t">
      <h2 id="ci-sup-t">Soporte</h2>
      <div class="ci-support-grid">
        <a v-if="p.waBase.value" class="ci-sup-card" :href="p.waGeneral.value" target="_blank" rel="noopener">
          <AppIcon name="whatsapp" :size="20" /><strong>WhatsApp directo</strong><span>Respuesta del local</span>
        </a>
        <div v-if="location" class="ci-sup-card"><AppIcon name="map-pin" :size="20" /><strong>{{ location }}</strong><span v-if="p.openNow.value" :data-state="p.openNow.value.state">{{ p.openNow.value.text }}</span></div>
        <div v-if="custom.about_years" class="ci-sup-card"><AppIcon name="shield-check" :size="20" /><strong>+{{ custom.about_years }} años</strong><span>Trayectoria y garantía</span></div>
      </div>
    </section>
  </main>
</div>
</template>
