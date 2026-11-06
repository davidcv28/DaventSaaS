<script setup>
// App nativa — Negocio: datos que ve el cliente en la web (customization:
// nombre comercial, titular, descripción, contacto y redes) + logo y foto
// de portada + datos fiscales/de facturación del perfil. Mismo pipeline
// de imágenes que el panel web (el backend normaliza a WebP).
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useAuthStore } from '../../stores/auth.store.js'
import { useStoreStore } from '../../stores/store.store.js'
import { locationsApi } from '../../api/locations.api.js'
import {
  validateDisplayName, validateHeadline, validateDescription,
  validateContactEmail, validateWhatsapp, validateInstagram,
  validateTiktok, validateFacebook, validateLogoFile, validateImageFile
} from '../../api/stores.api.js'
import {
  validateBusinessName, validatePhone, validateAddress
} from '../../validators/auth.validators.js'
import AppIcon from '../../components/AppIcon.vue'
import AppButton from '../../components/AppButton.vue'

const auth = useAuthStore()
const stores = useStoreStore()

// ----- Datos de la web pública (customization) -----
const web = reactive({
  display_name: '', headline: '', description: '', contact_email: '',
  whatsapp: '', instagram: '', tiktok: '', facebook: ''
})
const webTouched = reactive({})
const webBusy = ref(false)
const webSaved = ref(false)

function fillWeb() {
  const c = stores.customization
  Object.assign(web, {
    display_name: c.display_name || '',
    headline: c.headline || '',
    description: c.description || '',
    contact_email: c.contact_email || '',
    whatsapp: c.whatsapp || '',
    instagram: c.instagram || '',
    tiktok: c.tiktok || '',
    facebook: c.facebook || ''
  })
}
onMounted(async () => {
  if (stores.status === 'idle') await stores.loadMine()
  fillWeb()
  fillProfile()
  loadProvinces()
})
watch(() => stores.store, () => fillWeb())

const webErrs = computed(() => {
  const e = {}
  const dn = validateDisplayName(web.display_name.trim())
  const h = validateHeadline(web.headline.trim())
  const d = validateDescription(web.description.trim())
  const ce = validateContactEmail(web.contact_email)
  const w = validateWhatsapp(web.whatsapp)
  const ig = validateInstagram(web.instagram)
  const tt = validateTiktok(web.tiktok)
  const fb = validateFacebook(web.facebook)
  if (dn) e.display_name = dn
  if (h) e.headline = h
  if (d) e.description = d
  if (ce) e.contact_email = ce
  if (w) e.whatsapp = w
  if (ig) e.instagram = ig
  if (tt) e.tiktok = tt
  if (fb) e.facebook = fb
  return e
})
const webErr = (k) => (webTouched[k] ? webErrs.value[k] || stores.fieldErrors[k] || '' : '')

async function saveWeb() {
  Object.keys(web).forEach((k) => { webTouched[k] = true })
  webSaved.value = false
  if (Object.keys(webErrs.value).length) return
  webBusy.value = true
  const ok = await stores.saveCustomization({
    display_name: web.display_name.trim(),
    headline: web.headline.trim(),
    description: web.description.trim(),
    contact_email: web.contact_email.trim(),
    whatsapp: web.whatsapp.trim(),
    instagram: web.instagram.trim(),
    tiktok: web.tiktok.trim(),
    facebook: web.facebook.trim()
  })
  webBusy.value = false
  if (ok) webSaved.value = true
}

// ----- Logo y portada -----
const logoBusy = ref(false)
const coverBusy = ref(false)
const imgErr = ref('')
const logoEl = ref(null)
const coverEl = ref(null)

async function pickLogo(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  const err = validateLogoFile(file)
  if (err) { imgErr.value = err; return }
  imgErr.value = ''
  logoBusy.value = true
  await stores.uploadLogo(file)
  logoBusy.value = false
}
async function pickCover(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  const err = validateImageFile(file)
  if (err) { imgErr.value = err; return }
  imgErr.value = ''
  coverBusy.value = true
  await stores.uploadCover(file)
  coverBusy.value = false
}

// ----- Datos fiscales (perfil de la cuenta) -----
const prof = reactive({ business_name: '', address: '', phone: '', province: '', city: '' })
const profTouched = reactive({})
const profBusy = ref(false)
const profSaved = ref(false)
const provinces = ref([])
const cities = ref([])

