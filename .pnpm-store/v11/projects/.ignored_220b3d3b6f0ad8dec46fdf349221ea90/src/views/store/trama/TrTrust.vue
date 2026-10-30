<script setup>
// Franja "trust" de TRAMA: los 4 primeros beneficios/garantías que el dueño
// carga en Mi empresa (envíos, cambios, pagos, atención), con su ícono real
// del catálogo de servicios. Se oculta sin ítems o si el dueño apagó
// show_benefits. No usa copy fijo: cada texto es del negocio.
import { computed, inject } from 'vue'
import { SERVICE_ICONS } from '../../../api/stores.api.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom } = ctx

const items = computed(() => (Array.isArray(custom.value.benefits) ? custom.value.benefits : []).slice(0, 4))
const show = computed(() => custom.value.show_benefits !== false && items.value.length > 0)
const icon = (key) => (SERVICE_ICONS[key] ? key : 'shield-check')
</script>

<template>
  <section v-if="show" class="tr-trust" aria-label="Beneficios y garantías">
    <div class="tr-container">
      <div class="tr-trust-grid">
        <div v-for="(b, i) in items" :key="i" v-reveal="(i % 4) * 70" class="tr-trust-item">
          <span class="tr-trust-icon" aria-hidden="true"><AppIcon :name="icon(b.icon)" :size="22" /></span>
          <div class="tr-trust-copy">
            <strong>{{ b.title }}</strong>
            <span v-if="b.text" class="tr-trust-text">{{ b.text }}</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
