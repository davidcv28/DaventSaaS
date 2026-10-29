<script setup>
// Bloque 'aimosaic' (solo IA): mosaico de fotos de la tienda (galería +
// imágenes ilustrativas premium) con título y epígrafe. Sin fotos no monta.
// Variantes: mosaic (por defecto) | rail.
import { computed, inject } from 'vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })
const ctx = inject('storePage')

const title = computed(() => String(props.block?.props?.title || '').trim().slice(0, 80))
const caption = computed(() => String(props.block?.props?.caption || '').trim().slice(0, 120))

const images = computed(() => {
  const raw = props.block?.props?.items
  const fromProps = Array.isArray(raw)
    ? raw.map((i) => String((typeof i === 'string' ? i : i?.image) || '').trim()).filter(Boolean)
    : []
  if (fromProps.length) return fromProps.slice(0, 9)
  const custom = ctx?.custom?.value || {}
  const pool = [
    ...(Array.isArray(custom.gallery) ? custom.gallery : []),
    ...(Array.isArray(custom.decor) ? custom.decor : [])
  ]
  return [...new Set(pool.filter((src) => typeof src === 'string' && src.trim()))].slice(0, 9)
})
const variant = computed(() => (props.block?.variant === 'rail' ? 'rail' : 'mosaic'))
</script>

<template>
  <section v-if="images.length" class="sp-aimosaic" :class="`is-${variant}`" :data-blk-variant="variant !== 'mosaic' ? variant : null">
    <div class="sp-container sp-aimosaic-inner">
      <h2 v-if="title" v-reveal class="sp-section-title sp-aimosaic-title">{{ title }}</h2>
      <ul class="sp-aimosaic-list">
        <li v-for="(src, i) in images" :key="`${i}-${src}`" v-reveal="(i % 4) * 60" class="sp-aimosaic-tile">
          <img :src="src" alt="" loading="lazy" decoding="async" />
        </li>
      </ul>
      <p v-if="caption" class="sp-aimosaic-caption">{{ caption }}</p>
    </div>
  </section>
</template>
