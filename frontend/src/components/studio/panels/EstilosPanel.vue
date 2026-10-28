<script setup>
// Panel "Estilos" — un solo camino: elegir el look mirando.
//   · Elegí el estilo de tu web  -> select por tier + vista previa
//   · Ajustá el estilo elegido   -> modo, color de botones, letra y logo
//   · Más ajustes de diseño      -> DesignLookTab completo, plegado
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

const advOpen = ref(false)

// ---------------------------------------------------------------------------
// Claro u oscuro: cambia el juego de colores del estilo sin re-elegirlo.
// ---------------------------------------------------------------------------
const themeOpts = [
  { id: 'light', label: 'Claro', icon: 'sun' },
  { id: 'dark', label: 'Oscuro', icon: 'moon' }
]
function pickTheme(id) {
  props.form.theme = id
  emit('set-viewer', id)
}

// ---------------------------------------------------------------------------
// Color de los botones: los 8 presets del catálogo + color propio (Premium).
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
// Letra: catálogo popular. Una fuente guardada fuera del picker se muestra
// igual, al principio — mismo criterio que el grupo "Guardada" del LookTab.
// ---------------------------------------------------------------------------
const fontKeys = computed(() => {
  const saved = props.form.name_font
  return saved && !STORE_FONT_PICKER.includes(saved) ? [saved, ...STORE_FONT_PICKER] : STORE_FONT_PICKER
})
function pickFont(key) {
  if (!advanced.value || !key) return
  ensureStoreFont(key)
  props.form.name_font = key
}

// ---------------------------------------------------------------------------
// Logo: misma subida que DesignLookTab (validación + store).
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
  // La muestra "Aa" y la lista se ven con su letra real: una sola hoja css2.
  setTimeout(ensureStoreFontPicker, 400)
})
</script>

