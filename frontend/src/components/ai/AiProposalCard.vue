<script setup>
import { ref, computed, watch } from 'vue'
import AppIcon from '../AppIcon.vue'
import AiLiveThumb from './AiLiveThumb.vue'
import AiImageRequest from './AiImageRequest.vue'
import AiDraftCopy from './AiDraftCopy.vue'

const props = defineProps({
  proposal: { type: Object, required: true },
  form: { type: Object, default: () => ({}) },
  vars: { type: Object, default: () => ({}) },
  template: { type: String, default: 'classic' },
  templateLabel: { type: String, default: '' },
  shopName: { type: String, default: '' },
  initial: { type: String, default: 'T' },
  logo: { type: String, default: '' },
  cover: { type: String, default: '' },
  advanced: { type: Boolean, default: false },
  showMap: { type: Boolean, default: false },
  nameFont: { type: Object, default: () => ({}) },
  busy: { type: String, default: '' },
  published: { type: Boolean, default: false },
  publicUrl: { type: String, default: '' },
  autofillDefault: { type: Boolean, default: true }
})
const emit = defineEmits(['preview', 'apply', 'change-style', 'refresh-images'])

const autofill = ref(props.autofillDefault)
watch(() => props.autofillDefault, (v) => { autofill.value = v })

const requests = computed(() => (Array.isArray(props.proposal.image_requests) ? props.proposal.image_requests : []))
const draft = computed(() => props.proposal.copy_draft || {})
const applying = computed(() => props.busy === `apply:${props.proposal.id}`)
const notes = computed(() => (Array.isArray(props.proposal.notes) ? props.proposal.notes.slice(0, 3) : []))
const themeChoice = computed(() => props.proposal.theme_choice || null)
const nightMode = computed(() => props.proposal.night_mode || null)
const coverChoice = computed(() => props.proposal.cover || null)
const themeSource = computed(() => (themeChoice.value?.source === 'user' ? 'elegido por vos' : 'elegido por la IA'))
const nightText = computed(() => {
  if (!nightMode.value?.enabled) return ''
  return nightMode.value.default === 'dark'
    ? 'Con modo noche, arranca en oscuro'
    : 'Con modo noche, arranca en claro'
})
</script>

<template>
  <article class="aidp" :class="{ applied: published }">
    <header class="aidp-head">
      <div>
        <h3>{{ proposal.label }}</h3>
        <p v-if="proposal.why">{{ proposal.why }}</p>
      </div>
      <span v-if="published" class="aidp-badge published">
        <AppIcon name="circle-check" :size="12" /> Publicada
      </span>
      <span v-else-if="templateLabel" class="aidp-badge">{{ templateLabel }}</span>
    </header>

    <div class="aidp-media">
      <div class="aid-mini">
        <AiLiveThumb
          :proposal="proposal"
          :form="form"
          :vars="vars"
          :template="template"
          :shop-name="shopName"
          :initial="initial"
          :logo="logo"
          :cover="cover"
          :advanced="advanced"
          :show-map="showMap"
          :name-font="nameFont"
          :public-url="publicUrl"
        />
      </div>
      <button
        type="button"
        class="aidp-media-btn"
        :aria-label="`Ver en grande: ${proposal.label}`"
        @click="emit('preview')"
      >
        <span class="aidp-media-hint"><AppIcon name="eye" :size="14" /> Ver en grande</span>
      </button>
    </div>

    <div v-if="themeChoice || nightText" class="aidp-chips">
      <span v-if="themeChoice" class="aidp-chip">
        <span class="aidp-dot" :style="{ background: themeChoice.accent || 'var(--aid-accent)' }" aria-hidden="true"></span>
        Color {{ themeSource }}
      </span>
      <span v-if="nightText" class="aidp-chip">
        <AppIcon name="moon" :size="13" aria-hidden="true" /> {{ nightText }}
      </span>
    </div>

    <p v-if="coverChoice?.reason" class="aidp-reason">
      <AppIcon name="image" :size="13" aria-hidden="true" /> {{ coverChoice.reason }}
    </p>

    <ul v-if="notes.length" class="aidp-notes">
      <li v-for="(n, k) in notes" :key="k">{{ n }}</li>
    </ul>

    <AiImageRequest
      v-for="req in requests"
      :key="req.id"
      :request="req"
      @refresh="emit('refresh-images')"
    />

    <AiDraftCopy v-model="autofill" :draft="draft" />

    <div v-if="published" class="aidp-published" role="status">
      <span class="aidp-published-title">
        <AppIcon name="circle-check" :size="16" /> Tu web ya está publicada
      </span>
      <div class="aidp-published-actions">
        <a v-if="publicUrl" class="btn btn-auto" :href="publicUrl" target="_blank" rel="noopener">
          <AppIcon name="external-link" :size="16" /> Ver mi página
        </a>
        <button class="btn ghost btn-auto" type="button" @click="emit('change-style')">
          <AppIcon name="refresh" :size="16" /> Cambiar el estilo
        </button>
      </div>
    </div>

    <footer v-else class="aidp-actions">
      <button class="btn ghost btn-auto" type="button" @click="emit('preview')">
        <AppIcon name="eye" :size="16" /> Ver en grande
      </button>
      <button class="btn btn-auto aid-primary" type="button" :disabled="Boolean(busy)" @click="emit('apply', { proposal, autofill })">
        <AppIcon name="check" :size="16" /> {{ applying ? 'Publicando…' : 'Establecer este estilo' }}
      </button>
    </footer>
  </article>
</template>
