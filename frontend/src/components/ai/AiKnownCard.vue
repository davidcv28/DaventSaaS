<script setup>
// Pantalla 1 del flujo nuevo: "esto ya lo sabemos de vos". El motor deduce
// nombre, ciudad, rubro, objetivos y conteos reales (prefill); la entrevista
// deja de preguntar lo que ya está en el perfil y solo pide lo que cambia el
// diseño. "Corregir" abre el rubro por si la deducción falló.
import { computed, ref } from 'vue'
import AppIcon from '../AppIcon.vue'
import AiSelect from './AiSelect.vue'

const props = defineProps({
  prefill: { type: Object, default: () => ({}) },
  rubroOptions: { type: Array, default: () => [] }
})
const rubro = defineModel({ type: String, default: '' })

const editing = ref(false)
const counts = computed(() => props.prefill?.counts || {})
const chips = computed(() => {
  const list = []
  const name = String(props.prefill?.name || '').trim()
  if (name) list.push({ key: 'name', label: name, icon: 'store' })
  const place = [props.prefill?.city, props.prefill?.province].filter(Boolean).join(', ')
  if (place) list.push({ key: 'city', label: place, icon: 'map-pin' })
  if (counts.value.products) list.push({ key: 'products', label: `${counts.value.products} productos`, icon: 'package' })
  if (counts.value.photos) list.push({ key: 'photos', label: `${counts.value.photos} fotos`, icon: 'image' })
  if (counts.value.categories) list.push({ key: 'categories', label: `${counts.value.categories} categorías`, icon: 'tag' })
  return list
})
</script>

<template>
  <article class="aidk">
    <header class="aidk-head">
      <div class="aidk-text">
        <h3>Esto ya lo sabemos de vos</h3>
        <p>No te lo preguntamos. Solo lo que cambia el diseño.</p>
      </div>
      <button class="btn ghost btn-auto" type="button" :aria-expanded="editing" @click="editing = !editing">
        <AppIcon :name="editing ? 'check' : 'pencil'" :size="15" />
        {{ editing ? 'Listo' : 'Corregir' }}
      </button>
    </header>

    <div v-if="chips.length" class="aidk-chips">
      <span v-for="chip in chips" :key="chip.key" class="aidk-chip">
        <AppIcon :name="chip.icon" :size="13" aria-hidden="true" />
        {{ chip.label }}
      </span>
    </div>

    <div v-if="editing" class="aidk-edit">
      <AiSelect v-model="rubro" :options="rubroOptions" label="Rubro" placeholder="Elegí tu rubro" />
    </div>
  </article>
</template>
