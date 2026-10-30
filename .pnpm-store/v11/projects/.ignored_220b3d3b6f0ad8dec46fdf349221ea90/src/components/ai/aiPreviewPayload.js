// Payload compartido de las vistas previas de "Diseñar con IA".
// La miniatura de cada propuesta (AiLiveThumb) y el modal por dispositivo
// (AiDevicePreview) montan la MISMA landing real en un iframe (?studio=1) y
// le empujan la propuesta con el protocolo del Studio. Un solo lugar arma el
// mensaje: si el contrato cambia, cambia acá y las dos previews quedan
// idénticas a lo que se va a publicar.
import { studioUpdate } from '../../studio/contract.js'

// Campos del form que no viajan como `custom`: el tema y el layout tienen su
// propia clave en el mensaje.
const SKIP = new Set(['site_theme', 'site_theme_draft', 'layout_config', 'layout_config_draft', 'template', 'template_draft'])

// postMessage no puede structured-clonar proxies reactivos (DataCloneError).
export function clonePlain(value) {
  try { return JSON.parse(JSON.stringify(value)) } catch { return null }
}

// copy_draft -> campos de negocio de la web (`steps` se persiste en
// service_steps; el resto comparte nombre).
export function draftFields(draft) {
  if (!draft || typeof draft !== 'object') return {}
  const out = {}
  for (const key of ('about_text', 'about_mission', 'faqs', 'services', 'announcements')) {
    if (draft[key]) out[key] = draft[key]
  }
  if (Array.isArray(draft.steps) && draft.steps.length) out.service_steps = draft.steps
  return out
}

// Mensaje studio:update con la propuesta aplicada.
export function buildStudioUpdate({ proposal, form, template, mode, device, shopName, logo, cover } = {}) {
  const custom = {}
  for (const [key, value] of Object.entries(form || {})) {
    if (!SKIP.has(key)) custom[key] = value
  }
  Object.assign(
    custom,
    proposal?.copy || {},
    draftFields(proposal?.copy_draft),
    {
      display_name: shopName || custom.display_name,
      logo: logo || null,
      cover: cover || null
    }
  )
  const message = studioUpdate({
    theme: proposal?.site_theme || form?.site_theme || {},
    layout: clonePlain(proposal?.layout_config || {}) || {},
    template,
    device
  })
  message.mode = mode === 'dark' ? 'dark' : 'light'
  message.custom = clonePlain(custom) || {}
  return message
}

export function previewSrc(publicUrl) {
  return publicUrl ? `${publicUrl}?studio=1` : ''
}

// El subdominio de la tienda puede ser otro origen: se postea al origen real
// del iframe (mismo criterio que el lienzo del Studio).
export function originOf(src) {
  try { return new URL(src, window.location.href).origin } catch { return window.location.origin }
}
