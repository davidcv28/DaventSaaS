<script setup>
// Ayuda del Studio (tecla "?"): atajos de teclado + gestos del lienzo.
import { onMounted, ref } from 'vue'
import AppIcon from '../AppIcon.vue'

const emit = defineEmits(['close'])
const closeBtn = ref(null)
onMounted(() => closeBtn.value?.focus())

const GROUPS = [
  {
    title: 'Editar',
    rows: [
      ['Ctrl Z', 'Deshacer el último cambio'],
      ['Ctrl Shift Z', 'Rehacer'],
      ['Ctrl S', 'Guardar el borrador']
    ]
  },
  {
    title: 'Moverte',
    rows: [
      ['Ctrl K', 'Buscar un ajuste'],
      ['?', 'Abrir o cerrar esta ayuda'],
      ['Esc', 'Cerrar paneles o salir de pantalla completa']
    ]
  }
]
</script>

<template>
  <div class="stx-overlay" role="presentation" @click.self="emit('close')">
    <div class="stx-card stx-help" role="dialog" aria-modal="true" aria-labelledby="stx-help-t">
      <header class="stx-head">
        <h3 id="stx-help-t"><AppIcon name="circle-help" :size="17" /> Atajos y gestos</h3>
        <button ref="closeBtn" type="button" class="stx-x" aria-label="Cerrar la ayuda" @click="emit('close')"><AppIcon name="x" :size="16" /></button>
      </header>
      <div class="stx-body">
        <section v-for="g in GROUPS" :key="g.title" class="stx-group">
          <h4>{{ g.title }}</h4>
          <ul>
            <li v-for="[keys, desc] in g.rows" :key="keys">
              <span class="stx-keys"><kbd v-for="k in keys.split(' ')" :key="k">{{ k }}</kbd></span>
              <span>{{ desc }}</span>
            </li>
          </ul>
        </section>
        <section class="stx-group">
          <h4>En la vista previa</h4>
          <ul>
            <li><span class="stx-keys"><AppIcon name="pipette" :size="14" /></span><span>Clickeá un elemento para abrir su herramienta</span></li>
            <li><span class="stx-keys"><AppIcon name="eye" :size="14" /></span><span>Mantené “Comparar” para ver la versión guardada</span></li>
          </ul>
        </section>
      </div>
    </div>
  </div>
</template>
