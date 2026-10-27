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
import '../assets/store-ofertas.css'
import TplProductCard from '../components/store/TplProductCard.vue'

// Familia OFERTAS — "el precio es el diseño". El cliente llega por el
// número: en 5 segundos tiene que ver cuánto cuesta, cuánto se ahorra,
// hasta cuándo dura y cómo pedirlo (siempre datos reales — la urgencia
// solo existe si el backend manda ends_at).
// Variantes: 'promo' (afiche de campaña — un deal domina, relieve duro,
// sellos rotados) y 'shop' (góndola — masthead con datos, grilla densa,
// precio dominante).
const p = useStorePage()
const { custom, shopName, location, pageTemplate, heroTitle, showCatalog } = p
const variant = computed(() => (pageTemplate.value === 'shop' ? 'shop' : 'promo'))

// ===== Datos de oferta (solo reales) =====
const offers = computed(() => p.products.value.filter((x) => p.productOffer(x) != null))
const rankedOffers = computed(() => [...offers.value].sort((a, b) => p.offerPct(b) - p.offerPct(a)))
const topDeal = computed(() => rankedOffers.value[0] || null)
const maxPct = computed(() => (topDeal.value ? p.offerPct(topDeal.value) : 0))
const savings = (prod) => Math.max(0, Number(prod.price) - p.effectivePrice(prod))

// Promos programadas del backend (nombre/alcance/vencimiento reales).
const promos = computed(() => p.catalog.value?.promotions || [])
const promoName = computed(() => promos.value[0]?.name || '')
const endsLabel = computed(() => {
  const d = topDeal.value ? productDiscount(topDeal.value) : null
  return offerEndsLabel(d) || offerEndsLabel(promos.value[0]) || ''
})
const endsOf = (prod) => offerEndsLabel(productDiscount(prod))

const railOffers = computed(() => rankedOffers.value.slice(0, 8))

// Banda marquee + barra de confianza (todo dato real, sin relleno).
const bandItems = computed(() => [
  { icon: 'tag', text: promoName.value || 'Ofertas' },
  offers.value.length ? { icon: 'percent', text: `${offers.value.length} ${offers.value.length === 1 ? 'oferta activa' : 'ofertas activas'}` } : null,
  endsLabel.value ? { icon: 'clock', text: endsLabel.value } : null,
  location.value ? { icon: 'map-pin', text: location.value } : null,
  { text: shopName.value }
].filter(Boolean))
const trustItems = computed(() => [
  offers.value.length ? { icon: 'percent', value: `${offers.value.length}`, label: offers.value.length === 1 ? 'oferta activa' : 'ofertas activas' } : null,
  maxPct.value ? { icon: 'tag', value: `-${maxPct.value}%`, label: 'descuento máximo' } : null,
  location.value ? { icon: 'map-pin', label: location.value } : null,
  p.openNow.value ? { icon: 'clock', label: p.openNow.value.text } : null
].filter(Boolean))

// Stats del masthead (shop).
const shopStats = computed(() => [
  p.products.value.length ? { value: `${p.products.value.length}`, label: p.products.value.length === 1 ? 'producto' : 'productos' } : null,
  offers.value.length ? { value: `${offers.value.length}`, label: 'en oferta' } : null,
  maxPct.value ? { value: `-${maxPct.value}%`, label: 'mejor descuento' } : null,
  p.departments.value.length ? { value: `${p.departments.value.length}`, label: p.departments.value.length === 1 ? 'sección' : 'secciones' } : null
].filter(Boolean).slice(0, 4))

const steps = [
  { icon: 'search', title: 'Encontrá la oferta', text: 'El precio tachado ya tiene el descuento aplicado: lo que ves es lo que pagás.' },
  { icon: 'whatsapp', title: 'Pedila por WhatsApp', text: 'El mensaje sale armado con el producto y el precio de oferta.' },
  { icon: 'check', title: 'Coordinás con el local', text: 'Entrega, retiro y pago se arreglan directo, sin intermediarios.' }
]

