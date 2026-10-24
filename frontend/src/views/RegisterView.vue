<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.store.js'
import { locationsApi } from '../api/locations.api.js'
import AuthLayout from '../components/AuthLayout.vue'
import AppInput from '../components/AppInput.vue'
import AppButton from '../components/AppButton.vue'
import AlertMessage from '../components/AlertMessage.vue'
import PasswordStrength from '../components/PasswordStrength.vue'
import {
  TAX_CONDITIONS, validateUsername, validateEmail, validatePassword,
  validateName, validateDocument, validateBusinessName, validatePhone,
  validateAddress, validateAcceptTerms, documentKindFor
} from '../validators/auth.validators.js'

const router = useRouter()
const auth = useAuthStore()

const step = ref(1)
const successMsg = ref('')
const provinces = ref([])
const cities = ref([])
const loadingGeo = ref(false)
const geoNotice = ref('')
const geoError = ref('')

const form = reactive({
  username: '', email: '', password: '', confirm_password: '',
  first_name: '', last_name: '', tax_condition: 'CF', business_name: '',
  document: '', province: '', city: '', address: '', phone: '',
  accept_terms: false
})
const touched = reactive({})

const docKind = computed(() => documentKindFor(form.tax_condition))
const docHint = computed(() =>
  docKind.value === 'DNI'
    ? 'DNI: 7 a 8 dígitos.'
    : 'CUIT/CUIL: 11 dígitos con prefijo válido (20, 23, 24, 27, 30, 33, 34) y dígito verificador.'
)

async function loadProvinces() {
  loadingGeo.value = true
  geoError.value = ''
  try {
    provinces.value = await locationsApi.getProvinces()
    geoNotice.value = locationsApi.usingFallback
      ? 'La API no respondió: usando catálogo local de emergencia. Revisá que Django esté corriendo.'
      : ''
  } catch (e) {
    provinces.value = []
    geoError.value = 'No se pudieron cargar las provincias. Verifica que Django corra en 127.0.0.1:8000.'
  } finally {
    loadingGeo.value = false
  }
}

let citiesRequest = 0
async function loadCities() {
  const myRequest = ++citiesRequest
  form.city = ''
  cities.value = []
  if (!form.province) return
  loadingGeo.value = true
  geoError.value = ''
  try {
    const rows = await locationsApi.getCities(form.province)
    if (myRequest !== citiesRequest) return // provincia cambió en el medio: descarto
    cities.value = rows
    if (!rows.length) geoError.value = 'No se encontraron ciudades para esta provincia.'
  } catch (e) {
    if (myRequest !== citiesRequest) return
    geoError.value = 'No se pudieron cargar las ciudades. Reintentá en unos segundos.'
  } finally {
    if (myRequest === citiesRequest) loadingGeo.value = false
  }
}

watch(() => form.province, loadCities)
watch(() => form.tax_condition, () => { touched.document = false })
onMounted(loadProvinces)

function err(name, validator) {
  if (!touched[name]) return ''
  return validator || auth.fieldErrors[name] || ''
}

function validateStep1() {
  const e = {}
  const u = validateUsername(form.username)
  const m = validateEmail(form.email)
  const p = validatePassword(form.password)
  if (u) e.username = u
  if (m) e.email = m
  if (p) e.password = p
  if (!form.confirm_password) e.confirm_password = 'Este campo es obligatorio'
  else if (form.password !== form.confirm_password) e.confirm_password = 'Las contraseñas no coinciden'
  return e
}

function validateStep2() {
  const e = {}
  const fn = validateName(form.first_name, 'Nombre')
  const ln = validateName(form.last_name, 'Apellido')
  const bn = validateBusinessName(form.business_name, form.tax_condition)
  const dc = validateDocument(form.document, form.tax_condition)
  if (fn) e.first_name = fn
  if (ln) e.last_name = ln
  if (bn) e.business_name = bn
  if (dc) e.document = dc
  return e
}

