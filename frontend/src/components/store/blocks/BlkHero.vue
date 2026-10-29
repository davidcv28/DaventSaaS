<script setup>
// Bloque 'hero' de la web pública: dos composiciones vivas.
//  - variant 'logo': sin foto, el logo (o monograma) es la pieza central.
//  - variantes de la familia ALT (centered/split/cinema/editorial/search/
//    slides): BlkHeroAlt, la portada partida que usa Raíz.
//  - fallback: banda de acento con avatar, badge, titular, CTAs, compartir y
//    meta. Es el hero de las webs sin variante y el respaldo del motor de IA.
import { ref, computed, inject, onMounted, onBeforeUnmount } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { openStatus } from '../../../utils/storeHours.js'
import AppIcon from '../../AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import BlkHeroAlt from './BlkHeroAlt.vue'

const props = defineProps({ block: { type: Object, default: null } })

const ALT = ['centered', 'split', 'cinema', 'editorial', 'search', 'slides']
const isAlt = computed(() => ALT.includes(props.block?.variant))
const isLogo = computed(() => props.block?.variant === 'logo')

const ctx = inject('storePage')
const { slug, custom, shopName, nameFont, initial, location, hasAbout, showContact, showCatalog, hasDesignAdvanced } = ctx

const copied = ref(false)
const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const servicesPage = ctx.showServices
const servicesTo = computed(() => ({ name: 'store-services', params: storeHostSlug ? {} : { slug: slug.value } }))
const whatsappUrl = computed(() => (custom.value.whatsapp ? `https://wa.me/${custom.value.whatsapp.replace(/\D/g, '')}` : ''))

// Imagen de portada (premium): fondo del hero. Sin diseño avanzado no se usa
// aunque haya quedado una guardada.
const cover = computed(() => (hasDesignAdvanced.value ? custom.value.cover || '' : ''))

const heroTitleIsName = computed(() => !custom.value.headline?.trim())
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value)
const heroBadge = computed(() => (heroTitleIsName.value ? (location.value || (showCatalog.value ? 'Catálogo online' : 'Sitio oficial')) : shopName.value))
const heroBadgeIcon = computed(() => (heroTitleIsName.value ? (location.value ? 'map-pin' : 'store') : ''))

const now = ref(new Date())
let clock = null
const openNow = computed(() => (custom.value.show_hours !== false ? openStatus(custom.value.hours, now.value) : null))
const heroMeta = computed(() => {
  const items = []
  if (!heroTitleIsName.value && location.value) items.push({ key: 'loc', icon: 'map-pin', text: location.value })
  if (openNow.value) items.push({ key: 'open', state: openNow.value.state, text: openNow.value.text })
  if (custom.value.about_years) items.push({ key: 'years', icon: 'clock', text: `+${custom.value.about_years} años de trayectoria` })
  return items
})

async function share() {
  const data = { title: shopName.value, text: custom.value.description?.trim() || `Mirá ${shopName.value}`, url: window.location.href }
  if (navigator.share) {
    try {
      await navigator.share(data)
      return
    } catch (e) {
      if (e?.name === 'AbortError') return
    }
  }
  try {
    await navigator.clipboard.writeText(window.location.href)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2500)
  } catch {
    // Sin clipboard disponible: el link ya está en la barra del navegador.
  }
}

// Parallax de la placa: desplazamiento ≤ 3.5% del alto, solo con puntero
// fino y sin reduced-motion. Un rAF por scroll, lectura de rect barata.
const heroEl = ref(null)
const finePointer = window.matchMedia?.('(hover: hover) and (pointer: fine)')?.matches
const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
let scrollRaf = 0
let settleTimer = null
function onHeroScroll() {
  if (scrollRaf) return
  scrollRaf = requestAnimationFrame(() => {
    scrollRaf = 0
    const el = heroEl.value
    if (!el) return
    const r = el.getBoundingClientRect()
    if (r.bottom < -80 || r.top > window.innerHeight) return
    const p = Math.min(1, Math.max(0, -r.top / Math.max(1, r.height)))
    el.style.setProperty('--sp-hero-shift', `${(p * -14).toFixed(2)}px`)
  })
}

onMounted(() => {
  clock = setInterval(() => { now.value = new Date() }, 60000)
  // Red de seguridad de la entrada orquestada: si la pestaña queda en segundo
  // plano o el motor no corre animaciones, la portada queda visible.
  settleTimer = setTimeout(() => { heroEl.value?.classList.add('is-settled') }, 2200)
  if (finePointer && !reduceMotion) {
    window.addEventListener('scroll', onHeroScroll, { passive: true })
    onHeroScroll()
  }
})
onBeforeUnmount(() => {
  clearInterval(clock)
  clearTimeout(settleTimer)
  window.removeEventListener('scroll', onHeroScroll)
  if (scrollRaf) cancelAnimationFrame(scrollRaf)
})
</script>

