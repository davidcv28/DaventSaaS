<script setup>
import { computed } from 'vue'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  draft: { type: Object, default: () => ({}) },
  modelValue: { type: Boolean, default: true }
})
const emit = defineEmits(['update:modelValue'])

const about = computed(() => props.draft.about_text || '')
const mission = computed(() => props.draft.about_mission || '')
const faqs = computed(() => (Array.isArray(props.draft.faqs) ? props.draft.faqs : []))
const services = computed(() => (Array.isArray(props.draft.services) ? props.draft.services : []))
const steps = computed(() => (Array.isArray(props.draft.steps) ? props.draft.steps : []))
const announcements = computed(() => (Array.isArray(props.draft.announcements) ? props.draft.announcements : []))
const hasAny = computed(() => Boolean(about.value || mission.value || faqs.value.length || services.value.length || steps.value.length || announcements.value.length))
</script>

<template>
  <div v-if="hasAny" class="aidc">
    <div class="aidc-head">
      <div>
        <strong><AppIcon name="sparkles" :size="15" /> Textos sugeridos</strong>
        <p>Sugerido por DAVENT — revisalo antes de publicar.</p>
      </div>
      <label class="aidc-toggle">
        <input type="checkbox" :checked="modelValue" @change="emit('update:modelValue', $event.target.checked)" />
        <span>Usar los textos sugeridos</span>
      </label>
    </div>

    <div class="aidc-body">
      <div v-if="about" class="aidc-block">
        <h4>Sobre tu negocio</h4>
        <p>{{ about }}</p>
      </div>
      <div v-if="mission" class="aidc-block">
        <h4>Tu misión</h4>
        <p>{{ mission }}</p>
      </div>
      <div v-if="services.length" class="aidc-block">
        <h4>Servicios</h4>
        <ul>
          <li v-for="(s, i) in services" :key="i"><strong>{{ s.name }}</strong><span v-if="s.desc"> — {{ s.desc }}</span></li>
        </ul>
      </div>
      <div v-if="steps.length" class="aidc-block">
        <h4>Cómo trabajás</h4>
        <ol>
          <li v-for="(s, i) in steps" :key="i"><strong>{{ s.title }}</strong><span v-if="s.desc"> — {{ s.desc }}</span></li>
        </ol>
      </div>
      <div v-if="faqs.length" class="aidc-block">
        <h4>Preguntas frecuentes</h4>
        <dl>
          <template v-for="(f, i) in faqs" :key="i">
            <dt>{{ f.q }}</dt>
            <dd>{{ f.a }}</dd>
          </template>
        </dl>
      </div>
      <div v-if="announcements.length" class="aidc-block">
        <h4>Anuncios</h4>
        <ul>
          <li v-for="(a, i) in announcements" :key="i">{{ a.text }}</li>
        </ul>
      </div>
    </div>
    <p class="aidc-foot">Después de aplicarlos podés editarlos a mano en “Cómo se ve”.</p>
  </div>
</template>
