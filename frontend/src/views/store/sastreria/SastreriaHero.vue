<script setup>
// Portada firma de SASTRERÍA (indumentaria editorial, nivel plus).
// Asimétrica: titular Fraunces con la última palabra en itálica de cuero,
// ficha de atelier (ciudad/horario/teléfono) y una portada alta con índice
// 01 y pie de foto. Debajo, un muestrario de materiales cierra el hueco.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom, shopName, location, showCatalog } = ctx

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const headline = computed(() => custom.value.headline?.trim() || shopName.value || 'Sastrería de autor, corte a medida.')
const words = computed(() => headline.value.split(/\s+/).filter(Boolean))
const lead = computed(() => (words.value.length > 1 ? words.value.slice(0, -1).join(' ') : headline.value))
const accent = computed(() => (words.value.length > 1 ? words.value[words.value.length - 1] : ''))
const text = computed(() => custom.value.description?.trim()
  || 'Prendas de lino, lana y algodón cortadas en el taller, con ajustes incluidos y encargos a medida.')
const cover = computed(() => custom.value.cover || '')
const phone = computed(() => custom.value.whatsapp || '')
const hours = computed(() => {
  const rows = Array.isArray(custom.value.hours) ? custom.value.hours.filter((h) => h && !h.closed) : []
  return rows.length ? 'Horarios en el local' : ''
})
const address = computed(() => (custom.value.show_location === false ? '' : location.value || ''))
const centered = computed(() => props.block?.variant === 'centered')
</script>

<template>
  <section class="ss-hero" :class="{ 'is-centered': centered }" aria-labelledby="ss-hero-title">
    <div class="ss-wrap ss-hero-grid">
      <div class="ss-hero-copy">
        <p v-reveal class="ss-kicker">01 — Colección</p>
        <h1 id="ss-hero-title" v-reveal="40">
          {{ lead }} <em v-if="accent">{{ accent }}</em>
        </h1>
        <p v-reveal="80" class="ss-hero-text">{{ text }}</p>
        <div v-reveal="120" class="ss-actions">
          <RouterLink v-if="showCatalog" class="ss-btn ss-btn-primary" :to="catalogTo">
            Ver la colección <AppIcon name="arrow-right" :size="15" />
          </RouterLink>
          <a v-if="phone" class="ss-btn ss-btn-ghost" :href="`https://wa.me/${String(phone).replace(/\D/g, '')}`">Pedir turno</a>
        </div>
        <dl v-reveal="160" class="ss-specs">
          <div><dt>Atelier</dt><dd>{{ location || shopName }}</dd></div>
          <div><dt>Horarios</dt><dd>{{ hours || 'Consultar' }}</dd></div>
          <div><dt>Contacto</dt><dd>{{ phone || 'Consultar' }}</dd></div>
        </dl>
      </div>
      <figure v-reveal="60" class="ss-hero-media">
        <img v-if="cover" :src="cover" :alt="shopName" loading="eager" />
        <span v-else class="ss-hero-initial" aria-hidden="true">{{ (shopName || 'S').slice(0, 1) }}</span>
        <span class="ss-hero-index" aria-hidden="true">01</span>
        <figcaption class="ss-hero-note">
          <span class="tag">Pieza de temporada</span>
          <strong>{{ shopName }}</strong>
          <span v-if="address">{{ address }}</span>
          <a v-if="phone" :href="`https://wa.me/${String(phone).replace(/\D/g, '')}`">Consultar disponibilidad</a>
        </figcaption>
      </figure>
    </div>
    <div v-reveal="200" class="ss-wrap ss-swatches" aria-hidden="true">
      <div class="ss-swatch"><span class="chip"></span><span><b>Lino</b><small>Ligero, de verano</small></span></div>
      <div class="ss-swatch"><span class="chip"></span><span><b>Lana</b><small>Fieltro y sastrería</small></span></div>
      <div class="ss-swatch"><span class="chip"></span><span><b>Cuero</b><small>Accesorios curtidos</small></span></div>
    </div>
  </section>
</template>
