<script setup>
// Pantalla 2 (abajo): la comparación no es mirar miniaturas. Una fila por
// decisión real de la composición y una columna por propuesta, con la tesis
// arriba para que se elija por lo que la web promete.
import { computed } from 'vue'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  proposals: { type: Array, default: () => [] },
  selectedId: { type: String, default: '' }
})
const emit = defineEmits(['choose'])

const rows = computed(() => {
  const list = props.proposals
  if (!list.length) return []
  const value = (proposal, key) => {
    const look = proposal.look || {}
    if (key === 'thesis') return proposal.thesis?.label || ''
    if (key === 'type') return look.fonts?.label || ''
    if (key === 'hero') return look.hero || ''
    if (key === 'grid') return look.grid || ''
    if (key === 'air') return look.density_label || ''
    if (key === 'sections') {
      const count = (look.structure?.landing || []).length
      return count ? `${count} secciones` : ''
    }
    return ''
  }
  const definitions = [
    { key: 'thesis', label: 'Promete' },
    { key: 'type', label: 'Tipografía' },
    { key: 'hero', label: 'Portada' },
    { key: 'grid', label: 'Grilla' },
    { key: 'air', label: 'Aire' },
    { key: 'sections', label: 'Portada con' }
  ]
  return definitions
    .map((def) => ({ ...def, values: list.map((proposal) => value(proposal, def.key)) }))
    //Una fila donde todas las propuestas dicen lo mismo no compara nada.
    .filter((row) => new Set(row.values.filter(Boolean)).size > 1)
})

const accents = computed(() => props.proposals.map((proposal) => proposal.theme_choice?.accent || proposal.look?.accent || ''))
</script>

<template>
  <section v-if="proposals.length > 1 && rows.length" class="aidx" aria-labelledby="aidx-title">
    <header class="aidx-head">
      <h3 id="aidx-title">Qué cambia</h3>
      <p>Las decisiones que hacen distinta cada propuesta.</p>
    </header>
    <div class="aidx-scroll">
      <table class="aidx-table">
        <thead>
          <tr>
            <th scope="col"><span class="sr-only">Decisión</span></th>
            <th v-for="proposal in proposals" :key="proposal.id" scope="col">
              <span class="aidx-col">
                <span class="aidx-dot" :style="{ background: accents[proposals.indexOf(proposal)] || 'var(--aid-accent)' }" aria-hidden="true"></span>
                {{ proposal.thesis?.label || proposal.label }}
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.key">
            <th scope="row">{{ row.label }}</th>
            <td v-for="(cell, index) in row.values" :key="index" :class="{ empty: !cell }">
              {{ cell || '—' }}
            </td>
          </tr>
          <tr class="aidx-actions-row">
            <th scope="row"><span class="sr-only">Elegir</span></th>
            <td v-for="proposal in proposals" :key="proposal.id">
              <button
                class="btn btn-auto"
                :class="{ 'aid-primary': proposal.id === selectedId }"
                type="button"
                @click="emit('choose', proposal.id)"
              >
                <AppIcon :name="proposal.id === selectedId ? 'circle-check' : 'check'" :size="15" />
                {{ proposal.id === selectedId ? 'Elegida' : 'Elegir' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
