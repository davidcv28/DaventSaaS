<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useStoreStore } from '../stores/store.store.js'
import { storeThemeVars, validateImageFile, LOGO_ACCEPT } from '../api/stores.api.js'
import { FLYER_LAYOUTS, FLYER_LIMITS, loadFlyerDraft, saveFlyerDraft, clearFlyerDraft } from '../utils/flyer.js'
import AppIcon from './AppIcon.vue'
import FlyerCanvas from './FlyerCanvas.vue'

// Diseñador de folletos: DAVENT arma el diseño, el cliente completa textos y
// elige foto. Las fotos salen de su galería; si sube una nueva, entra a la
// galería (mismo cupo del plan) y queda seleccionada.
const props = defineProps({
  slug: { type: String, default: '' },
  shopName: { type: String, default: 'Mi tienda' },
  logo: { type: String, default: '' },
  qr: { type: String, default: '' },
  url: { type: String, default: '' },
  contact: { type: String, default: '' },
  canAddGallery: { type: Boolean, default: false },
  galleryHint: { type: String, default: '' }
})
const emit = defineEmits(['print'])

const store = useStoreStore()
const draft = reactive(loadFlyerDraft(props.slug, props.contact))
const fileInput = ref(null)
const busy = ref(false)
const err = ref('')
const L = FLYER_LIMITS

const gallery = computed(() => store.customization.gallery || [])
const themeVars = computed(() => storeThemeVars(store.customization))
const accept = LOGO_ACCEPT

watch(draft, () => saveFlyerDraft(props.slug, draft), { deep: true })
watch(() => props.contact, (c) => { if (c && !draft.contact) draft.contact = c })

// Si la foto elegida se borró de la galería, se limpia sola.
watch(gallery, (list) => {
  if (draft.photo && !list.some((g) => g.url === draft.photo)) draft.photo = ''
})

async function onPick(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || !props.canAddGallery) return
  err.value = validateImageFile(file)
  if (err.value) return
  const before = new Set(gallery.value.map((g) => g.id))
  busy.value = true
  const ok = await store.addGalleryImage(file)
  busy.value = false
  if (!ok) {
    err.value = store.fieldErrors.image || store.fieldErrors.detail || store.lastError
    return
  }
  const added = gallery.value.find((g) => !before.has(g.id))
  if (added) draft.photo = added.url
}

function reset() {
  clearFlyerDraft(props.slug)
  Object.assign(draft, loadFlyerDraft(props.slug, props.contact))
}
</script>