<template>
  <!-- ===== Presentación (portada de la empresa) ===== -->
  <section v-if="isLogo" class="sp-hero-logo">
    <div class="sp-container sp-hero-logo-inner">
      <div class="sp-hero-logo-mark" :class="{ 'has-logo': custom.logo }" aria-hidden="true">
        <img v-if="custom.logo" :src="custom.logo" alt="" fetchpriority="high" />
        <span v-else class="sp-hero-logo-mono" :style="nameFont">{{ initial }}</span>
      </div>
      <p v-reveal class="sp-hero-logo-eyebrow">{{ heroBadge }}</p>
      <h1 v-reveal="120" class="sp-hero-logo-title" :class="{ 'is-name': heroTitleIsName }" :style="heroTitleIsName ? nameFont : null">{{ heroTitle }}</h1>
      <p v-if="custom.description" v-reveal="200" class="sp-hero-logo-sub">{{ custom.description }}</p>
      <div v-reveal="280" class="sp-hero-logo-ctas">
        <RouterLink v-if="showCatalog" class="sp-btn sp-hero-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
        <RouterLink v-if="servicesPage" class="sp-btn" :class="showCatalog ? 'sp-hero-ghost' : 'sp-hero-btn'" :to="servicesTo">Servicios <AppIcon name="wrench" :size="16" /></RouterLink>
        <a v-if="showContact" class="sp-btn sp-hero-ghost" href="#contacto"><AppIcon name="message-circle" :size="16" /> Contáctanos</a>
      </div>
      <ul v-if="heroMeta.length" v-reveal="360" class="sp-hero-logo-meta">
        <li v-for="m in heroMeta" :key="m.key" :class="m.state ? `sp-open is-${m.state}` : null"><span v-if="m.state" class="sp-live-dot" aria-hidden="true"></span><AppIcon v-else :name="m.icon" :size="14" /> {{ m.text }}</li>
      </ul>
    </div>
  </section>
  <BlkHeroAlt v-else-if="isAlt" :block="block" />
  <section v-else ref="heroEl" class="sp-hero" :class="{ 'is-compact': block?.variant === 'compact' }">
    <div class="sp-hero-band" :class="{ 'has-cover': cover }">
      <div v-if="cover" class="sp-hero-cover" aria-hidden="true">
        <img :src="cover" alt="" fetchpriority="high" />
      </div>
      <div class="sp-hero-decor" aria-hidden="true">
        <span class="sp-orb o1"></span>
        <span class="sp-orb o2"></span>
        <span class="sp-orb o3"></span>
        <span class="sp-float f1"><AppIcon name="package" :size="26" /></span>
        <span class="sp-float f2"><AppIcon name="tag" :size="22" /></span>
        <span class="sp-float f3"><AppIcon name="shield-check" :size="24" /></span>
        <span class="sp-float f4"><AppIcon name="trending-up" :size="22" /></span>
        <span class="sp-float f5"><AppIcon name="store" :size="24" /></span>
      </div>
      <div class="sp-container sp-hero-inner">
        <span v-reveal class="sp-ava">
          <img v-if="custom.logo" class="sp-logo lg" :src="custom.logo" :alt="`Logo de ${shopName}`" />
          <span v-else class="sp-mono lg" aria-hidden="true">{{ initial }}</span>
        </span>
        <p v-reveal="80" class="sp-hero-badge">
          <AppIcon v-if="heroBadgeIcon" :name="heroBadgeIcon" :size="13" />
          {{ heroBadge }}
        </p>
        <h1 v-reveal="160" class="sp-hero-title" :class="{ 'is-name': heroTitleIsName }" :style="heroTitleIsName ? nameFont : null">{{ heroTitle }}</h1>
        <p v-if="custom.description" v-reveal="240" class="sp-hero-sub">{{ custom.description }}</p>
        <div v-reveal="320" class="sp-hero-ctas">
          <RouterLink v-if="showCatalog" class="sp-btn sp-hero-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
          <RouterLink v-if="servicesPage" class="sp-btn" :class="showCatalog ? 'sp-hero-ghost' : 'sp-hero-btn'" :to="servicesTo">Servicios <AppIcon name="wrench" :size="16" /></RouterLink>
          <a v-if="showContact" class="sp-btn sp-hero-ghost" href="#contacto"><AppIcon name="message-circle" :size="16" /> Contáctanos</a>
          <button type="button" class="sp-icon-btn" :aria-label="copied ? 'Link copiado' : 'Compartir tienda'" :title="copied ? 'Link copiado' : 'Compartir'" @click="share">
            <AppIcon :name="copied ? 'check' : 'share-2'" :size="17" />
          </button>
        </div>
        <ul v-if="heroMeta.length" v-reveal="400" class="sp-hero-meta">
          <li v-for="m in heroMeta" :key="m.key" :class="m.state ? `sp-open is-${m.state}` : null"><span v-if="m.state" class="sp-live-dot" aria-hidden="true"></span><AppIcon v-else :name="m.icon" :size="14" /> {{ m.text }}</li>
        </ul>
      </div>
    </div>
  </section>
</template>
