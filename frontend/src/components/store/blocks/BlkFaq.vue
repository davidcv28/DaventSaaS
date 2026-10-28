<script setup>
// Bloque 'faq' (Preguntas frecuentes): respuestas desplegables. Se apaga
// con show_faq y se oculta solo sin ítems. props.title pisa el título.
import { computed, inject } from 'vue'
import AppIcon from '../../AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom, pageTemplate, showContact } = ctx
const tpl = pageTemplate

const faqs = computed(() => (Array.isArray(custom.value.faqs) ? custom.value.faqs : []))
const show = computed(() => custom.value.show_faq !== false && faqs.value.length > 0)
const faqsTitle = computed(() => props.block?.props?.title?.trim() || custom.value.faqs_title?.trim() || 'Preguntas frecuentes')
const eyebrowUnless = (label, title) => (String(title || '').trim().toLowerCase() === label.toLowerCase() ? '' : label)
const faqEyebrow = computed(() => eyebrowUnless('Dudas frecuentes', faqsTitle.value))
</script>

<template>
  <section v-if="show" class="sp-faq" aria-labelledby="sp-faq-title">
    <div class="sp-container sp-faq-wrap">
      <div class="sp-faq-intro">
        <p v-if="faqEyebrow" class="sp-eyebrow">{{ faqEyebrow }}</p>
        <h2 id="sp-faq-title" v-reveal class="sp-section-title">{{ faqsTitle }}</h2>
        <p v-if="tpl === 'shop'" class="sp-faq-note">
          ¿No encontrás lo que buscás?
          <a v-if="showContact" href="#contacto">Escribinos</a><template v-else>Consultanos por WhatsApp.</template>
        </p>
      </div>
      <div class="sp-faq-list">
        <details v-for="(f, i) in faqs" :key="i" v-reveal="(i % 4) * 60" class="sp-faq-item">
          <summary>{{ f.q }}<span class="sp-faq-caret" aria-hidden="true"><AppIcon name="chevron-down" :size="16" /></span></summary>
          <p class="sp-faq-answer">{{ f.a }}</p>
        </details>
      </div>
    </div>
  </section>
</template>
