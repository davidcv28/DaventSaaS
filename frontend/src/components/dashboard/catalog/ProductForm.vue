<script setup>
import AppIcon from '../../AppIcon.vue'
import AppInput from '../../AppInput.vue'
import AppButton from '../../AppButton.vue'
import { formatARS } from '../../../api/billing.api.js'

// Formulario de producto agrupado en bloques (Básicos / Precio y oferta /
// Foto / Organización). Todo el estado es del padre: `form`, `touched` y
// `features` llegan como objetos reactivos y se mutan por referencia.
const props = defineProps({
  form: { type: Object, required: true },
  touched: { type: Object, required: true },
  features: { type: Array, required: true },
  categories: { type: Array, default: () => [] },
  brands: { type: Array, default: () => [] },
  editing: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
  legacyOffer: { type: [Number, String], default: null },
  offerCleared: { type: Boolean, default: false },
  imagePreview: { type: String, default: '' },
  imageErr: { type: String, default: '' },
  hasImage: { type: Boolean, default: false },
  hasOriginal: { type: Boolean, default: false },
  bgBusy: { type: Boolean, default: false },
  accept: { type: String, default: 'image/*' },
  featureLimit: { type: Number, default: 20 },
  featuresErr: { type: String, default: '' },
  fieldErr: { type: Function, required: true },
  // Control de stock: solo se muestra con has_ecommerce en el plan
  // (sin el beneficio el backend rechaza la escritura del campo).
  stockEnabled: { type: Boolean, default: false }
})
const emit = defineEmits([
  'save', 'cancel', 'pick-image', 'remove-bg', 'restore-original',
  'clear-image', 'clear-offer', 'add-feature', 'remove-feature'
])
</script>