<template>
  <div class="studio">
    <div class="studio-form">
      <section class="card studio-card">
        <h3><AppIcon name="layout-grid" :size="18" /> 1. Elegí el diseño</h3>
        <div class="studio-layouts" role="radiogroup" aria-label="Diseño del folleto">
          <label v-for="l in FLYER_LAYOUTS" :key="l.id" class="studio-layout" :class="{ on: draft.layout === l.id }">
            <input v-model="draft.layout" type="radio" name="flyer-layout" :value="l.id" class="sr-only" />
            <span class="studio-layout-icon"><AppIcon :name="l.icon" :size="18" /></span>
            <strong>{{ l.label }}</strong>
            <small>{{ l.desc }}</small>
          </label>
        </div>
      </section>

      <section class="card studio-card">
        <h3><AppIcon name="image" :size="18" /> 2. Foto del folleto</h3>
        <p class="lead">Elegí una de tu galería o subí una nueva: la foto que subas acá queda guardada también en la galería de tu web.</p>
        <div class="studio-photos">
          <button type="button" class="studio-photo none" :class="{ on: !draft.photo }" @click="draft.photo = ''">
            <AppIcon name="x" :size="18" /><span>Sin foto</span>
          </button>
          <button v-for="(g, i) in gallery" :key="g.id" type="button" class="studio-photo" :class="{ on: draft.photo === g.url }" :aria-pressed="draft.photo === g.url" :aria-label="`Usar la imagen ${i + 1} de la galería`" @click="draft.photo = g.url">
            <img :src="g.url" alt="" />
            <span v-if="draft.photo === g.url" class="studio-photo-check"><AppIcon name="check" :size="12" :stroke="3" /></span>
          </button>
          <button type="button" class="studio-photo add" :disabled="busy || !canAddGallery" @click="fileInput?.click()">
            <span v-if="busy" class="spinner spinner-brand" aria-hidden="true"></span>
            <AppIcon v-else name="upload" :size="18" />
            <span>Subir foto</span>
          </button>
        </div>
        <input ref="fileInput" type="file" class="sr-only" :accept="accept" aria-label="Subir una foto a la galería" @change="onPick" />
        <p v-if="!gallery.length" class="hint">Todavía no tenés fotos en la galería. Subí la primera desde acá.</p>
        <p v-if="!canAddGallery" class="hint">Llegaste al cupo de la galería de tu plan: elegí una existente o liberá lugar en Diseño web → Fotos.</p>
        <p v-if="err" class="field-error" role="alert">{{ err }}</p>
      </section>

      <section class="card studio-card">
        <h3><AppIcon name="pencil" :size="18" /> 3. Completá los textos</h3>
        <div class="field">
          <label for="fl-title"><AppIcon name="type" :size="14" class="label-icon" aria-hidden="true" />Titular <span class="counter">{{ draft.title.length }}/{{ L.title }}</span></label>
          <input id="fl-title" v-model="draft.title" class="input" :maxlength="L.title" placeholder="Ej. Liquidación de invierno" />
        </div>
        <div class="field">
          <label for="fl-sub"><AppIcon name="file-text" :size="14" class="label-icon" aria-hidden="true" />Frase de apoyo <span class="counter">{{ draft.subtitle.length }}/{{ L.subtitle }}</span></label>
          <input id="fl-sub" v-model="draft.subtitle" class="input" :maxlength="L.subtitle" placeholder="Ej. Hasta agotar stock en toda la tienda" />
        </div>
        <div class="field">
          <label for="fl-badge"><AppIcon name="tag" :size="14" class="label-icon" aria-hidden="true" />Sello o descuento <span class="counter">{{ draft.badge.length }}/{{ L.badge }}</span></label>
          <input id="fl-badge" v-model="draft.badge" class="input" :maxlength="L.badge" placeholder="Ej. -30% OFF" />
          <p class="hint">Opcional. Se destaca en el diseño; dejalo vacío si no hay oferta.</p>
        </div>
        <div class="field">
          <label><AppIcon name="checklist" :size="14" class="label-icon" aria-hidden="true" />Puntos destacados</label>
          <div class="studio-bullets">
            <div v-for="(_, i) in draft.bullets" :key="i" class="studio-bullet">
              <span class="studio-bullet-n">{{ i + 1 }}</span>
              <input v-model="draft.bullets[i]" class="input" :maxlength="L.bullet" :placeholder="['Ej. Envíos a todo el país', 'Ej. 3 cuotas sin interés', 'Ej. Cambios sin cargo'][i]" :aria-label="`Punto destacado ${i + 1}`" />
            </div>
          </div>
        </div>
      </section>

      <section class="card studio-card">
        <h3><AppIcon name="qr-code" :size="18" /> 4. Contacto y QR</h3>
        <div class="field">
          <label for="fl-cta"><AppIcon name="megaphone" :size="14" class="label-icon" aria-hidden="true" />Llamado a la acción</label>
          <input id="fl-cta" v-model="draft.cta" class="input" :maxlength="L.cta" placeholder="Ej. Escaneá y mirá todo el catálogo" />
        </div>
        <div class="field">
          <label for="fl-contact"><AppIcon name="whatsapp" :size="14" class="label-icon" aria-hidden="true" />WhatsApp o teléfono</label>
          <input id="fl-contact" v-model="draft.contact" class="input" :maxlength="L.contact" placeholder="Ej. +54 9 387 155 1234" />
        </div>
        <div class="check-list">
          <label class="check-item"><input v-model="draft.showQr" type="checkbox" /><span class="check-text"><strong>Mostrar el código QR</strong><small>Lleva directo a tu página.</small></span></label>
          <label class="check-item"><input v-model="draft.showLogo" type="checkbox" /><span class="check-text"><strong>Mostrar logo y nombre</strong><small>En la cabecera del folleto.</small></span></label>
        </div>
      </section>
    </div>

    <aside class="studio-side">
      <div class="card studio-preview" :style="themeVars">
        <h3><AppIcon name="eye" :size="18" /> Vista previa</h3>
        <div class="studio-sheet"><FlyerCanvas :design="draft" :shop-name="shopName" :logo="logo" :qr="qr" :url="url" /></div>
        <p class="hint">Tamaño A5: salen 2 por hoja A4 apaisada. El color sale del acento de tu web.</p>
        <div class="btn-row">
          <button type="button" class="btn btn-auto" @click="emit('print')"><AppIcon name="printer" :size="16" /> Imprimir / PDF</button>
          <button type="button" class="btn ghost btn-auto" @click="reset"><AppIcon name="refresh" :size="16" /> Empezar de cero</button>
        </div>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.studio { display: grid; grid-template-columns: minmax(0, 1fr) minmax(280px, 380px); gap: 18px; align-items: start; }
