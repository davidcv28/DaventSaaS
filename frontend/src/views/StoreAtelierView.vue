<script setup>
import { ref, computed, onMounted } from 'vue'
import { useStorePage } from '../composables/useStorePage.js'
import AppIcon from '../components/AppIcon.vue'
import MarqueeBand from '../components/store/MarqueeBand.vue'
import StTag from '../components/store/StTag.vue'
import OfferSeal from '../components/store/OfferSeal.vue'
import { vReveal } from '../directives/reveal.js'
import '../assets/store-atelier.css'

// Familia INDUMENTARIA — "Lookbook". La ropa es protagonista y la UI casi
// desaparece: titular XXL que atraviesa la foto, pestañas tipográficas,
// grilla editorial con ritmo y hotspots del look. Dos variantes sobre el
// mismo esqueleto: 'atelier' (editorial limpio, radio 2px) y 'street'
// (crudo: Archivo Black, borde negro, relieve duro, radio 0).
const p = useStorePage()
const { custom, shopName, location, pageTemplate, hasAbout, showContact, showCatalog, heroTitle } = p
const variant = computed(() => (pageTemplate.value === 'street' ? 'street' : 'atelier'))

// Titular en 3 líneas superpuestas: reparte las palabras del headline; la
// primera va en outline, la segunda sólida y la tercera la corta la imagen.
// Con headline corto las líneas restantes caen al nombre de la tienda.
const titleLines = computed(() => {
  const words = heroTitle.value.split(/\s+/).filter(Boolean)
  const lines = [[], [], []]
  if (words.length <= 3) {
    words.forEach((w, i) => lines[i].push(w))
    const tail = shopName.value.split(/\s+/).filter(Boolean)
    for (let i = words.length; i < 3; i++) lines[i].push(tail[i - words.length] || '')
  } else {
    const per = Math.ceil(words.length / 3)
    lines[0] = words.slice(0, per)
    lines[1] = words.slice(per, per * 2)
    lines[2] = words.slice(per * 2)
  }
  return lines.map((l) => l.join(' ')).map((t, i) => (t || (i === 0 ? shopName.value : '')))
})

// Marquee: datos reales (nombre, colección, ubicación, ofertas).
const bandItems = computed(() => {
  const items = [{ icon: 'zap', text: shopName.value }, { icon: 'tag', text: heroTitle.value }]
  if (p.offerCount.value) items.push({ icon: 'percent', text: `${p.offerCount.value} ${p.offerCount.value === 1 ? 'oferta' : 'ofertas'}` })
  if (location.value) items.push({ icon: 'map-pin', text: location.value })
  items.push({ icon: 'scissors', text: `Colección ${p.collectionTag.value}` })
  return items
})

// Rail de categorías como pestañas tipográficas grandes (no chips).
const tabs = computed(() => p.departments.value.slice(0, 8))
const activeTab = ref(null) // null = todo
const gridItems = computed(() => {
  const list = activeTab.value == null ? p.products.value : p.products.value.filter((x) => x.category === activeTab.value)
  return list.slice(0, 12)
})
// Ritmo editorial: 1 grande (4:5), 2 chicas (3:4), 1 grande invertida.
const cellClass = (i) => ['big', '', '', 'big inv'][i % 4]
const corteOf = (prod) => p.featureValues(prod, 'corte', 'fit', 'silueta')[0] || ''

// "Look completo": una imagen grande del pool con hotspots a productos.
const lookImage = computed(() => p.imagePool.value[1] || p.heroImage.value)
const lookProducts = computed(() => p.products.value.filter((x) => x.image).slice(0, 3))
const HOTSPOTS = [{ x: 30, y: 62 }, { x: 58, y: 38 }, { x: 74, y: 70 }]
const openSpot = ref(-1)
const toggleSpot = (i) => { openSpot.value = openSpot.value === i ? -1 : i }

// Etiqueta de prenda (cierre): ubicación + contacto + código de barras.
const address = computed(() => p.store.value?.location_address || '')

onMounted(() => { p.loadCatalog() })
</script>

