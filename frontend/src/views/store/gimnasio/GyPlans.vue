<script setup>
// Membresías del club: tarjetas de precio con índice, lista de beneficios y
// CTA por WhatsApp/contacto. La tarjeta central se destaca con la placa lima
// (jerarquía visual, sin inventar “el más elegido”). Sin planes cargados el
// bloque se auto-oculta: nunca mostramos una grilla vacía.
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
  <section v-if="show" id="planes" class="gy-plans" aria-labelledby="gy-plans-title">
    <div class="gy-wrap">
      <header v-reveal class="gy-plans-head">
        <div class="gy-plans-head-copy">
          <p class="gy-eyebrow"><span class="gy-eyebrow-idx">{{ String(sectionIndex || 1).padStart(2, '0') }}</span> Planes</p>
          <h2 id="gy-plans-title">{{ title }}</h2>
        </div>
        <p class="gy-plans-lead">
          Compará las opciones y consultá la que mejor se adapte a tu objetivo.
        </p>
      </header>

      <ul class="gy-plans-grid">
        <li
          v-for="(plan, i) in items" :key="`${i}-${plan.name}`" v-reveal="(i % 3) * 80"
          class="gy-plan" :class="{ 'is-featured': i === featuredIndex }"
        >
          <span class="gy-plan-idx" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
          <div class="gy-plan-top">
            <h3 class="gy-plan-name">{{ plan.name }}</h3>
          </div>
          <p v-if="plan.price" class="gy-plan-price">{{ plan.price }}</p>
          <p v-if="plan.note" class="gy-plan-note">{{ plan.note }}</p>
          <ul v-if="feats(plan).length" class="gy-plan-feats">
            <li v-for="(f, fi) in feats(plan)" :key="fi">
              <AppIcon name="check" :size="15" :stroke="2.6" aria-hidden="true" />
              <span>{{ f }}</span>
            </li>
          </ul>
          <a v-if="canContact" class="gy-plan-cta" :href="planHref(plan)">
            Quiero este plan <AppIcon name="arrow-up-right" :size="16" aria-hidden="true" />
          </a>
        </li>
      </ul>
    </div>
  </section>
</template>
