<script setup>
// Panel "Estilos" — flujo guiado en 3 niveles (mobile-first):
//   1 · Elegí un estilo   -> galería de presets (protagonista)
//   2 · Ajustes rápidos   -> tema, acento, fuente y logo (lo más tocado)
//   3 · Personalización   -> DesignLookTab completo, colapsado por defecto
// Sin lógica de datos propia: escribe los mismos campos de `form` que
// DesignLookTab y dispara los mismos eventos (ring/navigate/set-viewer).
// Cada control vive en un PanelField con data-focus del contrato, así el
// shell dibuja el anillo sobre el elemento real de la vista previa.
import { ref, computed, onMounted } from 'vue'
import AppIcon from '../../AppIcon.vue'
import DesignLookTab from '../../design/DesignLookTab.vue'
import PresetGallery from '../../../studio/presets/PresetGallery.vue'
import PanelField from './PanelField.vue'
import PanelLock from './PanelLock.vue'
import { useStoreStore } from '../../../stores/store.store.js'
import {
  STORE_ACCENTS, STORE_FONTS, STORE_FONT_PICKER,
  storeFontFamily, ensureStoreFont, ensureStoreFontPicker,
  effectiveAccent, validateLogoFile, LOGO_ACCEPT
} from '../../../api/stores.api.js'
import { normalizeHex } from '../../../utils/colorTools.js'

const props = defineProps({
  form: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) },
  shopName: { type: String, default: '' }
})
const emit = defineEmits(['navigate', 'ring', 'set-viewer'])

const store = useStoreStore()
const advanced = computed(() => Boolean(props.benefits?.has_design_advanced))

// Anillos del LookTab (logo/accent/font/cover) -> targets del contrato.
const RING_MAP = { logo: 'chrome.nav', accent: 'buttons', font: 'typo', cover: 'hero' }
const onLookRing = (key) => emit('ring', RING_MAP[key] || key)

// ---------------------------------------------------------------------------
// Nivel 3: personalización avanzada (progresiva — arranca plegada)
// ---------------------------------------------------------------------------
const advOpen = ref(false)

// ---------------------------------------------------------------------------
// Nivel 2 — Tema claro/oscuro (persiste + cambia el modo del visor)
// ---------------------------------------------------------------------------
const themeOpts = [
  { id: 'light', label: 'Claro' },
  { id: 'dark', label: 'Oscuro' }
]
function pickTheme(id) {
  props.form.theme = id
  emit('set-viewer', id)
}

// ---------------------------------------------------------------------------
// Nivel 2 — Acento: los 8 presets del catálogo + color propio (Premium).
// Misma escritura que DesignLookTab: accent slug o accent_custom hex.
// ---------------------------------------------------------------------------
const accents = STORE_ACCENTS
const accentMeta = computed(() => effectiveAccent(props.form))
function pickAccent(key) {
  if (!advanced.value) return
  props.form.accent = key
  props.form.accent_custom = ''
}
function setCustomAccent(hex) {
  if (!advanced.value) return
  const n = normalizeHex(hex)
  if (n) props.form.accent_custom = n
}

// ---------------------------------------------------------------------------
// Nivel 2 — Tipografía: chips del catálogo popular en carril con snap.
// Si quedó guardada una fuente fuera del picker (preset/otra época) se
// muestra al principio — mismo criterio que el grupo "Guardada" del LookTab.
// ---------------------------------------------------------------------------
const fontKeys = computed(() => {
  const saved = props.form.name_font
  return saved && !STORE_FONT_PICKER.includes(saved) ? [saved, ...STORE_FONT_PICKER] : STORE_FONT_PICKER
})
function pickFont(key) {
  if (!advanced.value) return
  ensureStoreFont(key)
  props.form.name_font = key
}

// ---------------------------------------------------------------------------
// Nivel 2 — Logo: misma subida que DesignLookTab (validación + store).
// ---------------------------------------------------------------------------
const logoInput = ref(null)
const logoBusy = ref(false)
const logoErr = ref('')
const currentLogo = computed(() => store.customization?.logo || '')
const LOGO_ACCEPT_TYPES = LOGO_ACCEPT

async function onLogoPicked(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  logoErr.value = validateLogoFile(file)
  if (logoErr.value) return
  logoBusy.value = true
  const ok = await store.uploadLogo(file)
  logoBusy.value = false
  if (!ok) logoErr.value = store.fieldErrors.logo || store.lastError
}

async function onRemoveLogo() {
  if (logoBusy.value) return
  logoErr.value = ''
  logoBusy.value = true
  const ok = await store.removeLogo()
  logoBusy.value = false
  if (!ok) logoErr.value = store.fieldErrors.logo || store.lastError
}

onMounted(() => {
  ensureStoreFont(props.form.name_font)
  // El carril de fuentes muestra sus muestras reales: una sola hoja css2.
  setTimeout(ensureStoreFontPicker, 400)
})
</script>

