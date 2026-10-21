<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import LegalLayout from '../components/LegalLayout.vue'
import AppIcon from '../components/AppIcon.vue'
import AppInput from '../components/AppInput.vue'
import AppButton from '../components/AppButton.vue'
import AlertMessage from '../components/AlertMessage.vue'
import { useLegalStore } from '../stores/legal.store.js'
import { useAuthStore } from '../stores/auth.store.js'
import {
  REPORT_KINDS, needsOriginalWork,
  validateReporterName, validateReporterEmail, validateReportedUrl,
  validateOriginalWork, validateReportDescription, validateGoodFaith
} from '../validators/legal.validators.js'

const legal = useLegalStore()
const auth = useAuthStore()

const form = reactive({
  reporter_name: '',
  reporter_email: '',
  kind: 'COPYRIGHT',
  reported_url: '',
  original_work: '',
  description: '',
  good_faith: false
})
const touched = reactive({})
const done = ref(false)

onMounted(() => {
  // Si el denunciante tiene sesión, precompletamos sus datos de contacto.
  if (!auth.user) return
  form.reporter_email = auth.user.email || ''
  const name = [auth.user?.profile?.first_name, auth.user?.profile?.last_name]
    .filter(Boolean).join(' ')
  if (name) form.reporter_name = name
})

const requiresWork = computed(() => needsOriginalWork(form.kind))

const errors = computed(() => {
  const e = {}
  const rn = validateReporterName(form.reporter_name)
  const re = validateReporterEmail(form.reporter_email)
  const ru = validateReportedUrl(form.reported_url)
  const ow = validateOriginalWork(form.original_work, form.kind)
  const ds = validateReportDescription(form.description)
  const gf = validateGoodFaith(form.good_faith)
  if (rn) e.reporter_name = rn
  if (re) e.reporter_email = re
  if (ru) e.reported_url = ru
  if (ow) e.original_work = ow
  if (ds) e.description = ds
  if (gf) e.good_faith = gf
  return e
})

function err(name) {
  if (!touched[name]) return ''
  return errors.value[name] || legal.fieldErrors[name] || ''
}

async function onSubmit() {
  Object.keys(form).forEach((k) => { touched[k] = true })
  if (Object.keys(errors.value).length) return
  const res = await legal.sendReport(form)
  if (res.ok) done.value = true
}
</script>

<template>
  <LegalLayout
    title="Denunciar contenido"
    subtitle="Reportá contenido que infrinja derechos de autor, marcas o que sea ilegal. El formulario está disponible para cualquier persona, con o sin cuenta."
  >
    <div v-if="done" class="empty">
      <span class="empty-icon"><AppIcon name="circle-check" :size="30" /></span>
      <h3>Denuncia registrada</h3>
      <p>Recibimos tu reporte. Nuestro equipo lo revisará y, si corresponde, quitará el contenido y tomará medidas sobre la cuenta responsable. Podemos contactarte por correo si necesitamos más información.</p>
      <RouterLink class="btn btn-auto" to="/terminos">Ver términos y condiciones</RouterLink>
    </div>

    <form v-else class="card" @submit.prevent="onSubmit" novalidate>
      <AlertMessage v-if="legal.lastError" kind="error" :message="legal.lastError" />
      <AlertMessage kind="info" message="Las denuncias falsas o abusivas pueden derivar en medidas sobre la cuenta denunciante. Completá los datos con precisión." />

      <div class="grid-2">
        <AppInput
          v-model="form.reporter_name"
          label="Nombre y apellido"
          name="reporter_name"
          placeholder="Escribe tu nombre completo"
          autocomplete="name"
          required
          :error="err('reporter_name')"
          @blur="touched.reporter_name = true"
        />
        <AppInput
          v-model="form.reporter_email"
          label="Correo electrónico"
          name="reporter_email"
          type="email"
          placeholder="Ej. denunciante@correo.com"
          hint="Te contactamos por este medio si necesitamos más información."
          autocomplete="email"
          required
          :error="err('reporter_email')"
          @blur="touched.reporter_email = true"
        />
      </div>

      <div class="field">
        <label for="kind">Tipo de denuncia <span aria-hidden="true">*</span></label>
        <select id="kind" v-model="form.kind" class="select">
          <option v-for="k in REPORT_KINDS" :key="k.value" :value="k.value">{{ k.label }}</option>
        </select>
      </div>

      <AppInput
        v-model="form.reported_url"
        label="URL del contenido denunciado"
        name="reported_url"
        type="url"
        placeholder="https://..."
        hint="Enlace a la página dentro de DAVENT donde aparece el contenido."
        required
        :error="err('reported_url')"
        @blur="touched.reported_url = true"
      />

      <AppInput
        v-if="requiresWork"
        v-model="form.original_work"
        label="Obra o derecho original"
        name="original_work"
        placeholder="Ej. Fotografías propias del catálogo de mi marca"
        hint="Identificá la obra, imagen, texto o marca afectada."
        required
        :error="err('original_work')"
        @blur="touched.original_work = true"
      />

      <div class="field">
        <label for="description">Descripción de la denuncia <span aria-hidden="true">*</span></label>
        <textarea
          id="description"
          v-model="form.description"
          class="textarea"
          :class="{ invalid: err('description') }"
          placeholder="Contanos qué contenido infringe tus derechos o las reglas de la plataforma"
          :aria-invalid="!!err('description')"
          @blur="touched.description = true"
        ></textarea>
        <p v-if="err('description')" class="field-error" role="alert">{{ err('description') }}</p>
      </div>

      <div class="field">
        <label class="check">
          <input v-model="form.good_faith" type="checkbox" @change="touched.good_faith = true" />
          <span>Declaro de buena fe que la información de esta denuncia es veraz y que soy el titular del derecho o estoy autorizado a actuar en su nombre.</span>
        </label>
        <p v-if="err('good_faith')" class="field-error" role="alert">{{ err('good_faith') }}</p>
      </div>

      <AppButton :loading="legal.status === 'loading'">Enviar denuncia</AppButton>
    </form>
  </LegalLayout>
</template>
