<script setup>
// App nativa — Productos: lista con buscador, switch de visibilidad,
// alta/edición en hoja inferior y borrado. Reutiliza catalog.store y la
// API multipart de productos (imagen incluida, normalizada a WebP en el
// backend igual que el panel web).
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useCatalogStore } from '../../stores/catalog.store.js'
import { formatARS } from '../../api/billing.api.js'
import {
  productListOffer, validateProductName, validateProductPrice,
  validateProductDescription, validateProductFeatures
} from '../../api/catalog.api.js'
import { validateImageFile as validateImg } from '../../api/stores.api.js'
import AppIcon from '../../components/AppIcon.vue'
import AppButton from '../../components/AppButton.vue'

const catalog = useCatalogStore()

onMounted(() => {
  if (catalog.status === 'idle') catalog.loadAll()
})

const q = ref('')
const items = computed(() => {
  const needle = q.value.trim().toLowerCase()
  const list = catalog.products || []
  if (!needle) return list
  return list.filter((p) => [p.name, p.category_name, p.brand_name].filter(Boolean).join(' ').toLowerCase().includes(needle))
})

const offerOf = (p) => productListOffer(p)

// ----- Hoja de edición -----
const sheet = ref(false)
const editing = ref(null) // producto en edición | null = alta
const busy = ref(false)
const imageFile = ref(null)
const imagePreview = ref('')
const imageErr = ref('')
const form = reactive({ name: '', price: '', is_active: true, category: '', brand: '', description: '' })
const features = ref([])
const touched = reactive({})

const fieldErr = (k) => (touched[k] ? errs.value[k] || catalog.fieldErrors[k] || '' : catalog.fieldErrors[k] || '')
const errs = computed(() => {
  const e = {}
  const n = validateProductName(form.name)
  const pr = validateProductPrice(form.price)
  const d = validateProductDescription(form.description)
  const f = validateProductFeatures(features.value)
  if (n) e.name = n
  if (pr) e.price = pr
  if (d) e.description = d
  if (f) e.features = f
  return e
})

function openSheet(product) {
  editing.value = product || null
  Object.assign(form, {
    name: product?.name || '',
    price: product?.price ?? '',
    is_active: product?.is_active ?? true,
    category: product?.category || '',
    brand: product?.brand || '',
    description: product?.description || ''
  })
  features.value = Object.entries(product?.features || {}).map(([name, value]) => ({ name, value }))
  imageFile.value = null
  imagePreview.value = product?.image || ''
  imageErr.value = ''
  Object.keys(touched).forEach((k) => { touched[k] = false })
  sheet.value = true
}
function closeSheet() { if (!busy.value) sheet.value = false }

function pickImage(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  const err = validateImg(file)
  if (err) { imageErr.value = err; return }
  imageErr.value = ''
  imageFile.value = file
  imagePreview.value = URL.createObjectURL(file)
}
function clearImage() {
  imageFile.value = null
  imagePreview.value = ''
}

async function save() {
  Object.keys(form).forEach((k) => { touched[k] = true })
  touched.features = true
  if (Object.keys(errs.value).length) return
  busy.value = true
  const feats = {}
  for (const r of features.value) {
    const n = r.name.trim()
    if (n && r.value.trim()) feats[n] = r.value.trim()
  }
  const fields = {
    name: form.name.trim(),
    price: form.price,
    is_active: form.is_active ? 'true' : 'false',
    description: form.description.trim(),
    category: form.category || '',
    brand: form.brand || '',
    features: feats
  }
  const res = await catalog.saveProduct(editing.value?.id || null, {
    fields,
    image: imageFile.value,
    imageClear: !imagePreview.value && Boolean(editing.value?.image)
  })
  busy.value = false
  if (res.ok) sheet.value = false
}

async function toggleVisible(p) {
  await catalog.saveProduct(p.id, { fields: { is_active: !p.is_active ? 'true' : 'false' } })
}

async function remove(p) {
  if (!window.confirm(`¿Eliminar "${p.name}"? Esta acción no se puede deshacer.`)) return
  await catalog.removeProduct(p.id)
}

// El teclado del WebView puede tapar la hoja: al abrir inputs llevar el foco a la vista.
watch(sheet, (v) => { document.body.style.overflow = v ? 'hidden' : '' })
</script>

