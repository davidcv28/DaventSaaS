<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useStoreStore } from '../stores/store.store.js'
import { storeThemeVars, validateImageFile, LOGO_ACCEPT } from '../api/stores.api.js'
import { catalogApi } from '../api/catalog.api.js'
import { formatARS } from '../api/billing.api.js'
import { FLYER_KINDS, FLYER_SIZES, FLYER_LIMITS, layoutsOfKind, layoutById, sizeById, imposition, flyerProduct, loadFlyerDraft, saveFlyerDraft, clearFlyerDraft } from '../utils/flyer.js'
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

const products = ref([])
const loadingProducts = ref(false)
const layouts = computed(() => layoutsOfKind(draft.kind))
const curLayout = computed(() => layoutById(draft.layout))
const isCatalog = computed(() => !!curLayout.value.products)
const ph = computed(() => curLayout.value.ph || {})
const maxProducts = computed(() => curLayout.value.products || 4)
const sizeInfo = computed(() => sizeById(draft.size))
const imp = computed(() => imposition(draft.size, draft.sheet))
const filled = computed(() => imposition(draft.size, 'a4'))
const chosen = computed(() => draft.productIds.map((id) => products.value.find((p) => p.id === id)).filter(Boolean).slice(0, maxProducts.value))

function setKind(kind) {
  if (draft.kind === kind) return
  draft.kind = kind
  draft.layout = layoutsOfKind(kind)[0].id
}
function toggleProduct(id) {
  const i = draft.productIds.indexOf(id)
  if (i >= 0) draft.productIds.splice(i, 1)
  else if (draft.productIds.length < maxProducts.value) draft.productIds.push(id)
}
watch(() => draft.layout, () => { draft.productIds.splice(maxProducts.value) })

