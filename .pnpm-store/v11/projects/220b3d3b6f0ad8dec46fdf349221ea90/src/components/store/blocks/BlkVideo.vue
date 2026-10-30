<script setup>
// Bloque 'video': embed de YouTube/Vimeo en su propia sección (el backend
// ya guarda la URL de embed normalizada). props.title pisa el título.
import { computed, inject } from 'vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom } = ctx

const videoEmbed = computed(() => (custom.value.video_url || '').trim())
const show = computed(() => custom.value.show_video !== false && Boolean(videoEmbed.value))
const videoTitle = computed(() => props.block?.props?.title?.trim() || custom.value.video_title?.trim() || 'Mirá nuestro video')
</script>

<template>
  <section v-if="show" class="sp-video" aria-labelledby="sp-video-title">
    <div class="sp-container">
      <header v-reveal class="sp-video-head">
        <h2 id="sp-video-title" class="sp-video-title">{{ videoTitle }}</h2>
      </header>
      <div v-reveal="80" class="sp-video-frame">
        <iframe
          :src="videoEmbed" :title="videoTitle" loading="lazy" allowfullscreen
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          referrerpolicy="strict-origin-when-cross-origin"
        ></iframe>
      </div>
    </div>
  </section>
</template>