<template>
  <section class="ap-sec">
    <div class="ap-head">
      <h2 class="ap-title">Productos</h2>
      <span class="ap-count">{{ catalog.products.length }}</span>
    </div>

    <div class="ap-search">
      <AppIcon name="search" :size="16" />
      <input v-model="q" type="search" placeholder="Buscar producto…" class="ap-search-input" />
    </div>

    <p v-if="catalog.lastError" class="field-error">{{ catalog.lastError }}</p>
    <p v-else-if="catalog.notice" class="ap-ok">{{ catalog.notice }}</p>

    <div v-if="catalog.status === 'loading'" class="ap-empty">Cargando…</div>
    <div v-else-if="!items.length" class="ap-empty">
      {{ q ? 'Sin resultados para esa búsqueda.' : 'Todavía no tenés productos. Tocá + para cargar el primero.' }}
    </div>

    <ul class="ap-list">
      <li v-for="p in items" :key="p.id" class="ap-row" @click="openSheet(p)">
        <span class="ap-thumb">
          <img v-if="p.image" :src="p.image" alt="" loading="lazy" />
          <AppIcon v-else name="image" :size="18" />
        </span>
        <span class="ap-info">
          <strong class="ap-name">{{ p.name }}</strong>
          <span class="ap-price">
            <template v-if="offerOf(p) !== null">
              <s>{{ formatARS(p.price) }}</s> {{ formatARS(offerOf(p)) }}
            </template>
            <template v-else>{{ formatARS(p.price) }}</template>
          </span>
        </span>
        <label class="ap-switch" @click.stop>
          <input type="checkbox" :checked="p.is_active" @change="toggleVisible(p)" />
          <span class="ap-track" aria-hidden="true"></span>
          <span class="sr-only">{{ p.is_active ? 'Visible' : 'Oculto' }}</span>
        </label>
      </li>
    </ul>

    <button type="button" class="ap-fab" aria-label="Agregar producto" @click="openSheet(null)">
      <AppIcon name="plus" :size="24" />
    </button>

    <Teleport to="body">
      <div v-if="sheet" class="ap-scrim" @click.self="closeSheet">
        <div class="ap-sheet" role="dialog" aria-modal="true" :aria-label="editing ? 'Editar producto' : 'Agregar producto'">
          <div class="ap-sheet-head">
            <h3>{{ editing ? 'Editar producto' : 'Nuevo producto' }}</h3>
            <button type="button" class="ap-iconbtn" aria-label="Cerrar" @click="closeSheet"><AppIcon name="x" :size="18" /></button>
          </div>

          <div class="field">
            <label for="ap-name">Nombre</label>
            <input id="ap-name" v-model="form.name" class="input" maxlength="120" placeholder="Ej. Remera oversize" @blur="touched.name = true" />
            <p v-if="fieldErr('name')" class="field-error">{{ fieldErr('name') }}</p>
          </div>

          <div class="grid-2">
            <div class="field">
              <label for="ap-price">Precio</label>
              <input id="ap-price" v-model="form.price" class="input" type="number" min="0" step="0.01" inputmode="decimal" placeholder="0.00" @blur="touched.price = true" />
              <p v-if="fieldErr('price')" class="field-error">{{ fieldErr('price') }}</p>
            </div>
            <div class="field">
              <label for="ap-vis">Visibilidad</label>
              <select id="ap-vis" v-model="form.is_active" class="select">
                <option :value="true">Visible</option>
                <option :value="false">Oculto</option>
              </select>
            </div>
          </div>

          <div class="grid-2">
            <div class="field">
              <label for="ap-cat">Categoría</label>
              <select id="ap-cat" v-model="form.category" class="select">
                <option value="">Sin categoría</option>
                <option v-for="c in catalog.categories" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
            </div>
            <div class="field">
              <label for="ap-brand">Marca</label>
              <select id="ap-brand" v-model="form.brand" class="select">
                <option value="">Sin marca</option>
                <option v-for="b in catalog.brands" :key="b.id" :value="b.id">{{ b.name }}</option>
              </select>
            </div>
          </div>

          <div class="field">
            <label>Foto</label>
            <div class="ap-imgrow">
              <span class="ap-thumb lg">
                <img v-if="imagePreview" :src="imagePreview" alt="" />
                <AppIcon v-else name="image" :size="20" />
              </span>
              <input ref="fileEl" type="file" accept="image/png,image/jpeg,image/webp" class="sr-only" @change="pickImage" />
              <button type="button" class="btn ghost btn-auto" @click="$refs.fileEl?.click()"><AppIcon name="upload" :size="15" /> {{ imagePreview ? 'Cambiar' : 'Subir' }}</button>
              <button v-if="imagePreview" type="button" class="btn ghost btn-auto" @click="clearImage">Quitar</button>
            </div>
            <p v-if="imageErr" class="field-error">{{ imageErr }}</p>
          </div>

          <div class="field">
            <label for="ap-desc">Descripción</label>
            <textarea id="ap-desc" v-model="form.description" class="textarea" rows="3" maxlength="600" placeholder="Detalles (opcional)" @blur="touched.description = true"></textarea>
            <p v-if="fieldErr('description')" class="field-error">{{ fieldErr('description') }}</p>
          </div>

          <div class="field">
            <label>Características <small class="ap-small">(opcional)</small></label>
            <div v-for="(row, i) in features" :key="i" class="ap-feat">
              <input v-model="row.name" class="input" maxlength="40" placeholder="Atributo (ej. Talle)" />
              <input v-model="row.value" class="input" maxlength="120" placeholder="Valor (ej. M)" />
              <button type="button" class="ap-iconbtn" aria-label="Quitar" @click="features.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
            </div>
            <button type="button" class="btn ghost btn-auto" @click="features.push({ name: '', value: '' })"><AppIcon name="plus" :size="14" /> Característica</button>
            <p v-if="touched.features && errs.features" class="field-error">{{ errs.features }}</p>
          </div>

          <p v-if="catalog.lastError" class="field-error">{{ catalog.lastError }}</p>
          <div class="btn-row">
            <AppButton :loading="busy" @click="save">{{ editing ? 'Guardar' : 'Publicar' }}</AppButton>
            <button v-if="editing" type="button" class="btn ghost danger" @click="remove(editing); sheet = false"><AppIcon name="trash" :size="15" /> Eliminar</button>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<style scoped>
