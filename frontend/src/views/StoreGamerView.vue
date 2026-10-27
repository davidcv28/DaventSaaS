<script setup>
import { computed, onMounted } from 'vue'
import { useStorePage } from '../composables/useStorePage.js'
import { productDiscount, offerEndsLabel } from '../api/catalog.api.js'
import AppIcon from '../components/AppIcon.vue'
import MarqueeBand from '../components/store/MarqueeBand.vue'
import TrustBar from '../components/store/TrustBar.vue'
import StepRail from '../components/store/StepRail.vue'
import OfferSeal from '../components/store/OfferSeal.vue'
import ScheduleCard from '../components/store/ScheduleCard.vue'
import { vReveal } from '../directives/reveal.js'
import '../assets/store-gamer.css'

// Familia GAMER — se compra por spec y precio. El cliente de hardware/
// periféricos/merch dev compara: en 5 segundos necesita ver qué se vende,
// cuánto cuesta y con qué viene (los features son specs de primera clase).
// Variantes: 'arena' (tablero esports — HUD, clip-path, Orbitron) y
// 'terminal' (consola de fósforo — ventana, prompt, log de arranque).
const p = useStorePage()
const { custom, shopName, location, pageTemplate, heroTitle, heroTitleIsName, showCatalog } = p
const variant = computed(() => (pageTemplate.value === 'terminal' ? 'terminal' : 'arena'))

// ===== Ofertas reales =====
const offers = computed(() => p.products.value.filter((x) => p.productOffer(x) != null))
const rankedOffers = computed(() => [...offers.value].sort((a, b) => p.offerPct(b) - p.offerPct(a)))
const topDeal = computed(() => rankedOffers.value[0] || null)
const maxPct = computed(() => (topDeal.value ? p.offerPct(topDeal.value) : 0))
const savings = (prod) => Math.max(0, Number(prod.price) - p.effectivePrice(prod))
const endsLabel = computed(() => {
  const d = topDeal.value ? productDiscount(topDeal.value) : null
  return offerEndsLabel(d) || offerEndsLabel(p.catalog.value?.promotions?.[0]) || ''
})
const endsOf = (prod) => offerEndsLabel(productDiscount(prod))

// La "player card" protagonista: mejor oferta, si no el primero con specs.
const star = computed(() => topDeal.value || p.products.value[0] || null)

// Specs en chips: las características reales del producto (featureRows).
const specChips = (prod, n = 3) => p.featureRows(prod).slice(0, n).map(([k, v]) => `${k}: ${v}`)

const railOffers = computed(() => rankedOffers.value.slice(0, 4))
const gridItems = computed(() => {
  const rest = p.products.value.filter((x) => x !== star.value)
  return rest.slice(0, 9)
})
const extraCount = computed(() => Math.max(0, p.products.value.length - gridItems.value.length - (star.value ? 1 : 0)))

// Stats del tablero / líneas del log (todo dato real).
const hudChips = computed(() => [
  p.products.value.length ? { icon: 'package', text: `${p.products.value.length} ítems` } : null,
  offers.value.length ? { icon: 'percent', text: `${offers.value.length} en oferta` } : null,
  location.value ? { icon: 'map-pin', text: location.value } : null,
  p.openNow.value ? { icon: 'clock', text: p.openNow.value.text } : null
].filter(Boolean))
const boardStats = computed(() => [
  p.products.value.length ? { value: `${p.products.value.length}`, label: 'productos' } : null,
  offers.value.length ? { value: `${offers.value.length}`, label: 'ofertas' } : null,
  maxPct.value ? { value: `-${maxPct.value}%`, label: 'mejor drop' } : null,
  p.brands.value.length ? { value: `${p.brands.value.length}`, label: 'marcas' } : null
].filter(Boolean).slice(0, 4))
const bootLines = computed(() => [
  `[ ok ] tienda inicializada — ${shopName.value}`,
  p.products.value.length ? `[ ok ] catálogo indexado: ${p.products.value.length} ítems` : null,
  offers.value.length ? `[ ok ] ofertas detectadas: ${offers.value.length}` : null,
  location.value ? `[ ok ] ubicación: ${location.value}` : null
].filter(Boolean))

