<script setup>
import { ref, computed, onMounted } from 'vue'
import { useStorePage } from '../composables/useStorePage.js'
import AppIcon from '../components/AppIcon.vue'
import StTag from '../components/store/StTag.vue'
import OfferSeal from '../components/store/OfferSeal.vue'
import StepRail from '../components/store/StepRail.vue'
import ScheduleCard from '../components/store/ScheduleCard.vue'
import { vReveal } from '../directives/reveal.js'
import '../assets/store-mercado.css'

// Familia COMESTIBLES — "Mercado". Mesa servida: apetito primero, pedido
// a un toque. Hero en arco sobre crema con grano + sello giratorio, rail
// de categorías en círculos, cards con "+" de pedido directo por WhatsApp
// y horarios con "Abierto ahora". Variantes: 'mercado' (cards cálidas) y
// 'carta' (menú de restaurante: lista con puntos y precios alineados).
const p = useStorePage()
const { custom, shopName, location, pageTemplate, hasAbout, showContact, showCatalog, heroTitle } = p
const variant = computed(() => (pageTemplate.value === 'carta' ? 'carta' : 'mercado'))

// Sello giratorio: texto real de la tienda en círculo (SVG textPath).
const sealText = computed(() => `${shopName.value} · Hecho a pedido · `)

