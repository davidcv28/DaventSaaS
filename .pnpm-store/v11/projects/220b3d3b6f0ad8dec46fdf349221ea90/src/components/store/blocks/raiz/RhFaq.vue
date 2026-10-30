<script setup>
// FAQ (§6.5-15): dos columnas — título sticky a la izquierda, <details>
// nativos a la derecha. NUNCA centrada a 860. Datos reales de "Preguntas
// frecuentes" ({q,a}).
import { computed } from 'vue'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useRhLinks } from './rhLinks.js'

const props = defineProps({ block: { type: Object, default: null } })

const { ctx } = useRhLinks()
const { custom, showContact } = ctx

const faqs = computed(() => (Array.isArray(custom.value.faqs) ? custom.value.faqs : []))
const show = computed(() => custom.value.show_faq !== false && faqs.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || custom.value.faqs_title?.trim() || 'Preguntas frecuentes')
</script>

<template>
  <section v-if="show" class="rz-section rh-numbered rh-faq" aria-labelledby="rh-faq-title">
    <div class="rh-wrap rh-faq-grid">
      <div class="rh-faq-aside">
        <p v-reveal class="rz-eyebrow">
          <span class="rz-eyebrow-num rh-secnum" aria-hidden="true"></span>
          Dudas frecuentes
        </p>
        <h2 id="rh-faq-title" v-reveal class="rh-title">{{ title }}</h2>
        <p v-if="showContact" v-reveal="60" class="rh-faq-note">
          ¿No encontrás tu respuesta?
          <a class="rh-link rh-link--inline" href="#contacto">Escribinos</a>
        </p>
      </div>

      <div class="rh-faq-list">
        <details v-for="(f, i) in faqs" :key="i" v-reveal="60 * (i % 4)" class="rh-faq-item">
          <summary class="rh-faq-q">
            <span>{{ f.q }}</span>
            <span class="rh-faq-icon" aria-hidden="true"><AppIcon name="plus" :size="18" /></span>
          </summary>
          <p class="rh-faq-a">{{ f.a }}</p>
        </details>
      </div>
    </div>
  </section>
</template>
