<script setup>
// Pantalla 4: la web publicada, revisada y compartible. Lista de chequeo con
// lo que está bien y lo que falta (cada cosa con su botón) + la tarjeta de
// cómo se ve el link al compartirlo, armada con los datos REALES de la
// tienda (nombre, descripción, logo) en vez de la marca de DAVENT.
import { computed } from 'vue'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  checks: { type: Array, default: () => [] },
  name: { type: String, default: '' },
  description: { type: String, default: '' },
  logo: { type: String, default: '' },
  publicUrl: { type: String, default: '' },
  busy: { type: Boolean, default: false }
})
const emit = defineEmits(['navigate', 'revert', 'copy'])

const done = computed(() => props.checks.filter((item) => item.ok))
const pending = computed(() => props.checks.filter((item) => !item.ok))
const urlLabel = computed(() => String(props.publicUrl || '').replace(/^https?:\/\//, ''))
const summary = computed(() => {
  const total = props.checks.length
  if (!total) return ''
  return `${done.value.length} de ${total} en orden`
})
</script>

<template>
  <section class="aidq" aria-labelledby="aidq-title">
    <header class="aidq-head">
      <div>
        <h2 id="aidq-title"><AppIcon name="circle-check" :size="18" /> Tu web ya está publicada</h2>
        <p>Publicada hace un momento · visible para cualquiera.</p>
      </div>
      <a v-if="publicUrl" class="btn btn-auto" :href="publicUrl" target="_blank" rel="noopener">
        <AppIcon name="external-link" :size="16" /> Abrir
      </a>
    </header>

    <div class="aidq-grid">
      <div class="aidq-col">
        <div class="aidq-col-head">
          <h3>Lista de chequeo</h3>
          <span v-if="summary" class="aidq-count">{{ summary }}</span>
        </div>
        <ul class="aidq-list">
          <li v-for="item in done" :key="item.key" class="ok">
            <AppIcon name="circle-check" :size="15" aria-hidden="true" />
            <span class="aidq-item-text">{{ item.label }}</span>
            <button class="btn ghost btn-auto" type="button" @click="emit('navigate', item.action)">Ver</button>
          </li>
          <li v-for="item in pending" :key="item.key" class="todo">
            <AppIcon name="circle-alert" :size="15" aria-hidden="true" />
            <span class="aidq-item-text">
              {{ item.label }}
              <small v-if="item.hint">{{ item.hint }}</small>
            </span>
            <button class="btn btn-auto" type="button" @click="emit('navigate', item.action)">Arreglar</button>
          </li>
        </ul>
      </div>

      <div class="aidq-col">
        <div class="aidq-col-head">
          <h3>Cómo se ve el link</h3>
        </div>
        <div class="aidq-share">
          <div class="aidq-share-card">
            <span class="aidq-share-img">
              <img v-if="logo" :src="logo" alt="" loading="lazy" />
              <AppIcon v-else name="store" :size="20" aria-hidden="true" />
            </span>
            <span class="aidq-share-text">
              <strong>{{ name || 'Tu negocio' }}</strong>
              <small>{{ description || 'Todavía no cargaste una descripción: es lo que se lee al compartir la web.' }}</small>
              <em>{{ urlLabel || 'tu-tienda.davent.com.ar' }}</em>
            </span>
          </div>
          <p class="aidq-share-note">
            El nombre y la descripción salen de tu perfil: lo que se ve acá es lo que se comparte.
          </p>
        </div>
        <div class="aidq-actions">
          <button v-if="publicUrl" class="btn btn-auto" type="button" @click="emit('copy')">
            <AppIcon name="share-2" :size="16" /> Copiar link
          </button>
          <button class="btn ghost btn-auto" type="button" :disabled="busy" @click="emit('revert')">
            <AppIcon name="undo" :size="16" /> Volver a la versión anterior
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