// Barra de pedido rápido.
const mapsUrl = computed(() => {
  const q = p.store.value?.location_address || location.value
  return q ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}` : ''
})

// Categorías como círculos de 72px (foto de su primer producto o inicial).
const circles = computed(() => p.departments.value.slice(0, 10))
const activeCat = ref(null)
const gridItems = computed(() => {
  const list = activeCat.value == null ? p.products.value : p.products.value.filter((x) => x.category === activeCat.value)
  return list.slice(0, 12)
})

// "Hoy en la carta": productos con oferta real.
const todayOffers = computed(() => p.products.value.filter((x) => p.productOffer(x) != null).slice(0, 6))

// Pedido directo por WhatsApp desde el "+" de la card.
const waOrder = (prod) => p.waProduct(prod, ['me gustaría pedirlo.'])

// Tags de dieta desde features reales (porción, peso, vegano, sin TACC...).
const dietaTone = (v) => (/vegano|vegetariano/.test(v) ? 'veg' : /tacc|gluten/.test(v) ? 'tacc' : /az[uú]car|keto|light/.test(v) ? 'sin-azucar' : '')
const dietaIcon = (v) => (/vegano|vegetariano/.test(v) ? 'leaf' : 'check')
const dietTagsOf = (prod) => p.featureRows(prod)
  .filter(([k]) => /dieta|porci|peso|vegano|tacc|gluten|alergen|ingrediente/i.test(k))
  .flatMap(([, v]) => String(v).split(/[,\/·]/).map((s) => s.trim().toLowerCase()).filter(Boolean))
  .slice(0, 3)
  .map((v) => ({ label: v, icon: dietaIcon(v), tone: dietaTone(v) }))

// "Cómo pedir" — 3 pasos fijos del flujo (no son datos de la tienda).
const steps = [
  { icon: 'search', title: 'Elegí', text: 'Mirá la carta y tocá el "+" de lo que te tiente.' },
  { icon: 'whatsapp', title: 'Pedí', text: 'Tu pedido llega armado al WhatsApp del local.' },
  { icon: 'check', title: 'Retirá o recibí', text: 'Coordinás entrega y pago directo con ellos.' }
]

// Carta: productos agrupados por categoría (menú de restaurante).
const menuGroups = computed(() => {
  if (variant.value !== 'carta') return []
  const groups = p.departments.value.map((d) => ({
    ...d,
    items: gridItems.value.filter((x) => x.category === d.id)
  })).filter((g) => g.items.length)
  const loose = gridItems.value.filter((x) => !x.category || !groups.some((g) => g.id === x.category))
  if (loose.length) groups.push({ id: -1, name: 'De la casa', items: loose })
  return groups.length ? groups : [{ id: -1, name: 'La carta', items: gridItems.value }]
})

onMounted(() => { p.loadCatalog() })
</script>

<template>
<div class="sp-page-root mc" :data-var="variant">
  <!-- ===== Hero orgánico: arco + sello giratorio sobre crema/grano ===== -->
  <header class="mc-hero">
    <div class="mc-hero-in">
      <figure v-if="p.heroImage.value" class="mc-hero-photo">
        <img :src="p.heroImage.value" :alt="`Plato de ${shopName}`" fetchpriority="high" decoding="async" />
        <svg class="mc-seal" viewBox="0 0 100 100" aria-hidden="true">
          <defs><path id="mc-seal-circle" d="M50,50 m-36,0 a36,36 0 1,1 72,0 a36,36 0 1,1 -72,0" /></defs>
          <circle cx="50" cy="50" r="48" />
          <text><textPath href="#mc-seal-circle">{{ sealText }}</textPath></text>
          <circle cx="50" cy="50" r="26" class="mc-seal-core" />
        </svg>
      </figure>
      <div class="mc-hero-copy">
        <p v-if="p.openNow.value" class="mc-open" :data-state="p.openNow.value.state"><AppIcon name="dot" :size="10" /> {{ p.openNow.value.text }}</p>
        <h1 class="mc-title">{{ heroTitle }}</h1>
        <p v-if="custom.description" class="mc-lede">{{ custom.description }}</p>
        <p v-if="location" class="mc-where"><AppIcon name="map-pin" :size="14" /> {{ location }}</p>
      </div>
    </div>
    <!-- Barra de pedido rápido -->
    <nav class="mc-quickbar" aria-label="Pedido rápido">
      <a v-if="showCatalog" class="mc-quick" href="#mc-carta"><AppIcon name="file-text" :size="18" /> Ver carta</a>
      <a v-if="p.waBase.value" class="mc-quick solid" :href="p.waGeneral.value" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="18" /> Pedir por WhatsApp</a>
      <a v-if="mapsUrl" class="mc-quick" :href="mapsUrl" target="_blank" rel="noopener"><AppIcon name="map-pin" :size="18" /> Cómo llegar</a>
    </nav>
  </header>

  <!-- ===== Rail de categorías en círculos ===== -->
  <nav v-if="circles.length" class="mc-cats" aria-label="Categorías">
    <button type="button" class="mc-cat" :class="{ on: activeCat === null }" @click="activeCat = null">
      <span class="mc-cat-img"><AppIcon name="store" :size="24" /></span><span class="mc-cat-name">Todo</span>
    </button>
    <button
      v-for="d in circles" :key="d.id" type="button" class="mc-cat" :class="{ on: activeCat === d.id }"
      :aria-pressed="activeCat === d.id" @click="activeCat = activeCat === d.id ? null : d.id"
    >
      <span class="mc-cat-img"><img v-if="d.image" :src="d.image" alt="" loading="lazy" /><AppIcon v-else name="tag" :size="22" /></span>
      <span class="mc-cat-name">{{ d.name }}</span>
    </button>
  </nav>

  <main class="mc-main" id="mc-carta">
    <!-- ===== Variante mercado: cards cálidas con "+" de pedido ===== -->
    <section v-if="variant === 'mercado' && gridItems.length" class="mc-grid" aria-label="Productos">
      <article v-for="prod in gridItems" :key="prod.id" class="mc-card">
        <RouterLink class="mc-card-media" :to="p.productTo(prod)" :aria-label="prod.name">
          <img v-if="prod.image" :src="prod.image" :alt="prod.name" loading="lazy" decoding="async" />
          <span v-else class="mc-card-ph"><AppIcon name="coffee" :size="28" /></span>
          <span class="mc-card-price">{{ p.formatARS(p.effectivePrice(prod)) }}</span>
          <OfferSeal v-if="p.productOffer(prod) != null" :pct="p.offerPct(prod)" shape="circle" />
        </RouterLink>
        <div class="mc-card-info">
          <RouterLink class="mc-card-name" :to="p.productTo(prod)">{{ prod.name }}</RouterLink>
          <div v-if="dietTagsOf(prod).length" class="mc-card-tags"><StTag v-for="t in dietTagsOf(prod)" :key="t.label" kind="dieta" :label="t.label" :icon="t.icon" :tone="t.tone" /></div>
          <a v-if="p.waBase.value" class="mc-card-add" :href="waOrder(prod)" target="_blank" rel="noopener" :aria-label="`Pedir ${prod.name} por WhatsApp`"><AppIcon name="plus" :size="20" /></a>
        </div>
      </article>
    </section>

    <!-- ===== Variante carta: menú de restaurante ===== -->
    <section v-else-if="variant === 'carta' && gridItems.length" class="mc-menu" aria-label="La carta">
      <div v-for="g in menuGroups" :key="g.id" class="mc-menu-group">
        <h2 class="mc-menu-title"><span>{{ g.name }}</span></h2>
        <ul class="mc-menu-list">
          <li v-for="prod in g.items" :key="prod.id">
            <RouterLink class="mc-menu-row" :to="p.productTo(prod)">
              <span class="mc-menu-name">{{ prod.name }}<OfferSeal v-if="p.productOffer(prod) != null" :pct="p.offerPct(prod)" shape="circle" small class="mc-menu-seal" /></span>
              <span class="mc-menu-dots" aria-hidden="true"></span>
              <span class="mc-menu-price"><s v-if="p.productOffer(prod) != null">{{ p.formatARS(prod.price) }}</s>{{ p.formatARS(p.effectivePrice(prod)) }}</span>
            </RouterLink>
            <p v-if="prod.description" class="mc-menu-desc">{{ prod.description.slice(0, 110) }}{{ prod.description.length > 110 ? '…' : '' }}</p>
            <a v-if="p.waBase.value" class="mc-menu-add" :href="waOrder(prod)" target="_blank" rel="noopener" :aria-label="`Pedir ${prod.name}`"><AppIcon name="plus" :size="16" /></a>
          </li>
        </ul>
      </div>
    </section>

    <section v-else-if="showCatalog" class="mc-empty">
      <span class="mc-empty-mark"><AppIcon name="coffee" :size="26" /></span>
      <h2>La cocina está preparando la carta</h2>
      <p>{{ shopName }} está subiendo sus productos. Escribinos y te contamos qué hay hoy.</p>
      <a v-if="p.waBase.value" class="mc-quick solid" :href="p.waGeneral.value" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" /> Consultar qué hay hoy</a>
    </section>

    <!-- ===== Hoy en la carta (ofertas) ===== -->
    <section v-if="todayOffers.length && variant === 'mercado'" v-reveal class="mc-today" aria-labelledby="mc-today-t">
      <h2 id="mc-today-t"><span>Hoy en la carta</span></h2>
      <div class="mc-today-track">
        <article v-for="prod in todayOffers" :key="prod.id" class="mc-today-card">
          <RouterLink class="mc-today-media" :to="p.productTo(prod)">
            <img v-if="prod.image" :src="prod.image" :alt="prod.name" loading="lazy" />
            <span v-else class="mc-card-ph"><AppIcon name="percent" :size="24" /></span>
            <OfferSeal :pct="p.offerPct(prod)" shape="circle" />
          </RouterLink>
          <div class="mc-today-info">
            <strong>{{ prod.name }}</strong>
            <span class="mc-today-price"><s>{{ p.formatARS(prod.price) }}</s>{{ p.formatARS(p.effectivePrice(prod)) }}</span>
          </div>
        </article>
      </div>
    </section>

    <!-- ===== Cómo pedir + horarios ===== -->
    <section v-reveal class="mc-how" aria-labelledby="mc-how-t">
      <h2 id="mc-how-t"><span>Cómo pedir</span></h2>
      <StepRail :steps="steps" />
    </section>

    <div class="mc-bottom">
      <ScheduleCard v-if="p.hours.value.length" :hours="p.hours.value" title="Horarios" />
      <section v-if="location || mapsUrl" v-reveal class="mc-zone" aria-labelledby="mc-zone-t">
        <h2 id="mc-zone-t"><span>Zona y entrega</span></h2>
        <p v-if="p.store.value?.location_address" class="mc-zone-addr"><AppIcon name="map-pin" :size="15" /> {{ p.store.value.location_address }}</p>
        <p v-else-if="location" class="mc-zone-addr"><AppIcon name="map-pin" :size="15" /> {{ location }}</p>
        <div class="mc-zone-ctas">
          <a v-if="mapsUrl" class="mc-quick" :href="mapsUrl" target="_blank" rel="noopener"><AppIcon name="map-pin" :size="16" /> Ver en el mapa</a>
          <a v-if="p.waBase.value" class="mc-quick" :href="p.waGeneral.value" target="_blank" rel="noopener"><AppIcon name="truck" :size="16" /> Consultar envío</a>
        </div>
      </section>
    </div>
  </main>
</div>
</template>