<template>
  <div class="est">
    <!-- ============ Elegí el estilo de tu web ============ -->
    <section class="est-pick" aria-labelledby="est-h">
      <header class="est-head">
        <h3 id="est-h">Elegí el estilo de tu web</h3>
        <p>Elegí uno y mirá la vista previa.</p>
      </header>
      <PresetGallery
        :benefits="benefits"
        :mode="form.theme === 'dark' ? 'dark' : 'light'"
        :accent="accentMeta.hex"
      />
    </section>

    <!-- ============ Ajustá el estilo elegido ============ -->
    <section class="est-tune" aria-labelledby="est-h-tune">
      <header class="est-tune-head">
        <h3 id="est-h-tune">Ajustá el estilo elegido</h3>
        <p>Cambios finos: no reemplazan el estilo, lo afinan.</p>
      </header>

      <PanelField label="Claro u oscuro" focus="page" need="none" :benefits="benefits">
        <div class="stp-seg est-seg" role="group" aria-label="Modo de color de la web">
          <button
            v-for="o in themeOpts" :key="o.id" type="button"
            class="stp-opt" :class="{ active: form.theme === o.id }"
            :aria-pressed="form.theme === o.id" @click="pickTheme(o.id)"
          >
            <AppIcon :name="o.icon" :size="14" aria-hidden="true" /> {{ o.label }}
          </button>
        </div>
      </PanelField>

      <PanelField
        label="Color de los botones" focus="buttons" need="advanced" :benefits="benefits"
        hint="Se mezcla con los colores de arriba: tiñe botones, enlaces y detalles."
      >
        <div class="est-accents" role="group" aria-label="Color de los botones">
          <button
            v-for="(a, key) in accents" :key="key" type="button"
            class="est-swatch" :class="{ active: form.accent === key && !form.accent_custom }"
            :style="{ '--sw': a.hex }" :title="a.label"
            :aria-label="`Color ${a.label}`" :aria-pressed="form.accent === key && !form.accent_custom"
            @click="pickAccent(key)"
          ><AppIcon v-if="form.accent === key && !form.accent_custom" name="check" :size="15" :stroke="2.6" aria-hidden="true" /></button>
          <label class="est-swatch est-swatch-pick" :class="{ active: form.accent_custom }" :style="{ '--sw': accentMeta.hex }" title="Elegir otro color">
            <input type="color" :value="accentMeta.hex" aria-label="Elegir otro color de botones" @input="setCustomAccent($event.target.value)" />
            <AppIcon name="pipette" :size="16" aria-hidden="true" />
          </label>
        </div>
      </PanelField>

      <PanelField label="Letra de tu web" focus="typo" need="advanced" :benefits="benefits">
        <div class="est-font">
          <span class="est-font-aa" :style="{ fontFamily: storeFontFamily(form.name_font) }" aria-hidden="true">Aa</span>
          <select
            class="stp-select" :value="form.name_font" aria-label="Letra de tu web"
            @change="pickFont($event.target.value)"
          >
            <option v-for="key in fontKeys" :key="key" :value="key">{{ STORE_FONTS[key]?.label || key }}</option>
          </select>
        </div>
      </PanelField>

      <PanelField label="Logo" focus="chrome.nav" need="none" :benefits="benefits">
        <div class="est-logo">
          <span class="est-logo-thumb">
            <img v-if="currentLogo" :src="currentLogo" alt="Logo de tu tienda" />
            <AppIcon v-else name="image" :size="18" aria-hidden="true" />
          </span>
          <div class="est-logo-acts">
            <input ref="logoInput" type="file" class="sr-only" :accept="LOGO_ACCEPT_TYPES" aria-label="Subir logo" @change="onLogoPicked" />
            <button type="button" class="btn ghost btn-auto est-logo-btn" :disabled="logoBusy" @click="logoInput?.click()">
              <span v-if="logoBusy" class="spinner" aria-hidden="true"></span>
              <AppIcon v-else name="upload" :size="14" aria-hidden="true" />
              {{ currentLogo ? 'Cambiar' : 'Subir' }}
            </button>
            <button v-if="currentLogo" type="button" class="icon-btn est-logo-x" :disabled="logoBusy" aria-label="Quitar el logo" @click="onRemoveLogo">
              <AppIcon name="x" :size="15" aria-hidden="true" />
            </button>
          </div>
        </div>
        <p v-if="logoErr" class="field-error" role="alert">{{ logoErr }}</p>
      </PanelField>

      <PanelLock
        v-if="!advanced"
        text="El color de los botones y la letra vienen con el Plan premium."
        @plans="emit('navigate', 'plans')"
      />
    </section>

    <!-- ============ Más ajustes de diseño (plegado) ============ -->
    <section class="est-more" :class="{ 'is-open': advOpen }">
      <button
        type="button" class="est-more-btn" data-focus="hero"
        :aria-expanded="advOpen" aria-controls="est-more-body"
        @click="advOpen = !advOpen"
      >
        <AppIcon class="est-more-ico" name="sliders" :size="16" aria-hidden="true" />
        <span class="est-more-tx">
          <strong>Más ajustes de diseño</strong>
          <small>Portada, tamaños, contraste y botones.</small>
        </span>
        <AppIcon class="est-chev" name="chevron-down" :size="17" aria-hidden="true" />
      </button>
      <div v-show="advOpen" id="est-more-body" class="est-more-body">
        <DesignLookTab
          :form="form" :benefits="benefits" :shop-name="shopName"
          @go-plans="emit('navigate', 'plans')" @ring="onLookRing"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.est { display: flex; flex-direction: column; gap: 14px; min-width: 0; }

/* ===== Encabezado del camino principal ===== */
.est-pick { display: flex; flex-direction: column; gap: 7px; min-width: 0; }
.est-head h3 { margin: 0; font-size: 14px; font-weight: 800; letter-spacing: -.01em; color: var(--ink); }
.est-head p { margin: 2px 0 0; font-size: 12px; line-height: 1.4; color: var(--muted); overflow-wrap: anywhere; }

