<script setup>
// Hero editorial asimétrico (§6.5-2): papel, copy en columnas 1-7 y visual en
// 8-12 con la placa de acento superpuesta. Sin banda de acento a sangre.
// En móvil el visual NO desaparece: pasa a una franja 3:2 entre el h1 y los
// CTAs (lo resuelve la grilla de áreas + display:contents del bloque copy).
import { computed, ref, inject, onMounted, onBeforeUnmount } from 'vue'
import { openStatus } from '../../../../utils/storeHours.js'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useRhLinks } from './rhLinks.js'

defineProps({ block: { type: Object, default: null } })

const { ctx, catalogTo, servicesTo } = useRhLinks()
const { custom, shopName, nameFont, initial, location, showCatalog, showContact, hasDesignAdvanced } = ctx
const servicesPage = ctx.showServices

const heroTitleIsName = computed(() => !custom.value.headline?.trim())
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value)
const heroBadge = computed(() => (heroTitleIsName.value
  ? (location.value || (showCatalog.value ? 'Catálogo online' : 'Sitio oficial'))
  : shopName.value))

// Visual: portada premium → primera foto real de la galería. Sin ninguna
// imagen la placa se resuelve tipográficamente con el monograma y el nombre
// (nunca queda un hueco y no hay CLS por una carga tardía del catálogo).
const galleryPhotos = computed(() => (Array.isArray(custom.value.gallery) ? custom.value.gallery : []))
const heroImage = computed(() => {
  if (hasDesignAdvanced.value && custom.value.cover) {
    return { url: custom.value.cover, alt: `Portada de ${shopName.value}` }
  }
  if (ctx.showGallery.value && galleryPhotos.value[0]?.url) {
    return { url: galleryPhotos.value[0].url, alt: `Imagen de ${shopName.value}` }
  }
  return null
})
// Sello de acento (uno por página): años, ubicación o estado del catálogo.
const seal = computed(() => (
  custom.value.about_years
    ? `+${custom.value.about_years} años`
    : (location.value || (showCatalog.value ? 'Catálogo online' : 'Sitio oficial'))
))

// Estado de atención en vivo (mismo criterio conservador que el resto de la web).
const now = ref(new Date())
let clock = null
const openNow = computed(() => (custom.value.show_hours !== false ? openStatus(custom.value.hours, now.value) : null))
const meta = computed(() => {
  const items = []
  if (!heroTitleIsName.value && location.value) items.push({ key: 'loc', icon: 'map-pin', text: location.value })
  if (openNow.value) items.push({ key: 'open', state: openNow.value.state, text: openNow.value.text })
  if (custom.value.about_years) items.push({ key: 'years', icon: 'clock', text: `+${custom.value.about_years} años` })
  return items
})

// Compartir: Web Share API con fallback a clipboard (idéntico al hero actual).
const copied = ref(false)
let copiedTimer = null
async function share() {
  const data = {
    title: shopName.value,
    text: custom.value.description?.trim() || `Mirá ${shopName.value}`,
    url: window.location.href
  }
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
    clearTimeout(copiedTimer)
    copiedTimer = setTimeout(() => { copied.value = false }, 2500)
  } catch {
    // Sin clipboard: el link ya está en la barra del navegador.
  }
}

onMounted(() => { clock = setInterval(() => { now.value = new Date() }, 60000) })
onBeforeUnmount(() => {
  clearInterval(clock)
  clearTimeout(copiedTimer)
})
</script>

<template>
  <section class="rh-hero rh-numbered" aria-labelledby="rh-hero-title">
    <div class="rh-wrap rh-hero-grid">
      <div class="rh-hero-copy">
        <p v-reveal class="rz-eyebrow rh-hero-eyebrow">
          <span class="rz-eyebrow-num rh-secnum" aria-hidden="true"></span>
          {{ heroBadge }}
        </p>

        <h1 id="rh-hero-title" v-reveal="60" class="rh-hero-title" :style="heroTitleIsName ? nameFont : null">
          {{ heroTitle }}
        </h1>

        <p v-if="custom.description" v-reveal="120" class="rh-hero-lead">{{ custom.description }}</p>

        <div v-reveal="180" class="rh-hero-ctas">
          <RouterLink v-if="showCatalog" class="rz-btn rh-hero-btn" :to="catalogTo">
            Ver catálogo <AppIcon name="arrow-right" :size="16" />
          </RouterLink>
          <RouterLink
            v-if="servicesPage" class="rz-btn rz-btn--ghost" :to="servicesTo"
            :aria-label="showCatalog ? 'Ver servicios' : 'Ver servicios y pedir presupuesto'"
          >
            Servicios <AppIcon name="wrench" :size="16" />
          </RouterLink>
          <a v-if="showContact" class="rh-hero-contact" href="#contacto">
            <AppIcon name="message-circle" :size="16" /> Contáctanos
          </a>
          <button
            type="button" class="rh-hero-share"
            :aria-label="copied ? 'Link copiado' : 'Compartir tienda'"
            :title="copied ? 'Link copiado' : 'Compartir'"
            @click="share"
          >
            <AppIcon :name="copied ? 'check' : 'share-2'" :size="16" />
            <span>{{ copied ? 'Copiado' : 'Compartir' }}</span>
          </button>
        </div>

        <ul v-if="meta.length" v-reveal="240" class="rh-hero-meta">
          <li v-for="m in meta" :key="m.key" :class="m.state ? `rh-open is-${m.state}` : null">
            <span v-if="m.state" class="rh-open-dot" aria-hidden="true"></span>
            <AppIcon v-else :name="m.icon" :size="14" aria-hidden="true" />
            {{ m.text }}
          </li>
        </ul>
      </div>

      <div v-reveal="300" class="rh-hero-aside">
        <figure v-if="heroImage" class="rz-frame rh-hero-media">
          <img :src="heroImage.url" :alt="heroImage.alt" fetchpriority="high" />
        </figure>
        <div v-else class="rh-hero-block">
          <img v-if="custom.logo" class="rh-hero-logo" :src="custom.logo" :alt="`Logo de ${shopName}`" />
          <span v-else class="rh-hero-initial" :style="nameFont" aria-hidden="true">{{ initial }}</span>
          <span class="rh-hero-block-rule" aria-hidden="true"></span>
          <span class="rh-hero-block-name" :style="nameFont">{{ shopName }}</span>
        </div>
        <span class="rz-plate rh-hero-seal">{{ seal }}</span>
      </div>
    </div>
  </section>
</template>
