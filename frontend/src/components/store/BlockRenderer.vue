<script setup>
// BlockRenderer: monta los bloques habilitados de una superficie pública
// en el orden del layout efectivo (default de la plantilla ∪
// layout_config). Cada id resuelve a un componente async del mapa
// `components` que recibe el Template Definition; los bloques apagados o
// sin componente no se montan, y los que quedan vacíos se auto-ocultan en
// su propio v-if (sin secciones vacías).
// Cada bloque recibe :block="{id, enabled, order, variant?, props?}" para
// aplicar su variante/props (p.ej. props.title = título alternativo).
//
// Bloques solo-IA: el motor guarda ids (aiquote, aistrip…) que la
// plantilla no declara en su layout canónico. Si el layout guardado los
// trae y hay componente, se insertan en su `order` — así el catálogo de
// bloques de cada plantilla no tiene que conocerlos.
//
// Overrides de site_theme.blocks[<id>] (radius/shadow/border/density/
// surface/align/accent): se emiten como variables --blk-* en el wrapper
// real del bloque. Sin override el wrapper sigue en display:contents, así
// ninguna de las 6 plantillas cambia de aspecto.
import { computed, inject } from 'vue'
import { resolveLayout } from '../../templates/index.js'

const props = defineProps({
  surface: { type: String, required: true },
  components: { type: Object, required: true }
})

const ctx = inject('storePage')
const resolved = computed(() =>
  resolveLayout(
    ctx.pageTemplate.value,
    props.surface,
    ctx.custom.value?.layout_config
  ).filter((b) => b.enabled && props.components[b.id])
)
const blocks = computed(() => {
  const base = resolved.value
  const saved = ctx.custom.value?.layout_config?.[props.surface]?.blocks
  if (!Array.isArray(saved)) return base
  const known = new Set(base.map((b) => b.id))
  const extras = []
  saved.forEach((raw, i) => {
    if (!raw || raw.id == null || raw.enabled === false) return
    if (known.has(raw.id) || !props.components[raw.id]) return
    known.add(raw.id)
    extras.push({
      id: raw.id,
      enabled: true,
      order: typeof raw.order === 'number' ? raw.order : i,
      variant: typeof raw.variant === 'string' && raw.variant ? raw.variant : undefined,
      props: raw.props && typeof raw.props === 'object' ? raw.props : undefined
    })
  })
  if (!extras.length) return base
  const out = [...base]
  for (const ex of extras) out.splice(Math.min(ex.order, out.length), 0, ex)
  return out
})

// Enums del contrato → valores concretos. Un valor desconocido se ignora
// (el bloque queda con su piel de siempre).
const RADIUS = { none: '0px', sm: '10px', md: '16px', lg: '22px', xl: '30px', full: '999px' }
const SHADOW = {
  none: 'none',
  soft: '0 8px 24px -14px rgba(15, 23, 42, .22)',
  md: '0 14px 38px -18px rgba(15, 23, 42, .3)',
  strong: '0 26px 64px -26px rgba(15, 23, 42, .45)'
}
const BORDER = {
  none: '0',
  hairline: '1px solid var(--sp-line)',
  strong: '2px solid color-mix(in srgb, var(--store-accent) 45%, var(--sp-line))'
}
const DENSITY = {
  compact: 'clamp(10px, 2.4vw, 20px)',
  cozy: 'clamp(20px, 4vw, 40px)',
  spacious: 'clamp(32px, 6vw, 72px)'
}
const SURFACE = {
  none: 'transparent',
  plain: 'var(--sp-bg)',
  soft: 'var(--sp-soft)',
  card: 'var(--sp-card-solid)',
  glass: 'color-mix(in srgb, var(--sp-card-solid) 62%, transparent)'
}
const ALIGN = { left: 'left', center: 'center', right: 'right' }

const overrideFor = (id) => {
  const all = ctx.custom.value?.site_theme?.blocks
  const o = all && typeof all === 'object' ? all[id] : null
  return o && typeof o === 'object' ? o : null
}
const hasOverride = (id) => Boolean(overrideFor(id))
function wrapStyle(id) {
  const o = overrideFor(id)
  if (!o) return { display: 'contents' }
  const style = {}
  if (RADIUS[o.radius]) style['--blk-radius'] = RADIUS[o.radius]
  if (SHADOW[o.shadow]) style['--blk-shadow'] = SHADOW[o.shadow]
  if (BORDER[o.border]) style['--blk-border'] = BORDER[o.border]
  if (DENSITY[o.density]) style['--blk-density'] = DENSITY[o.density]
  if (SURFACE[o.surface]) style['--blk-surface'] = SURFACE[o.surface]
  if (ALIGN[o.align]) style['--blk-align'] = ALIGN[o.align]
  if (typeof o.accent === 'string' && /^#[0-9a-f]{6}$/i.test(o.accent)) style['--blk-accent'] = o.accent
  return style
}
</script>

<template>
  <!-- data-blk marca cada bloque para el editor (scroll-sync); el wrapper
       con display:contents no toca el layout de la página. Solo pasa a
       wrapper real cuando site_theme.blocks fija overrides del bloque. -->
  <div
    v-for="b in blocks" :key="b.id" :data-blk="b.id"
    :class="{ 'blk-wrap': hasOverride(b.id) }"
    :data-blk-surface="hasOverride(b.id) ? (overrideFor(b.id).surface || null) : null"
    :style="wrapStyle(b.id)"
  >
    <component :is="components[b.id]" :block="b" />
  </div>
</template>
