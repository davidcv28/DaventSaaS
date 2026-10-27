<script setup>
import { computed, onMounted } from 'vue'
import { useStorePage } from '../composables/useStorePage.js'
import { servicePriceLabel } from '../api/services.api.js'
import AppIcon from '../components/AppIcon.vue'
import MarqueeBand from '../components/store/MarqueeBand.vue'
import TrustBar from '../components/store/TrustBar.vue'
import OfferSeal from '../components/store/OfferSeal.vue'
import ScheduleCard from '../components/store/ScheduleCard.vue'
import { vReveal } from '../directives/reveal.js'
import '../assets/store-belleza.css'

// Familia BELLEZA — se compra tiempo y confianza. El cliente de
// estética/spa/peluquería decide por: qué servicios hay, cuánto duran,
// cuánto cuestan y cómo reservar. La portada lidera con la carta de
// servicios y el botón "Reservar turno" (WhatsApp real, sin agendado).
// Variantes: 'calma' (spa sereno — aire, Lora itálica, radios amplios) y
// 'signature' (ceremonial — Cinzel sobre espresso, filetes, monograma;
// el layout ya pinta su paleta --sg-*).
const p = useStorePage()
const { custom, shopName, location, pageTemplate, heroTitle, heroTitleIsName, showCatalog, showServices } = p
const variant = computed(() => (pageTemplate.value === 'signature' ? 'signature' : 'calma'))

// ===== Servicios (turno + duración + precio reales) =====
const services = computed(() => p.serviceItems.value || [])
const hasServices = computed(() => services.value.length > 0)
const waReserve = (item) => p.waLink([item ? `quiero reservar un turno para "${item.name}"${item.duration ? ` (${item.duration})` : ''}.` : 'quiero reservar un turno.'])
const waGeneral = p.waGeneral

// ===== Productos (la boutique del local) =====
const offers = computed(() => p.products.value.filter((x) => p.productOffer(x) != null))
const gridItems = computed(() => {
  const ranked = [...offers.value].sort((a, b) => p.offerPct(b) - p.offerPct(a))
  const rest = p.products.value.filter((x) => p.productOffer(x) == null)
  return [...ranked, ...rest].slice(0, 8)
})
const extraCount = computed(() => Math.max(0, p.products.value.length - gridItems.value.length))

// ===== Datos de confianza (solo reales) =====
const stats = computed(() => [
  services.value.length ? { value: `${services.value.length}`, label: services.value.length === 1 ? 'servicio' : 'servicios' } : null,
  custom.value.about_years ? { value: `${custom.value.about_years}`, label: custom.value.about_years === 1 ? 'año de trayectoria' : 'años de trayectoria' } : null,
  p.openNow.value ? { value: '·', label: p.openNow.value.text } : null
].filter(Boolean).slice(0, 3))
const bandItems = computed(() => [
  { icon: 'sparkles', text: shopName.value },
  services.value.length ? { icon: 'clock', text: `${services.value.length} ${services.value.length === 1 ? 'servicio' : 'servicios'} disponibles` } : null,
  offers.value.length ? { icon: 'percent', text: `${offers.value.length} ${offers.value.length === 1 ? 'oferta' : 'ofertas'}` } : null,
  location.value ? { icon: 'map-pin', text: location.value } : null
].filter(Boolean))
const trustItems = computed(() => [
  services.value.length ? { icon: 'sparkles', value: `${services.value.length}`, label: services.value.length === 1 ? 'servicio' : 'servicios' } : null,
  offers.value.length ? { icon: 'percent', value: `${offers.value.length}`, label: 'en oferta' } : null,
  location.value ? { icon: 'map-pin', label: location.value } : null,
  p.openNow.value ? { icon: 'clock', label: p.openNow.value.text } : null
].filter(Boolean))