<template>
  <div class="stl-flow">
    <!-- ============ Nivel 1 · Elegí un estilo ============ -->
    <section class="stl" aria-labelledby="stl-h-presets">
      <header class="stl-head">
        <span class="stl-n" aria-hidden="true">1</span>
        <div class="stl-head-tx">
          <h3 id="stl-h-presets">Elegí un estilo</h3>
          <p>Un look completo en un toque. <b>Probar</b> lo ves en vivo y se deshace; nada se guarda hasta que guardás vos.</p>
        </div>
      </header>
      <PresetGallery :benefits="benefits" />
    </section>

    <!-- ============ Nivel 2 · Ajustes rápidos ============ -->
    <section class="stl" aria-labelledby="stl-h-quick">
      <header class="stl-head">
        <span class="stl-n" aria-hidden="true">2</span>
        <div class="stl-head-tx">
          <h3 id="stl-h-quick">Ajustes rápidos</h3>
          <p>Lo esencial sobre el estilo elegido: tema, acento, fuente y logo.</p>
        </div>
      </header>

      <div class="stl-quick">
        <PanelField label="Tema" focus="page" need="none" :benefits="benefits">
          <div class="stp-seg" role="group" aria-label="Tema claro u oscuro de la página">
            <button
              v-for="o in themeOpts" :key="o.id" type="button"
              class="stp-opt" :class="{ active: form.theme === o.id }"
              :aria-pressed="form.theme === o.id" @click="pickTheme(o.id)"
            >{{ o.label }}</button>
          </div>
        </PanelField>

        <PanelField label="Logo" focus="chrome.nav" need="none" :benefits="benefits">
          <div class="stl-logo">
            <span class="stl-logo-thumb">
              <img v-if="currentLogo" :src="currentLogo" alt="Logo de tu tienda" />
              <AppIcon v-else name="image" :size="20" aria-hidden="true" />
            </span>
            <div class="stl-logo-acts">
              <input ref="logoInput" type="file" class="sr-only" :accept="LOGO_ACCEPT_TYPES" aria-label="Subir logo" @change="onLogoPicked" />
              <button type="button" class="btn ghost btn-auto" :disabled="logoBusy" @click="logoInput?.click()">
                <span v-if="logoBusy" class="spinner" aria-hidden="true"></span>
                <AppIcon v-else name="upload" :size="15" aria-hidden="true" />
                {{ currentLogo ? 'Cambiar' : 'Subir' }}
              </button>
              <button v-if="currentLogo" type="button" class="icon-btn" :disabled="logoBusy" aria-label="Quitar el logo" @click="onRemoveLogo">
                <AppIcon name="x" :size="15" aria-hidden="true" />
              </button>
            </div>
          </div>
          <p v-if="logoErr" class="field-error" role="alert">{{ logoErr }}</p>
        </PanelField>

        <PanelField class="stl-wide" label="Acento" focus="buttons" need="advanced" :benefits="benefits" hint="Color de botones, enlaces y detalles.">
          <div class="stl-accents" role="group" aria-label="Color de acento">
            <button
              v-for="(a, key) in accents" :key="key" type="button"
              class="stl-swatch" :class="{ active: form.accent === key && !form.accent_custom }"
              :style="{ '--sw': a.hex }" :title="a.label"
              :aria-label="`Acento ${a.label}`" :aria-pressed="form.accent === key && !form.accent_custom"
              @click="pickAccent(key)"
            ><AppIcon v-if="form.accent === key && !form.accent_custom" name="check" :size="15" :stroke="2.5" aria-hidden="true" /></button>
            <label class="stl-swatch stl-swatch-pick" :class="{ active: form.accent_custom }" :style="{ '--sw': accentMeta.hex }" title="Color propio">
              <input type="color" :value="accentMeta.hex" aria-label="Elegir un color de acento propio" @input="setCustomAccent($event.target.value)" />
              <AppIcon name="pipette" :size="16" aria-hidden="true" />
            </label>
          </div>
        </PanelField>

        <PanelField class="stl-wide" label="Tipografía" focus="typo" need="advanced" :benefits="benefits" hint="Se aplica a todo el texto de tu página.">
          <div class="stl-fonts" role="group" aria-label="Fuente de tu página">
            <button
              v-for="key in fontKeys" :key="key" type="button"
              class="stl-font" :class="{ active: form.name_font === key }"
              :aria-pressed="form.name_font === key" :title="STORE_FONTS[key]?.label"
              @click="pickFont(key)"
            >
              <span class="stl-font-aa" :style="{ fontFamily: storeFontFamily(key) }" aria-hidden="true">Aa</span>
              <span class="stl-font-n">{{ STORE_FONTS[key]?.label }}</span>
            </button>
          </div>
        </PanelField>
      </div>

      <PanelLock
        v-if="!advanced"
        text="El acento y la tipografía vienen con el Plan premium."
        @plans="emit('navigate', 'plans')"
      />
    </section>

    <!-- ============ Nivel 3 · Personalización avanzada ============ -->
    <section class="stl" :class="{ 'stl-open': advOpen }">
      <h3 class="stl-adv-h">
        <button
          type="button" class="stl-adv-btn" data-focus="hero"
          :aria-expanded="advOpen" aria-controls="stl-adv-body"
          @click="advOpen = !advOpen"
        >
          <span class="stl-n" aria-hidden="true">3</span>
          <span class="stl-adv-tx">
            <strong>Personalización avanzada</strong>
            <small>Portada, tamaños, contraste y diseño en detalle.</small>
          </span>
          <AppIcon class="stl-chev" name="chevron-down" :size="17" aria-hidden="true" />
        </button>
      </h3>
      <div v-show="advOpen" id="stl-adv-body" class="stl-adv-body">
        <DesignLookTab
          :form="form" :benefits="benefits" :shop-name="shopName"
          @go-plans="emit('navigate', 'plans')" @ring="onLookRing"
        />
      </div>
    </section>
  </div>
</template>
