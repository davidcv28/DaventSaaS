<script setup>
// Bloque 'aiband' (solo IA): banda CTA intermedia con fondo de acento y
// botón al mismo destino que el bloque 'cta' (WhatsApp → contacto →
// catálogo → servicios). Sin título ni texto no monta.
// Variantes: band (por defecto) | card.
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

const title = computed(() => String(props.block?.props?.title || '').trim().slice(0, 80))
const text = computed(() => String(props.block?.props?.text || '').trim().slice(0, 160))
const label = computed(() => String(props.block?.props?.label || '').trim().slice(0, 40))
const show = computed(() => Boolean(title.value || text.value))
const variant = computed(() => (props.block?.variant === 'card' ? 'card' : 'band'))

const link = computed(() => {
  if (whatsappUrl.value) return { href: whatsappUrl.value, external: true }
  if (showContact.value) return { href: '#contacto', external: false }
  if (showCatalog.value) return { to: catalogTo.value, external: false }
  if (servicesPage.value) return { to: servicesTo.value, external: false }
  return null
})
const linkLabel = computed(() => label.value
  || (link.value?.external ? 'Escribinos por WhatsApp' : link.value?.href === '#contacto' ? 'Contáctanos' : link.value?.to === servicesTo.value ? 'Ver servicios' : 'Ver catálogo'))
</script>

<template>
  <section v-if="show" class="sp-aiband" :class="`is-${variant}`" :data-blk-variant="variant !== 'band' ? variant : null">
    <div class="sp-container">
      <div class="sp-aiband-inner">
        <div class="sp-aiband-copy">
          <h2 v-if="title" v-reveal class="sp-aiband-title">{{ title }}</h2>
          <p v-if="text" v-reveal="80" class="sp-aiband-text">{{ text }}</p>
        </div>
        <component
          :is="link?.to ? 'RouterLink' : 'a'" v-reveal="160" class="sp-btn sp-aiband-btn"
          :to="link?.to" :href="link?.href"
          :target="link?.external ? '_blank' : null" :rel="link?.external ? 'noopener' : null"
        >
          {{ linkLabel }} <AppIcon name="arrow-right" :size="16" class="sp-arrow" />
        </component>
      </div>
    </div>
  </section>
</template>
