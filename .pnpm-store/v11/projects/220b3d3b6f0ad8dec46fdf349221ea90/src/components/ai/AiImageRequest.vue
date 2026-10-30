<script setup>
import { ref, computed } from 'vue'
import AppIcon from '../AppIcon.vue'
import { http } from '../../api/http.js'

const props = defineProps({
  request: { type: Object, required: true }
})
const emit = defineEmits(['uploaded', 'refresh'])

const input = ref(null)
const images = ref([])
const uploading = ref(0)
const error = ref('')
const dragOver = ref(false)

const minCount = computed(() => Number(props.request.min_count) || 1)
const count = computed(() => images.value.length)
const done = computed(() => count.value >= minCount.value)
const pct = computed(() => Math.min(100, Math.round((count.value / minCount.value) * 100)))

function pick() {
  if (uploading.value) return
  input.value?.click()
}

function onDrop(e) {
  dragOver.value = false
  uploadFiles(e.dataTransfer?.files)
}

function onPick(e) {
  uploadFiles(e.target.files)
  if (input.value) input.value.value = ''
}

// TODO(A): mover a stores.api.js (aiDesignImage) cuando el contrato v2 quede
// cerrado en ese archivo. Hoy el endpoint es nuevo y stores.api.js tiene dueño.
async function uploadFiles(files) {
  const list = Array.from(files || []).filter((f) => f.type?.startsWith('image/'))
  if (!list.length) return
  error.value = ''
  for (const file of list) {
    uploading.value++
    try {
      const form = new FormData()
      form.append('image', file)
      form.append('request_id', props.request.id)
      const { data } = await http.post('/stores/ai-design/image/', form, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      if (data?.image) images.value.push(data.image)
      emit('uploaded', { request_id: props.request.id, image: data?.image, storage: data?.storage, gallery: data?.gallery })
    } catch (e) {
      const d = e?.response?.data
      error.value = d?.detail || d?.Exito || 'No pudimos subir esa foto. Probá con otra.'
    } finally {
      uploading.value--
    }
  }
}
</script>

<template>
  <div class="aiir">
    <div class="aiir-head">
      <div class="aiir-title">
        <AppIcon name="images" :size="18" />
        <strong>{{ request.label || 'Fotos para tu web' }}</strong>
      </div>
      <span class="aiir-count" :class="{ done }">{{ count }} de {{ minCount }}</span>
    </div>
    <p v-if="request.hint" class="aiir-hint">{{ request.hint }}</p>

    <div
      class="aiir-drop"
      :class="{ over: dragOver, full: done }"
      role="button"
      tabindex="0"
      :aria-label="`Subir fotos: ${request.label || 'fotos'}`"
      @click="pick"
      @keydown.enter.prevent="pick"
      @keydown.space.prevent="pick"
      @dragover.prevent="dragOver = true"
      @dragleave.prevent="dragOver = false"
      @drop.prevent="onDrop"
    >
      <AppIcon name="upload" :size="20" />
      <span>{{ uploading ? 'Subiendo…' : 'Arrastrá tus fotos acá o hacé clic para elegirlas' }}</span>
      <small>JPG, PNG o WebP</small>
      <input ref="input" type="file" accept="image/*" multiple hidden @change="onPick" />
    </div>

    <div class="aiir-progress" role="progressbar" :aria-valuenow="pct" aria-valuemin="0" aria-valuemax="100" :aria-label="`Fotos subidas: ${count} de ${minCount}`">
      <span :style="{ width: pct + '%' }"></span>
    </div>

    <div v-if="images.length" class="aiir-grid">
      <img v-for="(img, i) in images" :key="img.id || i" :src="img.url" alt="Foto subida" loading="lazy" />
    </div>

    <p v-if="error" class="aiir-error" role="alert">{{ error }}</p>

    <button v-if="done" class="btn btn-auto aiir-redo" type="button" @click="emit('refresh')">
      <AppIcon name="sparkles" :size="16" /> Rehacer con estas fotos
    </button>
  </div>
</template>