function fillProfile() {
  const p = auth.user?.profile || {}
  Object.assign(prof, {
    business_name: p.business_name || '',
    address: p.address || '',
    phone: p.phone || '',
    province: p.province || '',
    city: p.city || ''
  })
  loadCities()
}
async function loadProvinces() {
  try { provinces.value = await locationsApi.getProvinces() } catch { provinces.value = [] }
}
async function loadCities() {
  cities.value = []
  if (!prof.province) return
  try { cities.value = await locationsApi.getCities(prof.province) } catch { cities.value = [] }
}
function onProvince() { prof.city = ''; loadCities() }

const profErrs = computed(() => {
  const e = {}
  const bn = validateBusinessName(prof.business_name, 'CF')
  const ad = validateAddress(prof.address)
  const ph = validatePhone(prof.phone)
  if (bn) e.business_name = bn
  if (ad) e.address = ad
  if (ph) e.phone = ph
  return e
})
const profErr = (k) => (profTouched[k] ? profErrs.value[k] || auth.fieldErrors[k] || '' : '')

async function saveProfile() {
  Object.keys(prof).forEach((k) => { profTouched[k] = true })
  profSaved.value = false
  if (Object.keys(profErrs.value).length) return
  profBusy.value = true
  const res = await auth.updateAccount({
    email: auth.user?.email,
    profile: {
      business_name: prof.business_name.trim() || null,
      address: prof.address.trim() || null,
      phone: prof.phone.trim() || null,
      ...(prof.province ? { province: Number(prof.province) } : {}),
      ...(prof.city ? { city: Number(prof.city) } : {})
    }
  })
  profBusy.value = false
  if (res.ok) profSaved.value = true
}
</script>

