<script setup>
// Bloque 'announcements': cinta de anuncios bajo la portada. Variante
// 'marquee' (default) = loop infinito con triple secuencia; variante
// 'static' = una sola secuencia fija, centrada, con wrap (respeta
// reduced-motion igual que el marquee pausado por media query).
import { computed, inject } from 'vue'
import { SERVICE_ICONS } from '../../../api/stores.api.js'
import AppIcon from '../../AppIcon.vue'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom } = ctx

const announcements = computed(() => (Array.isArray(custom.value.announcements) ? custom.value.announcements : []))
const show = computed(() => custom.value.show_announcements !== false && announcements.value.length > 0)
const annIcon = (key) => (SERVICE_ICONS[key] ? key : 'megaphone')
const isStatic = computed(() => props.block?.variant === 'static')
const items = computed(() => (isStatic.value ? announcements.value : [...announcements.value, ...announcements.value, ...announcements.value]))
</script>

<template>
  <div v-if="show" class="sp-ann" :class="{ 'is-static': isStatic }" role="note" aria-label="Anuncios de la tienda">
    <div class="sp-ann-track">
      <span v-for="(a, i) in items" :key="i" class="sp-ann-item" :aria-hidden="!isStatic && i >= announcements.length"><AppIcon :name="annIcon(a.icon)" :size="14" />{{ a.text }}</span>
    </div>
  </div>
</template>
