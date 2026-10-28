<script setup>
import { ref, computed, watch } from 'vue'
import AppIcon from '../AppIcon.vue'
import DesignPreview from '../design/DesignPreview.vue'
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
  applied: { type: Boolean, default: false },
  autofillDefault: { type: Boolean, default: true }
})
const emit = defineEmits(['preview', 'apply', 'refresh-images'])

const autofill = ref(props.autofillDefault)
watch(() => props.autofillDefault, (v) => { autofill.value = v })

const requests = computed(() => (Array.isArray(props.proposal.image_requests) ? props.proposal.image_requests : []))
const draft = computed(() => props.proposal.copy_draft || {})
const applying = computed(() => props.busy === `apply:${props.proposal.id}`)
const notes = computed(() => (Array.isArray(props.proposal.notes) ? props.proposal.notes.slice(0, 3) : []))
</script>

<template>
  <article class="aidp" :class="{ applied }">
    <header class="aidp-head">
      <div>
        <h3>{{ proposal.label }}</h3>
        <p v-if="proposal.why">{{ proposal.why }}</p>
      </div>
      <span v-if="templateLabel" class="aidp-badge">{{ templateLabel }}</span>
    </header>

    <div class="aid-mini">
      <DesignPreview
        :form="form"
        :vars="vars"
        :template="template"
        :shop-name="shopName"
        :initial="initial"
        :logo="logo"
        :cover="cover"
        :advanced="advanced"
        :catalog-on="true"
        :show-map="showMap"
        :name-font="nameFont"
      />
    </div>

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

    <footer class="aidp-actions">
      <button class="btn ghost btn-auto" type="button" @click="emit('preview')">
        <AppIcon name="eye" :size="16" /> Ver en grande
      </button>
      <button class="btn btn-auto" type="button" :disabled="Boolean(busy)" @click="emit('apply', { proposal, autofill })">
        <AppIcon name="check" :size="16" /> {{ applying ? 'Aplicando…' : 'Aplicar al borrador' }}
      </button>
    </footer>
    <p v-if="applied" class="aidp-applied"><AppIcon name="check" :size="14" /> En el borrador</p>
  </article>
</template>