onMounted(async () => {
  loadingProducts.value = true
  try {
    const rows = await catalogApi.listProducts()
    products.value = rows.filter((p) => p.is_active !== false).map(flyerProduct)
    const ids = new Set(products.value.map((p) => p.id))
    draft.productIds = draft.productIds.filter((id) => ids.has(id))
  } catch { products.value = [] }
  loadingProducts.value = false
})

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
        <h3><AppIcon name="layout-grid" :size="18" /> 1. Elegí el tipo y el diseño</h3>
        <div class="studio-kinds" role="radiogroup" aria-label="Tipo de folleto">
          <button v-for="k in FLYER_KINDS" :key="k.id" type="button" role="radio" class="studio-kind" :class="{ on: draft.kind === k.id }" :aria-checked="draft.kind === k.id" @click="setKind(k.id)">
            <AppIcon :name="k.icon" :size="18" />
            <span><strong>{{ k.label }}</strong><small>{{ k.desc }}</small></span>
          </button>
        </div>
        <div class="studio-layouts" role="radiogroup" aria-label="Diseño del folleto">
          <label v-for="l in layouts" :key="l.id" class="studio-layout" :class="{ on: draft.layout === l.id }">
            <input v-model="draft.layout" type="radio" name="flyer-layout" :value="l.id" class="sr-only" />
            <span class="studio-layout-icon"><AppIcon :name="l.icon" :size="18" /></span>
            <strong>{{ l.label }}</strong>
            <small>{{ l.desc }}</small>
          </label>
        </div>
      </section>

      <section class="card studio-card">
        <h3><AppIcon name="file-text" :size="18" /> 2. Tamaño y hoja de impresión</h3>
        <div class="studio-sizes" role="radiogroup" aria-label="Tamaño del folleto">
          <button v-for="s in FLYER_SIZES" :key="s.id" type="button" role="radio" class="studio-size" :class="{ on: draft.size === s.id }" :aria-checked="draft.size === s.id" @click="draft.size = s.id">
            <strong>{{ s.label }}</strong>
            <small>{{ s.w }}×{{ s.h }} mm</small>
            <small>{{ s.note }}</small>
          </button>
        </div>
        <div v-if="draft.size !== 'a4'" class="field studio-sheet-q">
          <label>¿Lo vas a imprimir en una hoja A4?</label>
          <div class="check-list">
            <label class="check-item"><input v-model="draft.sheet" type="radio" name="flyer-sheet" value="a4" /><span class="check-text"><strong>Sí, llenar la hoja A4</strong><small>Se acomodan {{ filled.count }} {{ sizeInfo.label }} por hoja ({{ filled.cols }}×{{ filled.rows }}{{ filled.landscape ? ', hoja apaisada' : '' }}), sin pisarse, listos para cortar.</small></span></label>
            <label class="check-item"><input v-model="draft.sheet" type="radio" name="flyer-sheet" value="own" /><span class="check-text"><strong>No, una por hoja</strong><small>Sale una sola copia en una hoja de {{ sizeInfo.w }}×{{ sizeInfo.h }} mm.</small></span></label>
          </div>
        </div>
        <p v-else class="hint">El A4 ocupa la hoja entera: sale una copia por hoja.</p>
        <div class="studio-imp" aria-hidden="true">
          <div class="studio-imp-page" :style="{ aspectRatio: `${imp.pageW} / ${imp.pageH}`, gridTemplateColumns: `repeat(${imp.cols}, ${imp.fw / imp.pageW * 100}%)`, gridTemplateRows: `repeat(${imp.rows}, ${imp.fh / imp.pageH * 100}%)` }">
            <i v-for="n in imp.count" :key="n"></i>
          </div>
          <span>{{ imp.count }} {{ imp.count === 1 ? 'copia' : 'copias' }} por hoja · {{ imp.own ? `hoja ${imp.pageW}×${imp.pageH} mm` : `A4 ${imp.landscape ? 'apaisada' : 'vertical'}` }}</span>
        </div>
      </section>

      <section v-if="isCatalog" class="card studio-card">
        <h3><AppIcon name="package" :size="18" /> 3. Elegí los productos <span class="counter">{{ draft.productIds.length }}/{{ maxProducts }}</span></h3>
        <p class="lead">Marcá hasta {{ maxProducts }} productos de tu catálogo: el folleto muestra su foto y su precio actual (con oferta si la tienen).</p>
        <p v-if="loadingProducts" class="hint"><span class="spinner spinner-brand" aria-hidden="true"></span> Cargando tu catálogo…</p>
        <p v-else-if="!products.length" class="hint">Todavía no tenés productos activos en tu catálogo. Cargalos y volvé: mientras tanto se ve un ejemplo.</p>
        <div v-else class="studio-prods">
          <button v-for="p in products" :key="p.id" type="button" class="studio-prod" :class="{ on: draft.productIds.includes(p.id) }" :aria-pressed="draft.productIds.includes(p.id)" @click="toggleProduct(p.id)">
            <span class="studio-prod-img"><img v-if="p.image" :src="p.image" alt="" /><AppIcon v-else name="image" :size="16" /></span>
            <span class="studio-prod-txt"><strong>{{ p.name }}</strong><small>{{ formatARS(p.price) }}</small></span>
            <span v-if="draft.productIds.includes(p.id)" class="studio-photo-check"><AppIcon name="check" :size="12" :stroke="3" /></span>
          </button>
        </div>
      </section>

      <section v-if="!isCatalog" class="card studio-card">
        <h3><AppIcon name="image" :size="18" /> 3. Foto del folleto</h3>
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
        <h3><AppIcon name="pencil" :size="18" /> 4. Completá los textos</h3>
        <div class="field">
          <label for="fl-title"><AppIcon name="type" :size="14" class="label-icon" aria-hidden="true" />Titular <span class="counter">{{ draft.title.length }}/{{ L.title }}</span></label>
          <input id="fl-title" v-model="draft.title" class="input" :maxlength="L.title" :placeholder="ph.title || 'Ej. Liquidación de invierno'" />
        </div>
        <div class="field">
          <label for="fl-sub"><AppIcon name="file-text" :size="14" class="label-icon" aria-hidden="true" />Frase de apoyo <span class="counter">{{ draft.subtitle.length }}/{{ L.subtitle }}</span></label>
          <input id="fl-sub" v-model="draft.subtitle" class="input" :maxlength="L.subtitle" :placeholder="ph.subtitle || 'Ej. Hasta agotar stock en toda la tienda'" />
        </div>
        <div class="field">
          <label for="fl-badge"><AppIcon name="tag" :size="14" class="label-icon" aria-hidden="true" />Sello o descuento <span class="counter">{{ draft.badge.length }}/{{ L.badge }}</span></label>
          <input id="fl-badge" v-model="draft.badge" class="input" :maxlength="L.badge" :placeholder="ph.badge || 'Ej. -30% OFF'" />
          <p class="hint">Opcional. Se destaca en el diseño; dejalo vacío si no hay oferta.</p>
        </div>
        <div v-if="!isCatalog || curLayout.perks" class="field">
          <label><AppIcon name="checklist" :size="14" class="label-icon" aria-hidden="true" />{{ ph.bulletsLabel || 'Puntos destacados' }}</label>
          <div class="studio-bullets">
            <div v-for="(_, i) in draft.bullets" :key="i" class="studio-bullet">
              <span class="studio-bullet-n">{{ i + 1 }}</span>
              <input v-model="draft.bullets[i]" class="input" :maxlength="L.bullet" :placeholder="(ph.bullets || ['Ej. Envíos a todo el país', 'Ej. 3 cuotas sin interés', 'Ej. Cambios sin cargo', ''])[i]" :aria-label="`Punto destacado ${i + 1}`" />
            </div>
          </div>
        </div>
      </section>

      <section class="card studio-card">
        <h3><AppIcon name="qr-code" :size="18" /> 5. Contacto y QR</h3>
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
        <div class="studio-sheet"><FlyerCanvas :design="draft" :products="chosen" :shop-name="shopName" :logo="logo" :qr="qr" :url="url" /></div>
        <p class="hint">Tamaño {{ sizeInfo.label }} ({{ sizeInfo.w }}×{{ sizeInfo.h }} mm): {{ imp.count === 1 ? 'sale 1 por hoja' : `salen ${imp.count} por hoja A4${imp.landscape ? ' apaisada' : ''}` }}. El color sale del acento de tu web.</p>
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