const bandItems = computed(() => [
  { icon: 'zap', text: shopName.value },
  offers.value.length ? { icon: 'percent', text: `${offers.value.length} ${offers.value.length === 1 ? 'oferta activa' : 'ofertas activas'}` } : null,
  endsLabel.value ? { icon: 'clock', text: endsLabel.value } : null,
  p.brands.value.length ? { icon: 'tag', text: `${p.brands.value.length} ${p.brands.value.length === 1 ? 'marca' : 'marcas'}` } : null,
  location.value ? { icon: 'map-pin', text: location.value } : null
].filter(Boolean))
const trustItems = computed(() => [
  offers.value.length ? { icon: 'percent', value: `${offers.value.length}`, label: offers.value.length === 1 ? 'oferta activa' : 'ofertas activas' } : null,
  maxPct.value ? { icon: 'tag', value: `-${maxPct.value}%`, label: 'descuento máximo' } : null,
  location.value ? { icon: 'map-pin', label: location.value } : null,
  p.openNow.value ? { icon: 'clock', label: p.openNow.value.text } : null
].filter(Boolean))

const steps = [
  { icon: 'file-text', title: 'Compará las specs', text: 'Cada ficha lista sus características tal como las cargó la tienda: sin humo.' },
  { icon: 'whatsapp', title: 'Consultá por WhatsApp', text: 'Preguntá compatibilidad, stock y armado — el mensaje sale con el producto.' },
  { icon: 'check', title: 'Cerrás con el local', text: 'Pago, entrega o retiro se arreglan directo, sin intermediarios.' }
]