<template>
  <div class="card pform">
    <h3><AppIcon :name="editing ? 'pencil' : 'plus'" :size="18" /> {{ editing ? 'Editar producto' : 'Agregar un producto' }}</h3>
    <p class="lead">Completá lo básico y tocá «Publicar». Después lo podés cambiar cuando quieras.</p>

    <section class="pf-block" aria-labelledby="pf-basics">
      <h4 id="pf-basics" class="pf-title"><AppIcon name="package" :size="15" aria-hidden="true" /> Básicos</h4>
      <AppInput v-model="form.name" label="Nombre" name="prod_name" placeholder="Ej. Remera oversize" :error="fieldErr('name')" @blur="touched.name = true" />
      <div class="field">
        <label for="prod-active">Visibilidad</label>
        <select id="prod-active" v-model="form.is_active" class="select">
          <option :value="true">Visible en mi web</option>
          <option :value="false">Oculto</option>
        </select>
      </div>
    </section>

    <section class="pf-block" aria-labelledby="pf-price">
      <h4 id="pf-price" class="pf-title"><AppIcon name="tag" :size="15" aria-hidden="true" /> Precio y oferta</h4>
      <div class="grid-2">
        <AppInput v-model="form.price" label="Precio" name="prod_price" type="number" min="0" step="0.01" placeholder="0.00" :error="fieldErr('price')" @blur="touched.price = true" />
      </div>
      <div v-if="legacyOffer && !offerCleared" class="legacy-offer">
        <AppIcon name="tag" :size="14" aria-hidden="true" />
        <span>Este producto tiene una oferta manual: <strong>{{ formatARS(legacyOffer) }}</strong>. Las ofertas ahora se programan en «Descuentos».</span>
        <button type="button" class="legacy-offer-btn" @click="emit('clear-offer')">Quitar</button>
      </div>
      <p v-else class="hint">¿Oferta? Programala en la pestaña «Descuentos»: se activa y vence sola.</p>
    </section>

    <section v-if="stockEnabled" class="pf-block" aria-labelledby="pf-stock">
      <h4 id="pf-stock" class="pf-title"><AppIcon name="inbox" :size="15" aria-hidden="true" /> Stock</h4>
      <div class="grid-2">
        <AppInput v-model="form.stock" label="Unidades disponibles" name="prod_stock" type="number" min="0" step="1" placeholder="Sin límite" :error="fieldErr('stock')" @blur="touched.stock = true" />
      </div>
      <p class="hint">Cuántas unidades tenés para vender: 0 = agotado (no se puede comprar) y vacío = sin límite. Se descuenta solo cuando el pago se confirma.</p>
    </section>

    <section class="pf-block" aria-labelledby="pf-photo">
      <h4 id="pf-photo" class="pf-title"><AppIcon name="image" :size="15" aria-hidden="true" /> Foto</h4>
      <div class="field">
        <label id="prod-image-label" class="sr-only">Imagen del producto</label>
        <div class="logo-box">
          <span class="logo-thumb">
            <img v-if="imagePreview" :src="imagePreview" alt="Imagen del producto" />
            <AppIcon v-else name="image" :size="20" aria-hidden="true" />
          </span>
          <div class="logo-actions">
            <input ref="fileInput" type="file" class="sr-only" :accept="accept" aria-labelledby="prod-image-label" @change="emit('pick-image', $event)" />
            <button type="button" class="btn ghost btn-auto" @click="$refs.fileInput?.click()">
              <AppIcon name="upload" :size="16" /> {{ imagePreview ? 'Cambiar' : 'Subir imagen' }}
            </button>
            <button v-if="hasImage && !hasOriginal" type="button" class="btn ghost btn-auto" :disabled="bgBusy" @click="emit('remove-bg')">
              <span v-if="bgBusy" class="spinner" aria-hidden="true"></span><AppIcon v-else name="sparkles" :size="16" /> {{ bgBusy ? 'Procesando…' : 'Quitar fondo' }}
            </button>
            <button v-if="hasOriginal" type="button" class="btn ghost btn-auto" @click="emit('restore-original')">Volver al original</button>
            <button v-if="imagePreview" type="button" class="btn ghost btn-auto" @click="emit('clear-image')">Quitar</button>
          </div>
        </div>
        <p class="hint">Una foto clara vende más. Si el fondo molesta, usá «Quitar fondo». Máximo 4 MB. Usá solo fotos propias o con permiso.</p>
        <p v-if="imageErr" class="field-error" role="alert">{{ imageErr }}</p>
      </div>
    </section>

    <details class="more-opts" :open="editing">
      <summary><AppIcon name="layout-grid" :size="15" aria-hidden="true" /> Organización <small>(opcional: categoría, descripción, características)</small></summary>
      <div class="grid-2">
        <div class="field">
          <label for="prod-category">Categoría</label>
          <select id="prod-category" v-model="form.category" class="select">
            <option value="">Sin categoría</option>
            <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
          <p class="hint">Se cargan en la pestaña Categorías.</p>
        </div>
        <div class="field">
          <label for="prod-brand">Marca</label>
          <select id="prod-brand" v-model="form.brand" class="select">
            <option value="">Sin marca</option>
            <option v-for="b in brands" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select>
        </div>
      </div>
      <div class="field">
        <label for="prod-description">Descripción</label>
        <textarea
          id="prod-description"
          v-model="form.description"
          class="textarea"
          :class="{ invalid: fieldErr('description') }"
          placeholder="Detalles del producto (opcional)"
          maxlength="600"
          rows="3"
          @blur="touched.description = true"
        ></textarea>
        <p class="hint">{{ form.description.length }}/600</p>
        <p v-if="fieldErr('description')" class="field-error" role="alert">{{ fieldErr('description') }}</p>
      </div>
      <div class="field">
        <label id="prod-features-label">Características</label>
        <ul v-if="features.length" class="feat-rows" aria-labelledby="prod-features-label">
          <li v-for="(row, i) in features" :key="i" class="feat-row">
            <input v-model="row.name" class="input" type="text" maxlength="40" placeholder="Atributo (ej. Talle)" :aria-label="`Nombre de la característica ${i + 1}`" />
            <input v-model="row.value" class="input" type="text" maxlength="120" placeholder="Valor (ej. M)" :aria-label="`Valor de la característica ${i + 1}`" />
            <button type="button" class="icon-btn danger" aria-label="Quitar característica" @click="emit('remove-feature', i)"><AppIcon name="trash" :size="15" /></button>
          </li>
        </ul>
        <button type="button" class="btn ghost btn-auto" :disabled="features.length >= featureLimit" @click="emit('add-feature')"><AppIcon name="plus" :size="15" /> Agregar característica</button>
        <p class="hint">La categoría sugiere atributos (se cargan desde la pestaña Categorías); podés sumar otros propios.</p>
        <p v-if="touched.features && featuresErr" class="field-error" role="alert">{{ featuresErr }}</p>
      </div>
    </details>

    <div class="btn-row">
      <AppButton :loading="busy" @click="emit('save')">{{ editing ? 'Guardar cambios' : 'Publicar producto' }}</AppButton>
      <button v-if="editing" type="button" class="btn ghost btn-auto" @click="emit('cancel')">Cancelar</button>
    </div>
  </div>
</template>

<style scoped>
.pf-block { padding: 14px 0 2px; border-top: 1px solid var(--line); margin-top: 14px; }
.pf-block:first-of-type { border-top: none; margin-top: 4px; padding-top: 4px; }
.pf-title {
  display: flex; align-items: center; gap: 7px; margin: 0 0 12px;
  font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em;
  color: var(--muted);
}
.pf-title svg { color: var(--brand-500); }
/* Cada bloque lleva su propio tono: azul básicos, verde precio, violeta foto,
   ámbar organización — el ojo encuentra la sección sin leer el título. */
section.pf-block:nth-of-type(2) .pf-title svg { color: #059669; }
/* Stock y foto por id (no nth-of-type): la sección de stock es condicional
   y movería el índice de la foto cuando el plan la habilita. */
#pf-stock svg { color: #0d9488; }
#pf-photo svg { color: #8b5cf6; }
.more-opts > summary svg { color: #d97706; }
</style>
