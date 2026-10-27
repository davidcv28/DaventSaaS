<script setup>
// Bloque 'cta': banda de llamado a la acción de cierre de la portada. El
// botón apunta a WhatsApp si el dueño cargó uno; si no, al formulario de
// contacto o al catálogo (en ese orden). La banda solo existe si hay
// título o texto cargados. props.title pisa el título de la banda.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom, showContact, showCatalog } = ctx
const servicesPage = ctx.showServices

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const servicesTo = computed(() => ({ name: 'store-services', params: storeHostSlug ? {} : { slug: slug.value } }))
const whatsappUrl = computed(() => (custom.value.whatsapp ? `https://wa.me/${custom.value.whatsapp.replace(/\D/g, '')}` : ''))

const show = computed(() => custom.value.show_cta !== false
  && Boolean(custom.value.cta_title?.trim() || custom.value.cta_text?.trim() || props.block?.props?.title?.trim()))
const ctaTitle = computed(() => props.block?.props?.title?.trim() || custom.value.cta_title?.trim() || '¿Hablamos?')
const ctaLink = computed(() => {
  if (whatsappUrl.value) return { href: whatsappUrl.value, external: true }
  if (showContact.value) return { href: '#contacto', external: false }
  if (showCatalog.value) return { to: catalogTo.value, external: false }
  if (servicesPage.value) return { to: servicesTo.value, external: false }
  return null
})
const ctaLabel = computed(() => custom.value.cta_label?.trim()
  || (ctaLink.value?.external ? 'Escribinos por WhatsApp' : ctaLink.value?.href === '#contacto' ? 'Contáctanos' : ctaLink.value?.to === servicesTo.value ? 'Ver servicios' : 'Ver catálogo'))
</script>

<template>
  <section v-if="show" class="sp-cta">
    <div class="sp-container sp-cta-inner">
      <h2 v-reveal class="sp-cta-title">{{ ctaTitle }}</h2>
      <p v-if="custom.cta_text" v-reveal="80" class="sp-cta-text">{{ custom.cta_text }}</p>
      <component
        v-if="ctaLink" :is="ctaLink.to ? 'RouterLink' : 'a'" v-reveal="160" class="sp-btn sp-cta-btn"
        :to="ctaLink.to" :href="ctaLink.href"
        :target="ctaLink.external ? '_blank' : null" :rel="ctaLink.external ? 'noopener' : null"
      >
        {{ ctaLabel }} <AppIcon name="arrow-right" :size="16" class="sp-arrow" />
      </component>
    </div>
  </section>
</template>
