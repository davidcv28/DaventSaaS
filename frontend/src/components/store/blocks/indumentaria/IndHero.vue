<script setup>
// Portada firma de INDUMENTARIA (lookbook / runway, nivel plus).
// Editorial de moda: rail lateral "COLECCIÓN / 01", titular display con la
// última palabra destacada, foto de campaña alta con etiqueta colgante y
// cinta marquee inferior con datos reales de la tienda (temporada, envíos,
// atención). La etiqueta parpadea sutil y la foto hace parallax leve.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../../config/env.js'
import { storeContactLink, hasContactChannel } from '../../../../api/stores.api.js'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom, shopName, location, showCatalog } = ctx

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const headline = computed(() => custom.value.headline?.trim() || shopName.value || 'Nueva temporada, prendas con carácter.')
const words = computed(() => headline.value.split(/\s+/).filter(Boolean))
const lead = computed(() => (words.value.length > 1 ? words.value.slice(0, -1).join(' ') : headline.value))
const accent = computed(() => (words.value.length > 1 ? words.value[words.value.length - 1] : ''))
const text = computed(() => custom.value.description?.trim()
  || 'Colección de temporada: prendas seleccionadas, talles reales y lanzamientos cada semana.')
const cover = computed(() => custom.value.cover || '')
const hasWa = computed(() => hasContactChannel(custom.value, 'whatsapp'))
const waUrl = computed(() => (hasWa.value ? storeContactLink(slug.value, 'whatsapp') : ''))
const address = computed(() => (custom.value.show_location === false ? '' : location.value || ''))
const year = computed(() => new Date().getFullYear())
// Cinta de temporada: solo ítems reales del negocio, duplicada para el loop.
const ribbon = computed(() => {
  const items = [`Nueva temporada ${year.value}`]
  if (shopName.value) items.push(shopName.value)
  if (hasWa.value) items.push('Atención por WhatsApp')
  if (address.value) items.push(address.value)
  items.push('Envíos a todo el país')
  return items
})
const centered = computed(() => props.block?.variant === 'centered')
</script>

<template>
  <section class="in-hero" :class="{ 'is-centered': centered }" aria-labelledby="in-hero-title">
    <div class="in-wrap in-hero-grid">
      <p class="in-rail" aria-hidden="true"><span>Colección</span><b>/ 01</b></p>
      <div class="in-hero-copy">
        <p v-reveal class="in-kicker">Lookbook — {{ year }}</p>
        <h1 id="in-hero-title" v-reveal="40">
          {{ lead }} <em v-if="accent">{{ accent }}</em>
        </h1>
        <p v-reveal="80" class="in-hero-text">{{ text }}</p>
        <div v-reveal="120" class="in-actions">
          <RouterLink v-if="showCatalog" class="in-btn in-btn-primary" :to="catalogTo">
            Ver la colección <AppIcon name="arrow-right" :size="15" />
          </RouterLink>
          <a v-if="waUrl" class="in-btn in-btn-ghost" :href="waUrl" target="_blank" rel="noopener">Consultar talles</a>
        </div>
        <ul v-reveal="160" class="in-hero-meta">
          <li v-if="address"><span class="in-meta-k">Tienda</span><span>{{ address }}</span></li>
          <li><span class="in-meta-k">Temporada</span><span>{{ year }}</span></li>
          <li><span class="in-meta-k">Contacto</span><span>{{ hasWa ? 'WhatsApp' : 'Consultar' }}</span></li>
        </ul>
      </div>
      <figure v-reveal="60" class="in-hero-media">
        <img v-if="cover" :src="cover" :alt="shopName" loading="eager" fetchpriority="high" />
        <span v-else class="in-hero-initial" aria-hidden="true">{{ (shopName || 'I').slice(0, 1) }}</span>
        <span class="in-tag" aria-hidden="true"><i>LOOK</i><b>01</b></span>
        <figcaption class="in-hero-note">
          <span class="tag">Pieza de campaña</span>
          <strong>{{ shopName }}</strong>
          <a v-if="waUrl" :href="waUrl" target="_blank" rel="noopener">Consultar disponibilidad</a>
        </figcaption>
      </figure>
    </div>
    <div class="in-marq" aria-hidden="true">
      <div class="in-marq-track">
        <span v-for="(item, i) in ribbon" :key="'a' + i" class="in-marq-item">{{ item }}<i>·</i></span>
        <span v-for="(item, i) in ribbon" :key="'b' + i" class="in-marq-item">{{ item }}<i>·</i></span>
      </div>
    </div>
  </section>
</template>