<template>
<div class="sp-page-root at" :data-var="variant">
  <!-- ===== Hero asimétrico: titular en 3 tintas atravesando la imagen ===== -->
  <header class="at-hero">
    <span class="at-collection" aria-hidden="true">{{ p.collectionTag.value }}</span>
    <div v-if="p.heroImage.value" class="at-hero-media">
      <img :src="p.heroImage.value" :alt="`Portada de ${shopName}`" fetchpriority="high" decoding="async" />
    </div>
    <div class="at-hero-copy">
      <h1 class="at-title">
        <span class="at-line out">{{ titleLines[0] }}</span>
        <span class="at-line solid">{{ titleLines[1] }}</span>
        <span v-if="titleLines[2]" class="at-line cut">{{ titleLines[2] }}</span>
      </h1>
      <p v-if="custom.description" class="at-lede">{{ custom.description }}</p>
      <ul class="at-hero-meta">
        <li v-if="location"><AppIcon name="map-pin" :size="13" /> {{ location }}</li>
        <li v-if="p.openNow.value" :data-state="p.openNow.value.state"><AppIcon name="clock" :size="13" /> {{ p.openNow.value.text }}</li>
        <li v-if="custom.about_years"><AppIcon name="award" :size="13" /> +{{ custom.about_years }} años</li>
      </ul>
      <div class="at-hero-ctas">
        <RouterLink v-if="showCatalog" class="at-cta" :to="p.catalogTo.value">Ver colección <AppIcon name="arrow-right" :size="15" /></RouterLink>
        <a v-if="p.waBase.value" class="at-cta ghost" :href="p.waGeneral.value" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="15" /> Consultar</a>
      </div>
    </div>
  </header>

  <MarqueeBand :items="bandItems" :speed="30" />

  <!-- ===== Rail de departamentos: pestañas tipográficas grandes ===== -->
  <nav v-if="tabs.length" class="at-tabs" aria-label="Departamentos">
    <button type="button" class="at-tab" :class="{ on: activeTab === null }" @click="activeTab = null">Todo</button>
    <button
      v-for="d in tabs" :key="d.id" type="button"
      class="at-tab" :class="{ on: activeTab === d.id }"
      :aria-pressed="activeTab === d.id"
      @click="activeTab = activeTab === d.id ? null : d.id"
    >{{ d.name }}<sup>{{ d.count }}</sup></button>
  </nav>

  <!-- ===== Grilla editorial: ritmo 1 grande / 2 chicas / 1 grande invertida ===== -->
  <main class="at-main">
    <section v-if="gridItems.length" class="at-grid" aria-label="Selección de productos">
      <RouterLink
        v-for="(prod, i) in gridItems" :key="prod.id"
        class="at-card" :class="cellClass(i)"
        :to="p.productTo(prod)"
        :aria-label="`${prod.name} — ${p.formatARS(p.effectivePrice(prod))}`"
      >
        <span class="at-card-media">
          <img v-if="prod.image" :src="prod.image" :alt="prod.name" loading="lazy" decoding="async" />
          <span v-else class="at-card-ph"><AppIcon name="scissors" :size="30" /></span>
          <OfferSeal v-if="p.productOffer(prod) != null" :pct="p.offerPct(prod)" :shape="variant === 'street' ? 'ticket' : 'corner'" />
        </span>
        <span class="at-card-info">
          <span class="at-card-name">{{ prod.name }}</span>
          <span class="at-card-row">
            <StTag v-if="corteOf(prod)" kind="corte" :label="corteOf(prod)" />
            <span class="at-card-price"><s v-if="p.productOffer(prod) != null">{{ p.formatARS(prod.price) }}</s>{{ p.formatARS(p.effectivePrice(prod)) }}</span>
          </span>
        </span>
      </RouterLink>
    </section>

    <!-- Estado vacío diseñado: 0 productos -->
    <section v-else-if="showCatalog" class="at-empty">
      <span class="at-empty-mark"><AppIcon name="scissors" :size="26" /></span>
      <h2>La colección se está preparando</h2>
      <p>{{ shopName }} está cargando sus piezas. Volvé pronto o consultanos directo.</p>
      <a v-if="p.waBase.value" class="at-cta" :href="p.waGeneral.value" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="15" /> Consultar por WhatsApp</a>
    </section>

    <!-- ===== Look completo: hotspots sobre una imagen ===== -->
    <section v-if="lookImage && lookProducts.length" v-reveal class="at-look" aria-labelledby="at-look-t">
      <figure class="at-look-media">
        <img :src="lookImage" :alt="`Look de ${shopName}`" loading="lazy" decoding="async" />
        <button
          v-for="(prod, i) in lookProducts" :key="prod.id" type="button"
          class="at-hotspot" :class="{ on: openSpot === i }"
          :style="{ left: `${HOTSPOTS[i].x}%`, top: `${HOTSPOTS[i].y}%` }"
          :aria-label="`Ver ${prod.name}`" :aria-expanded="openSpot === i"
          @click="toggleSpot(i)"
        ></button>
        <TransitionGroup name="at-pop">
          <RouterLink
            v-for="(prod, i) in lookProducts" v-show="openSpot === i" :key="`card-${prod.id}`"
            class="at-spot-card" :style="{ left: `${HOTSPOTS[i].x}%`, top: `${HOTSPOTS[i].y}%` }"
            :to="p.productTo(prod)"
          >
            <img :src="prod.image" :alt="''" loading="lazy" />
            <span><strong>{{ prod.name }}</strong><em>{{ p.formatARS(p.effectivePrice(prod)) }}</em></span>
          </RouterLink>
        </TransitionGroup>
      </figure>
      <div class="at-look-copy">
        <h2 id="at-look-t">El look completo</h2>
        <p>Tocá los puntos sobre la imagen para ver cada pieza.</p>
      </div>
    </section>

    <!-- ===== Sobre la marca (solo con datos) ===== -->
    <section v-if="hasAbout" v-reveal class="at-about" aria-labelledby="at-about-t">
      <h2 id="at-about-t" class="at-about-title">{{ custom.about_title?.trim() || shopName }}</h2>
      <p v-if="custom.about_text" class="at-about-text">{{ custom.about_text }}</p>
      <p v-if="custom.about_mission" class="at-about-mission">{{ custom.about_mission }}</p>
      <div v-if="p.aboutSpecialties.value.length" class="at-about-tags">
        <StTag v-for="s in p.aboutSpecialties.value" :key="s" kind="corte" :label="s" />
      </div>
    </section>

    <!-- ===== Cierre: etiqueta de prenda ===== -->
    <section v-if="showContact || location || p.waBase.value" v-reveal id="contacto" class="at-tag" aria-labelledby="at-tag-t">
      <span class="at-tag-hole" aria-hidden="true"></span>
      <div class="at-tag-body">
        <h2 id="at-tag-t">{{ shopName }}</h2>
        <ul class="at-tag-meta">
          <li v-if="location"><AppIcon name="map-pin" :size="14" /> {{ location }}</li>
          <li v-if="address"><AppIcon name="store" :size="14" /> {{ address }}</li>
          <li v-if="p.openNow.value" :data-state="p.openNow.value.state"><AppIcon name="clock" :size="14" /> {{ p.openNow.value.text }}</li>
        </ul>
        <div class="at-tag-ctas">
          <a v-if="p.waBase.value" class="at-cta" :href="p.waGeneral.value" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="15" /> Escribinos</a>
          <RouterLink v-if="showCatalog" class="at-cta ghost" :to="p.catalogTo.value">Catálogo completo</RouterLink>
        </div>
        <ul v-if="p.socials.value.length" class="at-tag-social">
          <li v-for="s in p.socials.value" :key="s.key"><a :href="s.url" target="_blank" rel="noopener" :aria-label="s.label"><AppIcon :name="s.key" :size="16" /></a></li>
        </ul>
      </div>
      <span class="at-tag-barcode" aria-hidden="true"><i v-for="n in 24" :key="n"></i></span>
      <p class="at-tag-foot">{{ p.collectionTag.value }} · {{ shopName }} · {{ p.year }}</p>
    </section>
  </main>
</div>
</template>
