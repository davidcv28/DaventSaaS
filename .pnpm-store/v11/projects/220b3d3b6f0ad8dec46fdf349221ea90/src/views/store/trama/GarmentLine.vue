<script setup>
// Línea de prenda de TRAMA: trazo de 1,4 px en el color heredado que reemplaza
// la foto cuando la sección no tiene imagen real (hero sin portada, categoría
// sin foto). El tipo se deduce del NOMBRE real de la categoría (remera/tee,
// buzo/hoodie, pantalón/jean, gorra/cap) y cae a remera si no reconoce nada.
// Es decorativa: no anuncia nada al lector de pantalla (`aria-hidden`).
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, default: '' },
  kind: { type: String, default: '' }
})

const KINDS = [
  [/hoodie|buzo|sweater|sudadera|campera|abrigo|chaleco|jacket/i, 'hoodie'],
  [/pant|jean|jogger|short|bermuda|calza|pollera|falda/i, 'pants'],
  [/cap|gorra|sombrero|beanie|boina|bucket/i, 'cap'],
  // Accesorios genéricos: el mockup usa la gorra como ícono de esa categoría,
  // así que no cae a la remera por defecto.
  [/accesorio|bolso|mochila|riñonera|rinonera|cartera|cintur|bufanda|gorro/i, 'cap'],
  [/tee|remera|camiseta|musculosa|top|t-shirt/i, 'tee']
]

const kind = computed(() => props.kind || KINDS.find(([re]) => re.test(props.name || ''))?.[1] || 'tee')
</script>

<template>
  <svg
    class="tr-garment" viewBox="0 0 120 120" fill="none" stroke="currentColor"
    stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"
    aria-hidden="true" focusable="false"
  >
    <!-- Recreación del trazo, sin leyenda -->
    <template v-if="kind === 'hoodie'">
      <path d="M44 30 L30 37 L20 58 L34 66 L34 104 L86 104 L86 66 L100 58 L90 37 L76 30" />
      <path d="M44 30 C44 16 51 10 60 10 C69 10 76 16 76 30" />
      <path d="M44 30 C50 39 70 39 76 30" />
      <path d="M52 40 L52 56" />
      <path d="M68 40 L68 56" />
      <path d="M46 82 L74 82 L78 98 L42 98" />
    </template>

    <template v-else-if="kind === 'pants'">
      <path d="M34 22 L86 22 L92 58 L80 108 L62 108 L60 64 L58 108 L40 108 L28 58 Z" />
      <path d="M34 32 L86 32" />
      <path d="M60 32 L60 62" />
    </template>

    <template v-else-if="kind === 'cap'">
      <path d="M24 66 C24 40 40 26 60 26 C80 26 96 40 96 66" />
      <path d="M24 66 C40 78 80 78 96 66" />
      <path d="M24 66 L18 74 C40 90 82 88 102 74 L96 66" />
      <path d="M60 26 L60 32" />
      <path d="M46 32 C51 42 53 54 53 66" />
      <path d="M74 32 C69 42 67 54 67 66" />
    </template>

    <template v-else>
      <path d="M44 24 L30 31 L20 52 L34 60 L34 102 L86 102 L86 60 L100 52 L90 31 L76 24 Z" />
      <path d="M44 24 C50 30 70 30 76 24" />
      <path d="M40 60 L40 98" />
      <path d="M80 60 L80 98" />
    </template>
  </svg>
</template>
