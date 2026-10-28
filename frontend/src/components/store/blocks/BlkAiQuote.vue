<script setup>
// Bloque 'aiquote' (solo IA): frase destacada del negocio con autor
// opcional. Sin texto no monta nada — nunca una sección vacía.
// Variantes: centered (por defecto) | split (línea de acento al costado).
import { computed } from 'vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const src = computed(() => (props.block?.props && typeof props.block.props === 'object' ? props.block.props : {}))
const text = computed(() => String(src.value.text || '').trim().slice(0, 160))
const author = computed(() => String(src.value.author || '').trim().slice(0, 40))
const variant = computed(() => (props.block?.variant === 'split' ? 'split' : 'centered'))
</script>

<template>
  <section v-if="text" class="sp-aiquote" :class="`is-${variant}`" :data-blk-variant="variant !== 'centered' ? variant : null">
    <div class="sp-container sp-aiquote-inner">
      <blockquote v-reveal class="sp-aiquote-body">
        <p class="sp-aiquote-text">{{ text }}</p>
        <footer v-if="author" class="sp-aiquote-author">{{ author }}</footer>
      </blockquote>
    </div>
  </section>
</template>