const mapsUrl = computed(() => {
  const q = p.store.value?.location_address || location.value
  return q ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}` : ''
})
const waStar = (prod) => p.waProduct(prod, prod && p.productOffer(prod) != null ? [`vi la oferta de ${p.formatARS(p.effectivePrice(prod))}.`] : [])
const catalogOffersTo = computed(() => ({ ...p.catalogTo.value, query: { offer: '1' } }))

onMounted(() => { p.loadCatalog() })
</script>

<template>
<div class="sp-page-root gm" :data-var="variant">
  <!-- ===== Hero: tablero esports (arena) / consola (terminal) ===== -->
  <header class="gm-hero">
    <div class="gm-hero-in">
      <!-- Variante terminal: todo dentro de la ventana -->
      <div v-if="variant === 'terminal'" class="gm-term" v-reveal>
        <div class="gm-term-bar" aria-hidden="true">
          <span class="gm-term-dots"><i></i><i></i><i></i></span>
          <span class="gm-term-path">{{ shopName.toLowerCase().replace(/\s+/g, '-') }}@davent:~/</span>
          <span class="gm-term-live">[ en línea ]</span>
        </div>
        <div class="gm-term-body">
          <div class="gm-log" aria-hidden="true">
            <span v-for="(l, i) in bootLines" :key="i"><b>{{ l.slice(0, 7) }}</b>{{ l.slice(7) }}</span>
          </div>
          <p class="gm-kicker">./run tienda --rubro gamer</p>
          <h1 class="gm-title">{{ heroTitle }}</h1>
          <p v-if="custom.description" class="gm-lede"># {{ custom.description }}</p>
          <span v-if="endsLabel" class="gm-chip"><AppIcon name="clock" :size="13" aria-hidden="true" /> {{ endsLabel }}</span>
          <div class="gm-hero-ctas">
            <RouterLink v-if="showCatalog" :to="p.catalogTo.value" class="gm-btn solid"><span class="gm-prompt">></span> ver --catalogo<span class="gm-caret"></span></RouterLink>
            <a v-if="p.waBase.value" class="gm-btn" :href="p.waGeneral.value" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" aria-hidden="true" /> consultar --whatsapp</a>
          </div>
        </div>
      </div>

      <!-- Variante arena: HUD + copy -->
      <div v-else class="gm-hero-copy">
        <div v-if="hudChips.length" class="gm-hud">
          <span v-for="c in hudChips" :key="c.text" class="gm-chip gm-clip"><AppIcon :name="c.icon" :size="13" aria-hidden="true" /> {{ c.text }}</span>
        </div>
        <p class="gm-kicker">{{ heroTitleIsName ? (location || 'tienda online') : shopName }}</p>
        <h1 class="gm-title">{{ heroTitle }}</h1>
        <p v-if="custom.description" class="gm-lede">{{ custom.description }}</p>
        <span v-if="endsLabel" class="gm-chip gm-clip"><AppIcon name="clock" :size="13" aria-hidden="true" /> {{ endsLabel }}</span>
        <div class="gm-hero-ctas">
          <RouterLink v-if="showCatalog" :to="p.catalogTo.value" class="gm-btn solid gm-clip"><AppIcon name="layout-grid" :size="17" aria-hidden="true" /> Ver el catálogo</RouterLink>
          <a v-if="p.waBase.value" class="gm-btn ghost" :href="p.waGeneral.value" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="17" aria-hidden="true" /> Consultar</a>
        </div>
        <div v-if="boardStats.length" class="gm-stats">
          <div v-for="s in boardStats" :key="s.label" class="gm-stat gm-clip"><b>{{ s.value }}</b><span>{{ s.label }}</span></div>
        </div>
      </div>

      <!-- Player card: el producto protagonista -->
      <article v-if="star" v-reveal class="gm-star gm-clip-x">
        <div class="gm-star-media">
          <img v-if="star.image" :src="star.image" :alt="star.name" fetchpriority="high" decoding="async" />
          <span v-else class="gm-star-ph"><AppIcon name="zap" :size="44" aria-hidden="true" /></span>
          <OfferSeal v-if="p.productOffer(star) != null" :pct="maxPct || p.offerPct(star)" shape="corner" class="gm-star-seal" />
        </div>
        <div class="gm-star-info">
          <span class="gm-star-flag">{{ variant === 'arena' ? 'MVP de la tienda' : 'featured_item' }}</span>
          <h2 class="gm-star-name">{{ star.name }}</h2>
          <p class="gm-star-price">
            <s v-if="p.productOffer(star) != null">{{ p.formatARS(star.price) }}</s>
            <strong>{{ p.formatARS(p.effectivePrice(star)) }}</strong>
          </p>
          <span v-if="savings(star) > 0" class="gm-save">-{{ p.offerPct(star) }}% · ahorrás {{ p.formatARS(savings(star)) }}</span>
          <div v-if="specChips(star).length" class="gm-star-specs">
            <span v-for="schip in specChips(star)" :key="schip" class="gm-star-spec">{{ schip }}</span>
          </div>
          <p class="gm-star-meta">
            <span v-if="endsOf(star)"><AppIcon name="clock" :size="13" aria-hidden="true" /> {{ endsOf(star) }}</span>
            <span v-if="p.catOf(star)"><AppIcon name="tag" :size="13" aria-hidden="true" /> {{ p.catOf(star) }}</span>
            <span v-if="p.brandOf(star)"><AppIcon name="tag" :size="13" aria-hidden="true" /> {{ p.brandOf(star) }}</span>
          </p>
          <div class="gm-hero-ctas">
            <a v-if="p.waBase.value" class="gm-btn solid" :href="waStar(star)" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" aria-hidden="true" /> {{ variant === 'arena' ? 'La quiero' : 'pedir --item' }}</a>
            <RouterLink class="gm-btn ghost" :to="p.productTo(star)">{{ variant === 'arena' ? 'Ver specs' : 'cat --specs' }}</RouterLink>
          </div>
        </div>
      </article>
    </div>
  </header>

  <MarqueeBand v-if="bandItems.length" :items="bandItems" />
  <TrustBar :items="trustItems" />

  <main class="gm-main">
    <!-- ===== Drops: ofertas reales ===== -->
    <section v-if="railOffers.length" v-reveal class="gm-sec" aria-labelledby="gm-drops-t">
      <div class="gm-sec-head">
        <h2 id="gm-drops-t" class="gm-sec-title">{{ variant === 'arena' ? 'Drops' : 'ls -l ./ofertas' }}</h2>
        <RouterLink v-if="showCatalog" class="gm-sec-link" :to="catalogOffersTo">{{ variant === 'arena' ? 'Todas las ofertas' : 'cat ofertas --all' }} <AppIcon name="arrow-right" :size="15" /></RouterLink>
      </div>
      <div class="gm-drops">
        <RouterLink v-for="prod in railOffers" :key="prod.id" class="gm-drop" :to="p.productTo(prod)">
          <span class="gm-drop-media">
            <img v-if="prod.image" :src="prod.image" :alt="prod.name" loading="lazy" decoding="async" />
            <span v-else class="gm-drop-ph"><AppIcon name="percent" :size="26" aria-hidden="true" /></span>
            <OfferSeal :pct="p.offerPct(prod)" shape="corner" class="gm-drop-seal" />
          </span>
          <span class="gm-drop-body">
            <span class="gm-drop-name">{{ prod.name }}</span>
            <span class="gm-drop-price">
              <s>{{ p.formatARS(prod.price) }}</s>
              <strong class="deal">{{ p.formatARS(p.effectivePrice(prod)) }}</strong>
            </span>
          </span>
          <span class="gm-drop-pct">-{{ p.offerPct(prod) }}%</span>
        </RouterLink>
      </div>
    </section>

    <!-- ===== El inventario ===== -->
    <section v-if="gridItems.length" class="gm-sec" aria-labelledby="gm-grid-t">
      <div class="gm-sec-head">
        <h2 id="gm-grid-t" class="gm-sec-title">{{ variant === 'arena' ? 'El inventario' : 'ls ./inventario' }}</h2>
        <RouterLink v-if="showCatalog && extraCount" class="gm-sec-link" :to="p.catalogTo.value">{{ variant === 'arena' ? `Ver ${extraCount} más` : `tail -n +${extraCount}` }} <AppIcon name="arrow-right" :size="15" /></RouterLink>
      </div>
      <div class="gm-grid">
        <RouterLink v-for="prod in gridItems" :key="prod.id" v-reveal class="gm-card" :to="p.productTo(prod)">
          <span class="gm-card-media">
            <img v-if="prod.image" :src="prod.image" :alt="prod.name" loading="lazy" decoding="async" />
            <span v-else class="gm-card-ph"><AppIcon name="zap" :size="26" aria-hidden="true" /></span>
            <OfferSeal v-if="p.productOffer(prod) != null" :pct="p.offerPct(prod)" shape="corner" class="gm-card-seal" />
            <span v-else-if="p.isNewProduct(prod)" class="gm-card-new">New</span>
          </span>
          <span class="gm-card-body">
            <span v-if="p.catOf(prod)" class="gm-card-cat">{{ p.catOf(prod) }}</span>
            <span class="gm-card-name">{{ prod.name }}</span>
            <span v-if="specChips(prod, 2).length" class="gm-card-specs">
              <span v-for="schip in specChips(prod, 2)" :key="schip" class="gm-card-spec">{{ schip }}</span>
            </span>
            <span class="gm-card-price">
              <s v-if="p.productOffer(prod) != null">{{ p.formatARS(prod.price) }}</s>
              <strong :class="{ deal: p.productOffer(prod) != null }">{{ p.formatARS(p.effectivePrice(prod)) }}</strong>
            </span>
          </span>
        </RouterLink>
      </div>
    </section>

    <section v-else-if="showCatalog" class="gm-empty">
      <span class="gm-empty-mark"><AppIcon name="zap" :size="26" aria-hidden="true" /></span>
      <h2>{{ variant === 'arena' ? 'Inventario en carga' : 'inventario: sin entradas' }}</h2>
      <p>{{ shopName }} está subiendo sus productos. Escribinos y te contamos qué hay hoy.</p>
      <a v-if="p.waBase.value" class="gm-btn solid" style="margin-top:8px" :href="p.waGeneral.value" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" aria-hidden="true" /> Consultar qué hay</a>
    </section>

    <!-- ===== Secciones ===== -->
    <section v-if="p.departments.value.length > 1" v-reveal class="gm-sec" aria-labelledby="gm-dept-t">
      <div class="gm-sec-head"><h2 id="gm-dept-t" class="gm-sec-title">{{ variant === 'arena' ? 'Categorías' : 'ls ./secciones' }}</h2></div>
      <nav class="gm-depts" aria-label="Secciones del catálogo">
        <RouterLink v-for="d in p.departments.value" :key="d.id" class="gm-dept" :to="p.deptTo(d.id)">
          {{ d.name }} <small>{{ d.count }}</small>
        </RouterLink>
      </nav>
    </section>

    <!-- ===== Marcas ===== -->
    <section v-if="p.brands.value.length" v-reveal class="gm-sec" aria-labelledby="gm-brands-t">
      <div class="gm-sec-head"><h2 id="gm-brands-t" class="gm-sec-title">{{ variant === 'arena' ? 'Marcas' : 'ls ./marcas' }}</h2></div>
      <div class="gm-brands">
        <RouterLink v-for="b in p.brands.value" :key="b.id" class="gm-brand" :to="{ ...p.catalogTo.value, query: { brand: b.id } }">{{ b.name }}</RouterLink>
      </div>
    </section>

    <!-- ===== Cómo comprar + datos ===== -->
    <section v-reveal class="gm-sec" aria-labelledby="gm-how-t">
      <div class="gm-sec-head"><h2 id="gm-how-t" class="gm-sec-title">{{ variant === 'arena' ? 'Cómo comprar' : 'man comprar' }}</h2></div>
      <div class="gm-cols">
        <div class="gm-panel"><StepRail :steps="steps" /></div>
        <div class="gm-panel">
          <ScheduleCard v-if="p.hours.value.length" :hours="p.hours.value" title="Horarios" />
          <template v-else>
            <h3>Zona y entrega</h3>
            <p v-if="p.store.value?.location_address || location" class="gm-zone-addr"><AppIcon name="map-pin" :size="15" aria-hidden="true" /> {{ p.store.value?.location_address || location }}</p>
            <div class="gm-zone-ctas">
              <a v-if="mapsUrl" class="gm-btn ghost" :href="mapsUrl" target="_blank" rel="noopener"><AppIcon name="map-pin" :size="15" aria-hidden="true" /> Mapa</a>
              <a v-if="p.waBase.value" class="gm-btn ghost" :href="p.waGeneral.value" target="_blank" rel="noopener"><AppIcon name="truck" :size="15" aria-hidden="true" /> Envíos</a>
            </div>
          </template>
        </div>
      </div>
    </section>

    <!-- ===== FAQs de compatibilidad (solo si el dueño las cargó) ===== -->
    <section v-if="p.faqs.value.length" v-reveal class="gm-sec" aria-labelledby="gm-faq-t">
      <div class="gm-sec-head"><h2 id="gm-faq-t" class="gm-sec-title">{{ variant === 'arena' ? 'Preguntas frecuentes' : 'man dudas' }}</h2></div>
      <div class="gm-faqs">
        <details v-for="(f, i) in p.faqs.value.slice(0, 6)" :key="i" class="gm-faq">
          <summary>{{ f.q }}</summary>
          <p>{{ f.a }}</p>
        </details>
      </div>
    </section>

    <!-- ===== Opiniones ===== -->
    <section v-if="p.testimonials.value.length" v-reveal class="gm-sec" aria-labelledby="gm-quotes-t">
      <div class="gm-sec-head"><h2 id="gm-quotes-t" class="gm-sec-title">{{ variant === 'arena' ? 'La comunidad' : 'cat ./reviews' }}</h2></div>
      <div class="gm-quotes">
        <figure v-for="(t, i) in p.testimonials.value.slice(0, 3)" :key="i" class="gm-quote">
          <blockquote class="gm-quote-text">{{ t.text }}</blockquote>
          <figcaption class="gm-quote-by"><strong>{{ t.name }}</strong><span v-if="t.detail">{{ t.detail }}</span></figcaption>
        </figure>
      </div>
    </section>

    <!-- ===== CTA final ===== -->
    <section v-reveal class="gm-sec" aria-labelledby="gm-cta-t">
      <div class="gm-cta">
        <h2 id="gm-cta-t">{{ variant === 'arena' ? 'Armá tu setup.' : 'init --pedido' }}</h2>
        <p>Consultanos por WhatsApp: confirmamos stock, specs y compatibilidad en el momento.</p>
        <div class="gm-cta-row">
          <a v-if="p.waBase.value" class="gm-btn solid" :href="p.waGeneral.value" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="17" aria-hidden="true" /> Escribir a {{ shopName }}</a>
          <RouterLink v-if="showCatalog" class="gm-btn ghost" :to="p.catalogTo.value">{{ variant === 'arena' ? 'Seguir explorando' : 'cd ./catalogo' }}</RouterLink>
        </div>
      </div>
    </section>
  </main>
</div>
</template>