const mapsUrl = computed(() => {
  const q = p.store.value?.location_address || location.value
  return q ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}` : ''
})
const waDeal = (prod) => p.waProduct(prod, [`vi la oferta de ${p.formatARS(p.effectivePrice(prod))}.`])
const catalogOffersTo = computed(() => ({ ...p.catalogTo.value, query: { offer: '1' } }))

onMounted(() => { p.loadCatalog() })
</script>

<template>
<div class="sp-page-root of" :data-var="variant">
  <!-- ===== Hero: afiche de campaña (promo) / masthead de góndola (shop) ===== -->
  <header class="of-hero">
    <div class="of-hero-in">
      <div class="of-hero-copy">
        <p class="of-kicker"><AppIcon name="tag" :size="13" aria-hidden="true" /> {{ promoName || 'Ofertas' }}</p>
        <h1 class="of-title">{{ heroTitle }}</h1>
        <p v-if="custom.description" class="of-lede">{{ custom.description }}</p>
        <span v-if="endsLabel" class="of-ends"><AppIcon name="clock" :size="13" aria-hidden="true" /> {{ endsLabel }}</span>
        <div class="of-hero-ctas">
          <RouterLink v-if="showCatalog && offers.length" :to="catalogOffersTo" class="of-btn accent"><AppIcon name="percent" :size="17" aria-hidden="true" /> Ver las ofertas</RouterLink>
          <RouterLink v-else-if="showCatalog" :to="p.catalogTo.value" class="of-btn accent"><AppIcon name="search" :size="17" aria-hidden="true" /> Ver el catálogo</RouterLink>
          <a v-if="p.waBase.value" class="of-btn" :href="p.waGeneral.value" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="17" aria-hidden="true" /> Consultar</a>
        </div>
        <div v-if="variant === 'shop' && shopStats.length" class="of-stats">
          <div v-for="s in shopStats" :key="s.label" class="of-stat"><b>{{ s.value }}</b><span>{{ s.label }}</span></div>
        </div>
      </div>

      <!-- El deal protagonista: mayor % real del catálogo -->
      <article v-if="topDeal" v-reveal class="of-deal">
        <div class="of-deal-media">
          <img v-if="topDeal.image" :src="topDeal.image" :alt="topDeal.name" fetchpriority="high" decoding="async" />
          <span v-else class="of-deal-ph"><AppIcon name="tag" :size="44" aria-hidden="true" /></span>
          <OfferSeal :pct="maxPct" :shape="variant === 'promo' ? 'ticket' : 'circle'" class="of-deal-seal" />
        </div>
        <div class="of-deal-info">
          <span class="of-deal-flag">{{ variant === 'promo' ? 'La oferta' : 'Destacado' }}</span>
          <h2 class="of-deal-name">{{ topDeal.name }}</h2>
          <p class="of-deal-price">
            <s>{{ p.formatARS(topDeal.price) }}</s>
            <strong>{{ p.formatARS(p.effectivePrice(topDeal)) }}</strong>
          </p>
          <span class="of-save"><AppIcon name="percent" :size="13" aria-hidden="true" /> Ahorrás {{ p.formatARS(savings(topDeal)) }}</span>
          <p class="of-deal-meta">
            <span v-if="endsOf(topDeal)"><AppIcon name="clock" :size="14" aria-hidden="true" /> {{ endsOf(topDeal) }}</span>
            <span v-if="p.catOf(topDeal)"><AppIcon name="tag" :size="14" aria-hidden="true" /> {{ p.catOf(topDeal) }}</span>
          </p>
          <div class="of-hero-ctas">
            <a v-if="p.waBase.value" class="of-btn solid" :href="waDeal(topDeal)" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" aria-hidden="true" /> Pedirla ahora</a>
            <RouterLink class="of-btn" :to="p.productTo(topDeal)">Ver detalle</RouterLink>
          </div>
        </div>
      </article>
    </div>
  </header>

  <MarqueeBand v-if="bandItems.length" :items="bandItems" />
  <TrustBar :items="trustItems" />

  <main class="of-main">
    <!-- ===== Las ofertas: rail de tickets / grilla densa según variante ===== -->
    <section v-if="railOffers.length" v-reveal class="of-sec" aria-labelledby="of-deals-t">
      <div class="of-sec-head">
        <h2 id="of-deals-t" class="of-sec-title">Las <em>ofertas</em></h2>
        <RouterLink v-if="showCatalog" class="of-sec-link" :to="catalogOffersTo">Todas <AppIcon name="arrow-right" :size="15" /></RouterLink>
      </div>
      <div class="of-tickets">
        <TplProductCard v-for="prod in railOffers" :key="prod.id" class="of-ticket" :p="prod"
          seal-shape="ticket" ph-icon="percent" :ph-size="26" :go="false"
          :save="savings(prod) > 0 ? `Ahorrás ${p.formatARS(savings(prod))}` : ''"
          @open="p.openProduct" />
      </div>
    </section>



    <section v-else-if="showCatalog" class="of-empty">
      <span class="of-empty-mark"><AppIcon name="tag" :size="26" aria-hidden="true" /></span>
      <h2>El local está cargando precios</h2>
      <p>{{ shopName }} está subiendo sus productos. Escribinos y te contamos qué hay hoy.</p>
      <a v-if="p.waBase.value" class="of-btn solid" style="margin-top:8px" :href="p.waGeneral.value" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" aria-hidden="true" /> Consultar qué hay</a>
    </section>

    <!-- ===== Secciones del local ===== -->
    <section v-if="p.departments.value.length > 1" v-reveal class="of-sec" aria-labelledby="of-dept-t">
      <div class="of-sec-head"><h2 id="of-dept-t" class="of-sec-title">Secciones</h2></div>
      <nav class="of-depts" aria-label="Secciones del catálogo">
        <RouterLink v-for="d in p.departments.value" :key="d.id" class="of-dept" :to="p.deptTo(d.id)">
          {{ d.name }} <small>{{ d.count }}</small>
        </RouterLink>
      </nav>
    </section>

    <!-- ===== Cómo comprar + zona/horarios ===== -->
    <section v-reveal class="of-sec" aria-labelledby="of-how-t">
      <div class="of-sec-head"><h2 id="of-how-t" class="of-sec-title">Cómo comprar</h2></div>
      <div class="of-cols">
        <div class="of-panel"><StepRail :steps="steps" /></div>
        <div class="of-panel">
          <ScheduleCard v-if="p.hours.value.length" :hours="p.hours.value" title="Horarios" />
          <template v-else>
            <h3>Zona y entrega</h3>
            <p v-if="p.store.value?.location_address || location" class="of-zone-addr"><AppIcon name="map-pin" :size="15" aria-hidden="true" /> {{ p.store.value?.location_address || location }}</p>
            <div class="of-zone-ctas">
              <a v-if="mapsUrl" class="of-btn" :href="mapsUrl" target="_blank" rel="noopener"><AppIcon name="map-pin" :size="15" aria-hidden="true" /> Mapa</a>
              <a v-if="p.waBase.value" class="of-btn" :href="p.waGeneral.value" target="_blank" rel="noopener"><AppIcon name="truck" :size="15" aria-hidden="true" /> Envíos</a>
            </div>
          </template>
        </div>
      </div>
    </section>

    <!-- ===== Opiniones (solo si el dueño cargó testimonios) ===== -->
    <section v-if="p.testimonials.value.length" v-reveal class="of-sec" aria-labelledby="of-quotes-t">
      <div class="of-sec-head"><h2 id="of-quotes-t" class="of-sec-title">Lo que dicen</h2></div>
      <div class="of-quotes">
        <figure v-for="(t, i) in p.testimonials.value.slice(0, 3)" :key="i" class="of-quote">
          <blockquote class="of-quote-text">{{ t.text }}</blockquote>
          <figcaption class="of-quote-by"><strong>{{ t.name }}</strong><span v-if="t.detail">{{ t.detail }}</span></figcaption>
        </figure>
      </div>
    </section>

    <!-- ===== CTA final ===== -->
    <section v-reveal class="of-sec" aria-labelledby="of-cta-t">
      <div class="of-cta">
        <h2 id="of-cta-t">El precio ya está.<br />Pedilo por WhatsApp.</h2>
        <p>Escribinos, confirmamos stock y coordinamos entrega o retiro en el momento.</p>
        <div class="of-cta-row">
          <a v-if="p.waBase.value" class="of-btn accent" :href="p.waGeneral.value" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="17" aria-hidden="true" /> Escribir a {{ shopName }}</a>
          <RouterLink v-if="showCatalog" class="of-btn" :to="p.catalogTo.value">Seguir mirando</RouterLink>
        </div>
      </div>
    </section>
  </main>
</div>
</template>
