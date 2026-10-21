<script setup>
import { ref, computed } from 'vue'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  label: { type: String, required: true },
  name: { type: String, required: true },
  type: { type: String, default: 'text' },
  placeholder: { type: String, default: '' },
  hint: { type: String, default: '' },
  error: { type: String, default: '' },
  autocomplete: { type: String, default: '' },
  required: { type: Boolean, default: false },
  maxlength: { type: [Number, String], default: undefined }
})

const emit = defineEmits(['update:modelValue', 'blur'])
const showPassword = ref(false)
const isPassword = computed(() => props.type === 'password')
const inputType = computed(() => (isPassword.value && showPassword.value ? 'text' : props.type))
const describedBy = computed(() => `${props.name}-hint ${props.name}-error`)
</script>

<template>
  <div class="field">
    <label :for="name">{{ label }} <span v-if="required" aria-hidden="true">*</span></label>
    <div class="input-wrap">
      <input
        :id="name"
        :name="name"
        :type="inputType"
        class="input"
        :class="{ invalid: !!error }"
        :value="modelValue"
        :placeholder="placeholder"
        :autocomplete="autocomplete"
        :required="required"
        :maxlength="maxlength"
        :aria-invalid="!!error"
        :aria-describedby="describedBy"
        @input="emit('update:modelValue', $event.target.value)"
        @blur="emit('blur')"
      />
      <button
        v-if="isPassword"
        type="button"
        class="password-toggle"
        @click="showPassword = !showPassword"
        :aria-label="showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'"
      >
        <AppIcon :name="showPassword ? 'eye-off' : 'eye'" :size="18" />
      </button>
    </div>
    <p v-if="hint" :id="`${name}-hint`" class="hint">{{ hint }}</p>
    <p v-if="error" :id="`${name}-error`" class="field-error" role="alert">{{ error }}</p>
  </div>
</template>
