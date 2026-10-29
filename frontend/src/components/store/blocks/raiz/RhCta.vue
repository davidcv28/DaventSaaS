<script setup>
// CTA final (§6.5-16): BANDA DE ACENTO distinta de la banda de beneficios —
// full-bleed, tipografía display y botón de tinta, no la misma caja repetida.
// El botón apunta a WhatsApp, al formulario de contacto o al catálogo.
import { computed } from 'vue'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useRhLinks } from './rhLinks.js'

const props = defineProps({ block: { type: Object, default: null } })

const { ctx, catalogTo, servicesTo, whatsappUrl } = useRhLinks()
const { custom, showContact, showCatalog } = ctx
const servicesPage = ctx.showServices

const show = computed(() => custom.value.show_cta !== false
  && Boolean(custom.value.cta_title?.trim() || custom.value.cta_text?.trim() || props.block?.props?.title?.trim()))
const title = computed(() => props.block?.props?.title?.trim() || custom.value.cta_title?.trim() || '¿Hablamos?')
const link = computed(() => {
  if (whatsappUrl.value) return { href: whatsappUrl.value, external: true }
  if (showContact.value) return { href: '#contacto', external: false }
  if (showCatalog.value) return { to: catalogTo.value, external: false }
  if (servicesPage.value) return { to: servicesTo.value, external: false }
  return null
})
const label = computed(() => custom.value.cta_label?.trim()
  || (link.value?.external ? 'Escribinos por WhatsApp'
    : link.value?.href === '#contacto' ? 'Contáctanos'
      : link.value?.to === servicesTo.value ? 'Ver servicios' : 'Ver catálogo'))
</script>

<template>
  <section v-if="show" class="rz-section rh-cta" aria-labelledby="rh-cta-title">
    <div class="rh-cta-band rz-band rz-band--accent">
      <div class="rh-wrap rh-cta-inner">
        <p v-reveal class="rz-eyebrow">Hablemos</p>
        <h2 id="rh-cta-title" v-reveal="60" class="rh-cta-title">{{ title }}</h2>
        <p v-if="custom.cta_text" v-reveal="120" class="rh-cta-text">{{ custom.cta_text }}</p>
        <component
          :is="link?.to ? 'RouterLink' : 'a'" v-if="link" v-reveal="180"
          class="rz-btn rz-btn--ink rh-cta-btn"
          :to="link.to" :href="link.href"
          :target="link.external ? '_blank' : null" :rel="link.external ? 'noopener' : null"
        >
          {{ label }} <AppIcon name="arrow-right" :size="16" />
        </component>
      </div>
    </div>
  </section>
</template>