/* ===== Ajustes subordinados al estilo ===== */
.est-tune {
  display: flex; flex-direction: column; gap: 8px; min-width: 0;
  padding-top: 12px; border-top: 1px solid var(--line-soft);
}
.est-tune-head h3 { margin: 0; font-size: 13px; font-weight: 800; color: var(--ink); }
.est-tune-head p { margin: 2px 0 0; font-size: 11.5px; line-height: 1.4; color: var(--muted); overflow-wrap: anywhere; }
.est-seg { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }

/* Color de botones: grilla completa, sin scroll. */
.est-accents { display: grid; grid-template-columns: repeat(auto-fill, minmax(40px, 1fr)); gap: 6px; min-width: 0; }
.est-swatch {
  position: relative; display: grid; place-items: center; justify-self: center;
  width: 40px; height: 40px; padding: 0; border: 0; border-radius: 50%;
  background: var(--sw); color: #fff; cursor: pointer; transition: box-shadow .14s;
}
.est-swatch.active { outline: 2px solid var(--ink); outline-offset: 2px; }
.est-swatch:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.est-swatch-pick { border: 1px dashed rgba(255, 255, 255, .55); }
.est-swatch-pick input { position: absolute; inset: 0; width: 100%; height: 100%; padding: 0; border: 0; opacity: 0; cursor: pointer; }
.est-swatch-pick .icon { pointer-events: none; filter: drop-shadow(0 1px 2px rgba(0, 0, 0, .55)); }

/* Letra: muestra real + lista, en una sola línea. */
.est-font { display: flex; align-items: center; gap: 8px; min-width: 0; }
.est-font-aa {
  flex: none; display: grid; place-items: center; width: 44px; height: 44px;
  border: 1px solid var(--line); border-radius: 9px; background: var(--surface);
  color: var(--ink); font-size: 20px; line-height: 1;
}
.est-font .stp-select { flex: 1; min-width: 0; }

/* Logo: miniatura + acciones en una línea. */
.est-logo { display: flex; align-items: center; gap: 8px; min-width: 0; }
.est-logo-thumb {
  flex: none; display: grid; place-items: center; width: 44px; height: 44px;
  border: 1px solid var(--line); border-radius: 9px; background: var(--surface);
  color: var(--muted); overflow: hidden;
}
.est-logo-thumb img { width: 100%; height: 100%; object-fit: contain; display: block; }
.est-logo-acts { display: flex; align-items: center; gap: 6px; min-width: 0; }
.est-logo-btn { min-height: 44px; padding: 8px 12px; font-size: 12.5px; }
.est-logo-x { flex: none; width: 44px; height: 44px; }
.est-logo-x:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }

/* ===== Más ajustes (secundario, plegado) ===== */
.est-more { padding-top: 12px; border-top: 1px solid var(--line-soft); min-width: 0; }
.est-more-btn {
  display: flex; align-items: center; gap: 8px; width: 100%; min-height: 48px; min-width: 0;
  padding: 6px 8px; border: 1px solid var(--line); border-radius: 10px;
  background: var(--surface); color: var(--ink-2); font: inherit; text-align: left; cursor: pointer;
}
.est-more-btn:hover { border-color: var(--brand-500); }
.est-more-btn:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.est-more-ico { flex: none; color: var(--muted); }
.est-more-tx { flex: 1; display: grid; gap: 1px; min-width: 0; }
.est-more-tx strong { font-size: 12.5px; font-weight: 700; color: var(--ink); }
.est-more-tx small { font-size: 11px; line-height: 1.3; color: var(--muted); overflow-wrap: anywhere; }
.est-chev { flex: none; color: var(--muted); transition: transform .18s ease; }
.est-more.is-open .est-chev { transform: rotate(180deg); }
.est-more-body { display: grid; gap: 12px; min-width: 0; padding-top: 10px; }

@media (prefers-reduced-motion: reduce) {
  .est-swatch, .est-chev { transition: none; }
}
</style>
