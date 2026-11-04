<script setup>
// Membresías del estudio (la firma MovementLab): tarjetas de planes con
// índice, precio grande + nota de sesiones/periodicidad, lista de
// beneficios y CTA "Elegir" por WhatsApp/contacto. El plan destacado va
// con borde de acento. Sin planes cargados el bloque se auto-oculta.
import { computed, inject } from 'vue'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { storeContactLink, hasContactChannel } from '../../../api/stores.api.js'

const props = defineProps({
  block: { type: Object, default: null },
  sectionIndex: { type: Number, default: 0 }
})

const ctx = inject('storePage')
const { slug, custom, shopName, showContact } = ctx

const items = computed(() => (Array.isArray(custom.value.plans) ? custom.value.plans : [])
  .filter((p) => String(p?.name || '').trim()))
const show = computed(() => custom.value.show_plans !== false && items.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || custom.value.plans_title?.trim() || 'Membresías')
const waBase = computed(() => (hasContactChannel(custom.value, 'whatsapp') ? storeContactLink(slug.value, 'whatsapp') : ''))
const canContact = computed(() => Boolean(waBase.value) || showContact.value)
const planHref = (plan) => {
  if (waBase.value) {
    const text = `Hola ${shopName.value}, quiero información del plan ${plan.name}.`
    return `${waBase.value}?text=${encodeURIComponent(text)}`
  }
  return showContact.value ? '#contacto' : ''
}
const featuredIndex = computed(() => (items.value.length > 1 ? Math.min(1, items.value.length - 1) : -1))
const feats = (plan) => (Array.isArray(plan.items) ? plan.items : []).filter(Boolean).slice(0, 6)
</script>

<template>
  <section v-if="show" id="planes" class="mv-plans" aria-labelledby="mv-plans-title">
    <div class="mv-wrap">
      <header v-reveal class="mv-plans-head">
        <div class="mv-plans-head-copy">
          <p class="mv-eyebrow"><span class="mv-eyebrow-idx">{{ String(sectionIndex || 1).padStart(2, '0') }}</span> Membresías</p>
          <h2 id="mv-plans-title">{{ title }}</h2>
        </div>
        <p class="mv-plans-lead">Sesiones por semana, seguimiento del coach y precio por sesión. Consultá la que mejor se adapte a tu objetivo.</p>
      </header>

      <ul class="mv-plans-grid">
        <li
          v-for="(plan, i) in items" :key="`${i}-${plan.name}`" v-reveal="(i % 3) * 80"
          class="mv-plan" :class="{ 'is-featured': i === featuredIndex }"
        >
          <div class="mv-plan-top">
            <span class="mv-plan-idx" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
            <span v-if="i === featuredIndex" class="mv-plan-flag">Recomendado</span>
          </div>
          <h3 class="mv-plan-name">{{ plan.name }}</h3>
          <p v-if="plan.price" class="mv-plan-price">{{ plan.price }}</p>
          <p v-if="plan.note" class="mv-plan-note">{{ plan.note }}</p>
          <ul v-if="feats(plan).length" class="mv-plan-feats">
            <li v-for="(f, fi) in feats(plan)" :key="fi">
              <AppIcon name="check" :size="15" :stroke="2.6" aria-hidden="true" />
              <span>{{ f }}</span>
            </li>
          </ul>
          <a v-if="canContact" class="mv-plan-cta" :href="planHref(plan)">
            Elegir <AppIcon name="arrow-up-right" :size="16" aria-hidden="true" />
          </a>
        </li>
      </ul>
    </div>
  </section>
</template>