<template>
  <section>
    <h2 class="ab-title">Mi negocio</h2>
    <p class="ab-sub">Lo que tus clientes ven en tu web y tus datos de facturación.</p>

    <div class="ab-card">
      <h3 class="ab-h">Fotos</h3>
      <div class="ab-photos">
        <div class="ab-photo">
          <span class="ab-thumb">
            <img v-if="stores.customization.logo" :src="stores.customization.logo" alt="Logo" />
            <AppIcon v-else name="image" :size="20" />
          </span>
          <input ref="logoEl" type="file" accept="image/png,image/jpeg,image/webp" class="sr-only" @change="pickLogo" />
          <button type="button" class="btn ghost btn-auto" :disabled="logoBusy" @click="logoEl?.click()">
            <AppIcon name="upload" :size="14" /> {{ stores.customization.logo ? 'Cambiar logo' : 'Logo' }}
          </button>
          <button v-if="stores.customization.logo" type="button" class="btn ghost btn-auto" @click="stores.removeLogo()">Quitar</button>
        </div>
        <div class="ab-photo">
          <span class="ab-thumb wide">
            <img v-if="stores.customization.cover" :src="stores.customization.cover" alt="Portada" />
            <AppIcon v-else name="images" :size="20" />
          </span>
          <input ref="coverEl" type="file" accept="image/png,image/jpeg,image/webp" class="sr-only" @change="pickCover" />
          <button type="button" class="btn ghost btn-auto" :disabled="coverBusy" @click="coverEl?.click()">
            <AppIcon name="upload" :size="14" /> {{ stores.customization.cover ? 'Cambiar portada' : 'Portada' }}
          </button>
          <button v-if="stores.customization.cover" type="button" class="btn ghost btn-auto" @click="stores.removeCover()">Quitar</button>
        </div>
      </div>
      <p v-if="imgErr" class="field-error">{{ imgErr }}</p>
    </div>

    <div class="ab-card">
      <h3 class="ab-h">Tu web</h3>
      <div class="field">
        <label for="ab-dn">Nombre comercial</label>
        <input id="ab-dn" v-model="web.display_name" class="input" maxlength="60" placeholder="Ej. Almacén Don José" @blur="webTouched.display_name = true" />
        <p v-if="webErr('display_name')" class="field-error">{{ webErr('display_name') }}</p>
      </div>
      <div class="field">
        <label for="ab-hl">Titular</label>
        <input id="ab-hl" v-model="web.headline" class="input" maxlength="80" placeholder="Frase que te describe" @blur="webTouched.headline = true" />
        <p v-if="webErr('headline')" class="field-error">{{ webErr('headline') }}</p>
      </div>
      <div class="field">
        <label for="ab-desc">Descripción</label>
        <textarea id="ab-desc" v-model="web.description" class="textarea" rows="3" maxlength="300" placeholder="Contá qué hacés" @blur="webTouched.description = true"></textarea>
        <p v-if="webErr('description')" class="field-error">{{ webErr('description') }}</p>
      </div>
      <div class="field">
        <label for="ab-wa">WhatsApp</label>
        <input id="ab-wa" v-model="web.whatsapp" class="input" inputmode="tel" placeholder="Ej. 54911..." @blur="webTouched.whatsapp = true" />
        <p v-if="webErr('whatsapp')" class="field-error">{{ webErr('whatsapp') }}</p>
      </div>
      <div class="grid-2">
        <div class="field">
          <label for="ab-ig">Instagram</label>
          <input id="ab-ig" v-model="web.instagram" class="input" placeholder="@usuario" @blur="webTouched.instagram = true" />
          <p v-if="webErr('instagram')" class="field-error">{{ webErr('instagram') }}</p>
        </div>
        <div class="field">
          <label for="ab-tt">TikTok</label>
          <input id="ab-tt" v-model="web.tiktok" class="input" placeholder="@usuario" @blur="webTouched.tiktok = true" />
          <p v-if="webErr('tiktok')" class="field-error">{{ webErr('tiktok') }}</p>
        </div>
      </div>
      <div class="field">
        <label for="ab-fb">Facebook</label>
        <input id="ab-fb" v-model="web.facebook" class="input" placeholder="usuario o link" @blur="webTouched.facebook = true" />
        <p v-if="webErr('facebook')" class="field-error">{{ webErr('facebook') }}</p>
      </div>
      <div class="field">
        <label for="ab-ce">Email de contacto</label>
        <input id="ab-ce" v-model="web.contact_email" class="input" type="email" placeholder="donde te escriben" @blur="webTouched.contact_email = true" />
        <p v-if="webErr('contact_email')" class="field-error">{{ webErr('contact_email') }}</p>
      </div>
      <p v-if="stores.lastError" class="field-error">{{ stores.lastError }}</p>
      <p v-else-if="webSaved" class="ab-ok">Guardado ✓</p>
      <AppButton :loading="webBusy" @click="saveWeb">Guardar datos de la web</AppButton>
    </div>

    <div class="ab-card">
      <h3 class="ab-h">Facturación</h3>
      <div class="field">
        <label for="ab-bn">Nombre de negocio / razón social</label>
        <input id="ab-bn" v-model="prof.business_name" class="input" maxlength="120" @blur="profTouched.business_name = true" />
        <p v-if="profErr('business_name')" class="field-error">{{ profErr('business_name') }}</p>
      </div>
      <div class="grid-2">
        <div class="field">
          <label for="ab-pv">Provincia</label>
          <select id="ab-pv" v-model="prof.province" class="select" @change="onProvince">
            <option value="">Seleccioná</option>
            <option v-for="p in provinces" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>
        <div class="field">
          <label for="ab-ct">Ciudad</label>
          <select id="ab-ct" v-model="prof.city" class="select" :disabled="!prof.province">
            <option value="">Seleccioná</option>
            <option v-for="c in cities" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
      </div>
      <div class="field">
        <label for="ab-ad">Dirección</label>
        <input id="ab-ad" v-model="prof.address" class="input" maxlength="160" @blur="profTouched.address = true" />
        <p v-if="profErr('address')" class="field-error">{{ profErr('address') }}</p>
      </div>
      <div class="field">
        <label for="ab-ph">Celular</label>
        <input id="ab-ph" v-model="prof.phone" class="input" inputmode="tel" @blur="profTouched.phone = true" />
        <p v-if="profErr('phone')" class="field-error">{{ profErr('phone') }}</p>
      </div>
      <p v-if="auth.lastError" class="field-error">{{ auth.lastError }}</p>
      <p v-else-if="profSaved" class="ab-ok">Guardado ✓</p>
      <AppButton :loading="profBusy" @click="saveProfile">Guardar facturación</AppButton>
    </div>
  </section>
</template>

<style scoped>
.ab-title { font-size: 20px; font-weight: 800; margin: 0; }
.ab-sub { font-size: 13px; color: var(--muted, #6b6478); margin: 4px 0 14px; }
.ab-card {
  background: var(--card, #fff); border: 1px solid var(--line, #e5e5ef);
  border-radius: 14px; padding: 14px; margin-bottom: 14px;
}
.ab-h { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: var(--muted, #6b6478); margin: 0 0 10px; }
.ab-photos { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.ab-photo { display: flex; flex-direction: column; gap: 8px; align-items: flex-start; }
.ab-thumb {
  display: grid; place-items: center;
  width: 64px; height: 64px; border-radius: 12px; overflow: hidden;
  background: var(--bg, #f6f6fb); color: var(--muted, #6b6478);
}
.ab-thumb.wide { width: 100%; height: 64px; }
.ab-thumb img { width: 100%; height: 100%; object-fit: cover; }
.ab-ok { color: #059669; font-size: 13px; }
</style>