.ap-head { display: flex; align-items: baseline; gap: 8px; margin-bottom: 10px; }
.ap-title { font-size: 20px; font-weight: 800; margin: 0; }
.ap-count { font-size: 12px; font-weight: 700; color: var(--muted, #6b6478); background: var(--card, #fff); border: 1px solid var(--line, #e5e5ef); border-radius: 999px; padding: 1px 8px; }
.ap-search {
  display: flex; align-items: center; gap: 8px;
  background: var(--card, #fff); border: 1px solid var(--line, #e5e5ef);
  border-radius: 12px; padding: 9px 12px; margin-bottom: 12px;
  color: var(--muted, #6b6478);
}
.ap-search-input { flex: 1; border: 0; outline: 0; background: none; font-size: 15px; color: var(--ink, #17141f); }
.ap-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.ap-row {
  display: flex; align-items: center; gap: 12px;
  background: var(--card, #fff); border: 1px solid var(--line, #e5e5ef);
  border-radius: 14px; padding: 10px 12px; cursor: pointer;
}
.ap-thumb {
  display: grid; place-items: center; flex: none;
  width: 44px; height: 44px; border-radius: 10px; overflow: hidden;
  background: var(--bg, #f6f6fb); color: var(--muted, #6b6478);
}
.ap-thumb.lg { width: 56px; height: 56px; }
.ap-thumb img { width: 100%; height: 100%; object-fit: cover; }
.ap-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.ap-name { font-size: 14px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ap-price { font-size: 13px; color: var(--muted, #6b6478); }
.ap-price s { margin-right: 5px; opacity: .6; }
.ap-empty { padding: 40px 12px; text-align: center; color: var(--muted, #6b6478); font-size: 14px; }
.ap-ok { color: #059669; font-size: 13px; }
.ap-fab {
  position: fixed; right: 16px; bottom: calc(76px + env(safe-area-inset-bottom, 0px));
  z-index: 25; width: 56px; height: 56px; border-radius: 50%;
  border: 0; background: var(--brand-500, #4f46e5); color: #fff;
  display: grid; place-items: center; cursor: pointer;
  box-shadow: 0 8px 22px rgba(79, 70, 229, .4);
}
.ap-scrim {
  position: fixed; inset: 0; z-index: 60;
  background: rgba(15, 12, 25, .5);
  display: flex; align-items: flex-end; justify-content: center;
}
.ap-sheet {
  width: 100%; max-width: 560px; max-height: 88dvh; overflow-y: auto;
  background: var(--card, #fff); border-radius: 20px 20px 0 0;
  padding: 16px 16px calc(20px + env(safe-area-inset-bottom, 0px));
}
.ap-sheet-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.ap-sheet-head h3 { margin: 0; font-size: 17px; }
.ap-iconbtn {
  display: grid; place-items: center; flex: none;
  width: 34px; height: 34px; border-radius: 9px;
  border: 1px solid var(--line, #e5e5ef); background: none;
  color: var(--muted, #6b6478); cursor: pointer;
}
.ap-imgrow { display: flex; align-items: center; gap: 10px; }
.ap-feat { display: grid; grid-template-columns: 1fr 1fr auto; gap: 6px; margin-bottom: 6px; }
.ap-small { color: var(--muted, #6b6478); font-weight: 400; }
.ap-switch { position: relative; flex: none; cursor: pointer; }
.ap-switch input { position: absolute; opacity: 0; inset: 0; cursor: pointer; }
.ap-track {
  display: block; width: 42px; height: 24px; border-radius: 999px;
  background: var(--line, #d8d6e3); transition: background .15s; position: relative;
}
.ap-track::after {
  content: ''; position: absolute; top: 3px; left: 3px;
  width: 18px; height: 18px; border-radius: 50%; background: #fff;
  transition: left .15s; box-shadow: 0 1px 3px rgba(0,0,0,.25);
}
.ap-switch input:checked + .ap-track { background: var(--brand-500, #4f46e5); }
.ap-switch input:checked + .ap-track::after { left: 21px; }
</style>