.studio-form { display: grid; gap: 14px; min-width: 0; }
.studio-card { margin-bottom: 0; }
.studio-side { position: sticky; top: 16px; }
.studio-preview { margin-bottom: 0; background: linear-gradient(180deg, var(--surface), var(--card)); }
.studio-sheet { width: min(100%, 300px); margin: 6px auto 12px; border-radius: 6px; overflow: hidden; box-shadow: 0 18px 40px -16px rgba(15, 23, 42, .5), 0 0 0 1px var(--line); }

.studio-layouts { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
.studio-layout { position: relative; display: grid; gap: 4px; align-content: start; padding: 14px; border: 1px solid var(--line); border-radius: 12px; background: var(--card); cursor: pointer; transition: border-color .15s, box-shadow .15s, transform .15s; }
.studio-layout:hover { border-color: var(--brand-400); transform: translateY(-1px); }
.studio-layout.on { border-color: var(--brand-500); box-shadow: var(--ring); background: linear-gradient(160deg, var(--brand-soft), transparent 80%), var(--card); }
.studio-layout:has(:focus-visible) { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.studio-layout-icon { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 10px; background: var(--surface); color: var(--muted); border: 1px solid var(--line); margin-bottom: 4px; transition: all .18s; }
.studio-layout.on .studio-layout-icon { background: linear-gradient(135deg, var(--brand-500), var(--accent)); color: #fff; border-color: transparent; }
.studio-layout strong { font-size: 14px; }
.studio-layout small { color: var(--muted); font-size: 12px; line-height: 1.4; }

.studio-photos { display: grid; grid-template-columns: repeat(auto-fill, minmax(84px, 1fr)); gap: 10px; }
.studio-photo { position: relative; aspect-ratio: 1; padding: 0; overflow: hidden; border: 2px solid var(--line); border-radius: 12px; background: var(--surface); cursor: pointer; display: grid; place-items: center; gap: 4px; align-content: center; font: inherit; font-size: 11.5px; font-weight: 600; color: var(--muted); transition: border-color .15s, box-shadow .15s, transform .15s; }
.studio-photo img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.studio-photo:hover:not(:disabled) { border-color: var(--brand-400); transform: translateY(-1px); }
.studio-photo.on { border-color: var(--brand-500); box-shadow: var(--ring); }
.studio-photo.add { border-style: dashed; color: var(--brand-ink); background: var(--brand-soft); }
.studio-photo:disabled { opacity: .5; cursor: not-allowed; }
.studio-photo-check { position: absolute; top: 6px; right: 6px; width: 20px; height: 20px; border-radius: 50%; background: var(--brand-500); color: #fff; display: grid; place-items: center; box-shadow: 0 2px 6px rgba(0, 0, 0, .35); }

.counter { margin-left: auto; font-size: 11.5px; font-weight: 600; color: var(--muted); }
.studio-bullets { display: grid; gap: 8px; }
.studio-bullet { display: flex; align-items: center; gap: 10px; }
.studio-bullet .input { flex: 1; }
.studio-bullet-n { flex: none; width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center; background: var(--brand-soft); color: var(--brand-ink); font-size: 12px; font-weight: 800; }

@media (max-width: 900px) {
  .studio { grid-template-columns: 1fr; }
  .studio-side { position: static; }
}
</style>