function validateStep3() {
  const e = {}
  if (!form.province) e.province = 'Seleccioná tu provincia'
  if (!form.city) e.city = 'Seleccioná tu ciudad'
  const ad = validateAddress(form.address)
  const ph = validatePhone(form.phone)
  const ty = validateAcceptTerms(form.accept_terms)
  if (ad) e.address = ad
  if (ph) e.phone = ph
  if (ty) e.accept_terms = ty
  return e
}

function markTouched(fields) {
  fields.forEach((f) => { touched[f] = true })
}

function next() {
  if (step.value === 1) {
    markTouched(['username', 'email', 'password', 'confirm_password'])
    if (Object.keys(validateStep1()).length) return
    step.value = 2
  } else if (step.value === 2) {
    markTouched(['first_name', 'last_name', 'business_name', 'document'])
    if (Object.keys(validateStep2()).length) return
    step.value = 3
  }
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function onSubmit() {
  markTouched(['province', 'city', 'address', 'phone', 'accept_terms'])
  if (Object.keys(validateStep1()).length || Object.keys(validateStep2()).length || Object.keys(validateStep3()).length) {
    step.value = 1
    return
  }
  const res = await auth.register(form)
  if (res.ok) {
    successMsg.value = res.message
    setTimeout(() => router.push({ name: 'login', query: { registered: '1' } }), 1400)
  }
}

const step1Errors = computed(() => validateStep1())
const step2Errors = computed(() => validateStep2())
const step3Errors = computed(() => validateStep3())
</script>
<template>
  <AuthLayout title="Creá tu cuenta" subtitle="Tres pasos: cuenta, datos fiscales y contacto. Validamos igual que el backend.">
    <div class="steps" aria-hidden="true">
      <div class="step" :class="{ done: step > 1, active: step === 1 }"></div>
      <div class="step" :class="{ done: step > 2, active: step === 2 }"></div>
      <div class="step" :class="{ active: step === 3 }"></div>
    </div>
    <div class="step-labels">
      <span :class="{ on: step === 1 }">1. Cuenta</span>
      <span :class="{ on: step === 2 }">2. Fiscal</span>
      <span :class="{ on: step === 3 }">3. Contacto</span>
    </div>

    <AlertMessage v-if="auth.lastError" kind="error" :message="auth.lastError" />
    <AlertMessage v-if="successMsg" kind="success" :message="`${successMsg} Redirigiendo al login…`" />
    <AlertMessage v-if="geoNotice" kind="warn" :message="geoNotice" />
    <AlertMessage v-if="geoError" kind="error" :message="geoError" />

    <form @submit.prevent="step === 3 ? onSubmit() : next()" novalidate>
      <div v-show="step === 1">
        <AppInput v-model="form.username" label="Nombre de usuario" name="username" placeholder="Ej. alfredo27" required :error="err('username', step1Errors.username)" @blur="touched.username = true" />
        <AppInput v-model="form.email" label="Correo electrónico" name="email" type="email" placeholder="Ej. alfredito2026@outlook.com" hint="Usá un correo real: te llega el link de verificación." required :error="err('email', step1Errors.email)" @blur="touched.email = true" />
        <AppInput v-model="form.password" label="Contraseña" name="password" type="password" placeholder="Ej. Asdf@123" hint="Mínimo 8: minúscula, mayúscula, número y especial." required :error="err('password', step1Errors.password)" @blur="touched.password = true" />
        <PasswordStrength :value="form.password" />
        <AppInput v-model="form.confirm_password" label="Confirmar contraseña" name="confirm_password" type="password" placeholder="Repetir contraseña" required :error="err('confirm_password', step1Errors.confirm_password)" @blur="touched.confirm_password = true" />
      </div>

      <div v-show="step === 2">
        <div class="grid-2">
          <AppInput v-model="form.first_name" label="Nombre" name="first_name" placeholder="Escribe tu nombre" required :error="err('first_name', step2Errors.first_name)" @blur="touched.first_name = true" />
          <AppInput v-model="form.last_name" label="Apellido/s" name="last_name" placeholder="Escribe tu/s apellido/s" required :error="err('last_name', step2Errors.last_name)" @blur="touched.last_name = true" />
        </div>
        <div class="field">
          <label for="tax_condition">Condición fiscal *</label>
          <select id="tax_condition" v-model="form.tax_condition" class="select">
            <option v-for="t in TAX_CONDITIONS" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
          <p class="hint">Tipo de documento automático: {{ docKind }} (CF → DNI, resto → CUIT).</p>
        </div>
        <AppInput v-model="form.business_name" label="Nombre de negocio" name="business_name" placeholder="Escribe tu nombre de negocio" :hint="form.tax_condition === 'CF' ? 'Opcional únicamente para consumidor final.' : 'Obligatorio para tu condición fiscal.'" :error="err('business_name', step2Errors.business_name)" @blur="touched.business_name = true" />
        <AppInput v-model="form.document" label="Documento" name="document" placeholder="Escribe tu número de identificación" :hint="docHint" required :error="err('document', step2Errors.document)" @blur="touched.document = true" />
      </div>

      <div v-show="step === 3">
        <div class="grid-2">
          <div class="field">
            <label for="province">Provincia *</label>
            <select id="province" v-model="form.province" class="select" :class="{ invalid: err('province', step3Errors.province) }">
              <option value="">Seleccionar…</option>
              <option v-for="p in provinces" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
            <p v-if="err('province', step3Errors.province)" class="field-error">{{ err('province', step3Errors.province) }}</p>
          </div>
          <div class="field">
            <label for="city">Ciudad *</label>
            <select id="city" v-model="form.city" class="select" :class="{ invalid: err('city', step3Errors.city) }" :disabled="!form.province">
              <option value="">{{ form.province ? 'Seleccionar…' : 'Primero elegí provincia' }}</option>
              <option v-for="c in cities" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
            <p v-if="err('city', step3Errors.city)" class="field-error">{{ err('city', step3Errors.city) }}</p>
          </div>
        </div>
        <AppInput v-model="form.address" label="Domicilio" name="address" placeholder="Escribe tu domicilio" :error="err('address', step3Errors.address)" @blur="touched.address = true" />
        <AppInput v-model="form.phone" label="Número de celular" name="phone" placeholder="+5493871551234" hint="Formato internacional. Ej. +5493871551234" required :error="err('phone', step3Errors.phone)" @blur="touched.phone = true" />
        <AlertMessage kind="info" message="Revisá que la ciudad pertenezca a la provincia: el backend lo exige." />
        <div class="field">
          <label class="check">
            <input
              v-model="form.accept_terms"
              type="checkbox"
              :aria-invalid="!!err('accept_terms', step3Errors.accept_terms)"
              @change="touched.accept_terms = true"
            />
            <span>
              Leí y acepto los <RouterLink to="/terminos" target="_blank">Términos y condiciones</RouterLink>,
              incluida la política de copyright y contenido prohibido. Declaro que el contenido que suba a mi
              catálogo es propio o cuenta con autorización.
            </span>
          </label>
          <p v-if="err('accept_terms', step3Errors.accept_terms)" class="field-error" role="alert">{{ err('accept_terms', step3Errors.accept_terms) }}</p>
        </div>
      </div>

      <div class="btn-row">
        <AppButton v-if="step > 1" variant="ghost" type="button" @click="step -= 1">Atrás</AppButton>
        <AppButton v-if="step < 3" type="submit">Continuar</AppButton>
        <AppButton v-else :loading="auth.status === 'loading'">Crear cuenta</AppButton>
      </div>
    </form>

    <div class="auth-links">
      <RouterLink to="/login">Ya tengo cuenta</RouterLink>
      <span v-if="loadingGeo">Cargando ubicaciones…</span>
    </div>
  </AuthLayout>
</template>

