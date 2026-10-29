<script setup>
// Beneficios / garantías (§6.5-9): banda A SANGRE de tinta que rompe el
// contenedor, numerales grandes y columnas con regla vertical de acento.
// Datos reales de "Garantías y beneficios" ({icon,title,text}).
import { computed } from 'vue'
import { SERVICE_ICONS } from '../../../../api/stores.api.js'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useRhLinks } from './rhLinks.js'

const props = defineProps({ block: { type: Object, default: null } })

const { ctx } = useRhLinks()
const { custom } = ctx

const items = computed(() => (Array.isArray(custom.value.benefits) ? custom.value.benefits : []))
const show = computed(() => custom.value.show_benefits !== false && items.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || 'Garantías y beneficios')
const icon = (key) => (SERVICE_ICONS[key] ? key : 'shield-check')
const pad = (n) => String(n).padStart(2, '0')
</script>

<template>
  <section v-if="show" class="rz-section rh-numbered rz-band rh-benefits" aria-labelledby="rh-benefits-title">
    <div class="rh-wrap">
      <header class="rh-head">
        <div class="rh-head-main">
          <p v-reveal class="rz-eyebrow">
            <span class="rz-eyebrow-num rh-secnum" aria-hidden="true"></span>
            Beneficios
          </p>
          <h2 id="rh-benefits-title" v-reveal class="rh-title">{{ title }}</h2>
        </div>
      </header>

      <div class="rh-benefits-grid">
        <div v-for="(b, i) in items" :key="i" v-reveal="60 * i" class="rh-benefit">
          <span class="rh-benefit-top">
            <span class="rh-benefit-num" aria-hidden="true">{{ pad(i + 1) }}</span>
            <span class="rh-benefit-icon" aria-hidden="true"><AppIcon :name="icon(b.icon)" :size="20" /></span>
          </span>
          <strong class="rh-benefit-title">{{ b.title }}</strong>
          <span v-if="b.text" class="rh-benefit-text">{{ b.text }}</span>
        </div>
      </div>
    </div>
  </section>
</template>