.studio-kinds { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(220px, 100%), 1fr)); gap: 10px; margin-bottom: 12px; }
.studio-kind { display: flex; align-items: flex-start; gap: 10px; padding: 12px 14px; text-align: left; font: inherit; color: var(--muted); border: 1px solid var(--line); border-radius: 12px; background: var(--card); cursor: pointer; transition: border-color .15s, box-shadow .15s; }
.studio-kind span { display: grid; gap: 2px; }
.studio-kind strong { font-size: 14px; color: var(--text, inherit); }
.studio-kind small { font-size: 12px; line-height: 1.4; }
.studio-kind:hover { border-color: var(--brand-400); }
.studio-kind.on { border-color: var(--brand-500); box-shadow: var(--ring); color: var(--brand-ink); background: linear-gradient(160deg, var(--brand-soft), transparent 80%), var(--card); }

.studio-sizes { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 10px; margin-bottom: 12px; }
.studio-size { display: grid; gap: 2px; justify-items: start; padding: 12px; font: inherit; border: 1px solid var(--line); border-radius: 12px; background: var(--card); cursor: pointer; transition: border-color .15s, box-shadow .15s; }
.studio-size strong { font-size: 18px; }
.studio-size small { color: var(--muted); font-size: 11.5px; }
.studio-size:hover { border-color: var(--brand-400); }
.studio-size.on { border-color: var(--brand-500); box-shadow: var(--ring); background: linear-gradient(160deg, var(--brand-soft), transparent 80%), var(--card); }
.studio-sheet-q { margin-bottom: 10px; }
.studio-imp { display: flex; align-items: center; gap: 12px; font-size: 12.5px; color: var(--muted); }
.studio-imp-page { flex: none; width: 64px; display: grid; justify-content: center; align-content: center; background: #fff; border: 1px solid var(--line); box-shadow: 0 2px 8px rgba(15, 23, 42, .15); }
.studio-imp-page i { border: 1px dashed var(--brand-500); background: var(--brand-soft); box-sizing: border-box; }

.studio-prods { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 8px; max-height: 320px; overflow-y: auto; padding: 2px; }
.studio-prod { position: relative; display: flex; align-items: center; gap: 10px; padding: 8px; font: inherit; text-align: left; border: 2px solid var(--line); border-radius: 12px; background: var(--card); cursor: pointer; min-width: 0; transition: border-color .15s; }
.studio-prod:hover { border-color: var(--brand-400); }
.studio-prod.on { border-color: var(--brand-500); box-shadow: var(--ring); }
.studio-prod-img { flex: none; width: 42px; height: 42px; border-radius: 8px; overflow: hidden; background: var(--surface); display: grid; place-items: center; color: var(--muted); }
.studio-prod-img img { width: 100%; height: 100%; object-fit: cover; }
.studio-prod-txt { display: grid; min-width: 0; padding-right: 18px; }
.studio-prod-txt strong { font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.studio-prod-txt small { color: var(--muted); font-size: 12px; }

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