const mapsUrl = computed(() => {
  const q = p.store.value?.location_address || location.value
  return q ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}` : ''
})

onMounted(() => { p.loadCatalog() })
</script>

<template>
<div class="sp-page-root be" :data-var="variant">
  <!-- ===== Hero: sereno (calma) / ceremonial (signature) ===== -->
  <header class="be-hero">
    <div class="be-hero-in">
      <span v-if="heroTitleIsName" class="be-mono-mark" aria-hidden="true">{{ p.initial }}</span>
      <p class="be-kicker">{{ heroTitleIsName ? (location || 'tienda online') : shopName }}</p>
      <h1 class="be-title">{{ heroTitle }}</h1>
      <p v-if="custom.description" class="be-lede">{{ custom.description }}</p>
      <div class="be-hero-ctas">
        <a v-if="p.waBase.value" class="be-btn solid" :href="waReserve()" target="_blank" rel="noopener"><AppIcon name="calendar" :size="17" aria-hidden="true" /> Reservar turno</a>
        <RouterLink v-if="showServices && hasServices" :to="p.servicesTo.value" class="be-btn"><AppIcon name="sparkles" :size="16" aria-hidden="true" /> Ver servicios</RouterLink>
        <RouterLink v-else-if="showCatalog" :to="p.catalogTo.value" class="be-btn"><AppIcon name="search" :size="16" aria-hidden="true" /> Ver productos</RouterLink>
      </div>
      <div v-if="stats.length" class="be-stats">
        <div v-for="s in stats" :key="s.label" class="be-stat"><b>{{ s.value }}</b><span>{{ s.label }}</span></div>
      </div>
    </div>
  </header>

  <MarqueeBand v-if="bandItems.length" :items="bandItems" />
  <TrustBar :items="trustItems" />

  <main class="be-main">
    <!-- ===== La carta de servicios: turno, duración, precio ===== -->
    <section v-if="hasServices" v-reveal class="be-sec" aria-labelledby="be-svc-t">
      <div class="be-sec-head">
        <h2 id="be-svc-t" class="be-sec-title">{{ variant === 'calma' ? 'Nuestros servicios' : 'La carta' }}</h2>
        <RouterLink v-if="showServices" class="be-sec-link" :to="p.servicesTo.value">Todos los servicios <AppIcon name="arrow-right" :size="15" /></RouterLink>
      </div>
      <div class="be-services">
        <div v-for="it in services.slice(0, 6)" :key="it.id" class="be-service">
          <span class="be-service-name">{{ it.name }}</span>
          <span v-if="it.description" class="be-service-desc">{{ it.description }}</span>
          <span class="be-service-meta">
            <span v-if="it.duration"><AppIcon name="clock" :size="13" aria-hidden="true" /> {{ it.duration }}</span>
          </span>
          <span class="be-service-price">
            <b>{{ it.price != null ? servicePriceLabel(it) : 'A convenir' }}</b>
            <a v-if="p.waBase.value" class="be-reserve" :href="waReserve(it)" target="_blank" rel="noopener">Reservar</a>
          </span>
        </div>
      </div>
    </section>

    <!-- ===== Resultados / antes-después (galería real) ===== -->
    <section v-if="p.gallery.value.length" v-reveal class="be-sec" aria-labelledby="be-gal-t">
      <div class="be-sec-head"><h2 id="be-gal-t" class="be-sec-title">{{ variant === 'calma' ? 'Nuestros resultados' : 'El portafolio' }}</h2></div>
      <div class="be-gallery">
        <div v-for="(g, i) in p.gallery.value.slice(0, 8)" :key="i" class="be-gal-item">
          <img :src="g.url" :alt="g.caption || `Resultado ${i + 1} de ${shopName}`" loading="lazy" decoding="async" />
        </div>
      </div>
    </section>

    <!-- ===== Productos ===== -->
    <section v-if="gridItems.length" v-reveal class="be-sec" aria-labelledby="be-grid-t">
      <div class="be-sec-head">
        <h2 id="be-grid-t" class="be-sec-title">{{ variant === 'calma' ? 'Para llevarte a casa' : 'La boutique' }}</h2>
        <RouterLink v-if="showCatalog && extraCount" class="be-sec-link" :to="p.catalogTo.value">Ver {{ extraCount }} más <AppIcon name="arrow-right" :size="15" /></RouterLink>
      </div>
      <div class="be-grid">
        <RouterLink v-for="prod in gridItems" :key="prod.id" class="be-card" :to="p.productTo(prod)">
          <span class="be-card-media">
            <img v-if="prod.image" :src="prod.image" :alt="prod.name" loading="lazy" decoding="async" />
            <span v-else class="be-card-ph"><AppIcon name="sparkles" :size="26" aria-hidden="true" /></span>
            <OfferSeal v-if="p.productOffer(prod) != null" :pct="p.offerPct(prod)" shape="corner" class="be-card-seal" />
          </span>
          <span class="be-card-body">
            <span class="be-card-name">{{ prod.name }}</span>
            <span class="be-card-price">
              <s v-if="p.productOffer(prod) != null">{{ p.formatARS(prod.price) }}</s>
              <strong :class="{ deal: p.productOffer(prod) != null }">{{ p.formatARS(p.effectivePrice(prod)) }}</strong>
            </span>
          </span>
        </RouterLink>
      </div>
    </section>

    <!-- ===== Horarios + zona ===== -->
    <section v-reveal class="be-sec" aria-labelledby="be-datos-t">
      <div class="be-sec-head"><h2 id="be-datos-t" class="be-sec-title">{{ variant === 'calma' ? 'Horarios y ubicación' : 'El atelier' }}</h2></div>
      <div class="be-cols">
        <div class="be-panel">
          <ScheduleCard v-if="p.hours.value.length" :hours="p.hours.value" title="Horarios" />
          <template v-else>
            <h3>Turnos</h3>
            <p class="be-lede" style="font-size:14px">Escribinos por WhatsApp y coordinamos tu turno en el momento.</p>
          </template>
        </div>
        <div class="be-panel">
          <h3>Ubicación</h3>
          <p v-if="p.store.value?.location_address || location" class="be-zone-addr"><AppIcon name="map-pin" :size="15" aria-hidden="true" /> {{ p.store.value?.location_address || location }}</p>
          <div class="be-zone-ctas">
            <a v-if="mapsUrl" class="be-btn ghost" :href="mapsUrl" target="_blank" rel="noopener"><AppIcon name="map-pin" :size="15" aria-hidden="true" /> Cómo llegar</a>
            <a v-if="p.waBase.value" class="be-btn ghost" :href="waGeneral.value" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="15" aria-hidden="true" /> Consultar</a>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== Opiniones ===== -->
    <section v-if="p.testimonials.value.length" v-reveal class="be-sec" aria-labelledby="be-quotes-t">
      <div class="be-sec-head"><h2 id="be-quotes-t" class="be-sec-title">{{ variant === 'calma' ? 'Lo que dicen' : 'Referencias' }}</h2></div>
      <div class="be-quotes">
        <figure v-for="(t, i) in p.testimonials.value.slice(0, 3)" :key="i" class="be-quote">
          <blockquote class="be-quote-text">{{ t.text }}</blockquote>
          <figcaption class="be-quote-by"><strong>{{ t.name }}</strong><span v-if="t.detail">{{ t.detail }}</span></figcaption>
        </figure>
      </div>
    </section>

    <!-- ===== CTA final ===== -->
    <section v-reveal class="be-sec" aria-labelledby="be-cta-t">
      <div class="be-cta">
        <h2 id="be-cta-t">{{ variant === 'calma' ? 'Reservá tu turno.' : 'Su turno le espera.' }}</h2>
        <p>Escribinos por WhatsApp, elegí tu servicio y coordinamos el horario que mejor te quede.</p>
        <div class="be-cta-row">
          <a v-if="p.waBase.value" class="be-btn solid" :href="waReserve()" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="17" aria-hidden="true" /> Reservar en {{ shopName }}</a>
          <RouterLink v-if="showCatalog" class="be-btn" :to="p.catalogTo.value">Ver productos</RouterLink>
        </div>
      </div>
    </section>
  </main>
</div>
</template>
