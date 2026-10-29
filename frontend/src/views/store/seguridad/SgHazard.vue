<script setup>
// Cinta hazard amarilla/negra: firma visual del diseño seguridad.
// Se usa como separador entre bandas (hero → franja de checks, pie) y la
// repite también el CSS del chrome. Decorativa: no lleva texto ni foco.
defineProps({
  tall: { type: Boolean, default: false }
})
</script>

<template>
  <div class="sg-hazard" :class="{ 'is-tall': tall }" role="presentation" aria-hidden="true"></div>
</template>
