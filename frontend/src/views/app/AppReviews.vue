<script setup>
// App nativa — Opiniones: moderación de valoraciones/comentarios de
// visitantes (GET /api/reviews/). El dueño responde (PATCH reply) o
// elimina (DELETE). La opinión ajena no se edita — PATCH simple da 405.
import { onMounted, ref } from 'vue'
import { useCatalogStore } from '../../stores/catalog.store.js'
import AppIcon from '../../components/AppIcon.vue'
import AppButton from '../../components/AppButton.vue'

const catalog = useCatalogStore()
const loading = ref(true)

onMounted(async () => {
  loading.value = true
  await catalog.loadReviews()
  loading.value = false
})

const replying = ref(null) // id de la opinión con el cuadro abierto
const replyText = ref('')
const replyBusy = ref(false)

function openReply(r) {
  replying.value = replying.value === r.id ? null : r.id
  replyText.value = r.owner_reply || ''
}

async function sendReply(r) {
  replyBusy.value = true
  const ok = await catalog.replyReview(r.id, replyText.value.trim())
  replyBusy.value = false
  if (ok) replying.value = null
}

async function remove(r) {
  if (!window.confirm('¿Eliminar esta opinión? Se quita de tu web.')) return
  await catalog.removeReview(r.id)
}

const fmtDate = (iso) => {
  const d = new Date(iso || '')
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('es-AR', { day: 'numeric', month: 'short', year: 'numeric' })
}
</script>

<template>
  <section>
    <div class="ar-head">
      <h2 class="ar-title">Opiniones</h2>
      <span class="ar-count">{{ catalog.reviews.length }}</span>
    </div>
    <p class="ar-sub">Lo que dicen los visitantes de tus productos en tu web.</p>

    <div v-if="loading" class="ar-empty">Cargando…</div>
    <div v-else-if="!catalog.reviews.length" class="ar-empty">
      <AppIcon name="message-circle" :size="26" />
      <p>Todavía no hay opiniones. Aparecen cuando un visitante comenta un producto en tu web.</p>
    </div>

    <ul class="ar-list">
      <li v-for="r in catalog.reviews" :key="r.id" class="ar-card">
        <div class="ar-top">
          <span class="ar-vote" :class="{ neg: r.is_positive === false }">
            <AppIcon :name="r.is_positive === false ? 'thumbs-down' : 'thumbs-up'" :size="14" />
            {{ r.is_positive === false ? 'No le gustó' : 'Le gustó' }}
          </span>
          <span class="ar-date">{{ fmtDate(r.created_at) }}</span>
        </div>
        <p class="ar-prod">{{ r.product_name }}</p>
        <p v-if="r.text" class="ar-text">“{{ r.text }}”</p>
        <p class="ar-who">{{ [r.name, r.surname].filter(Boolean).join(' ') || 'Visitante' }}</p>

        <div v-if="r.owner_reply" class="ar-reply">
          <span class="ar-reply-tag">Tu respuesta</span>
          <p class="ar-reply-text">{{ r.owner_reply }}</p>
        </div>

        <div v-if="replying === r.id" class="ar-editor">
          <textarea v-model="replyText" class="textarea" rows="2" maxlength="600" placeholder="Escribí tu respuesta pública…"></textarea>
          <div class="btn-row">
            <AppButton :loading="replyBusy" @click="sendReply(r)">Publicar respuesta</AppButton>
            <button v-if="r.owner_reply && !replyText" type="button" class="btn ghost btn-auto" @click="sendReply(r)">Quitar respuesta</button>
          </div>
        </div>

        <div class="ar-actions">
          <button type="button" class="ar-action" @click="openReply(r)">
            <AppIcon name="send" :size="14" /> {{ r.owner_reply ? 'Editar respuesta' : 'Responder' }}
          </button>
          <button type="button" class="ar-action danger" @click="remove(r)">
            <AppIcon name="trash" :size="14" /> Eliminar
          </button>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.ar-head { display: flex; align-items: baseline; gap: 8px; }
.ar-title { font-size: 20px; font-weight: 800; margin: 0; }
.ar-count { font-size: 12px; font-weight: 700; color: var(--muted, #6b6478); background: var(--card, #fff); border: 1px solid var(--line, #e5e5ef); border-radius: 999px; padding: 1px 8px; }
.ar-sub { font-size: 13px; color: var(--muted, #6b6478); margin: 4px 0 14px; }
.ar-empty {
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  padding: 48px 16px; text-align: center; color: var(--muted, #6b6478); font-size: 14px;
}
.ar-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.ar-card {
  background: var(--card, #fff); border: 1px solid var(--line, #e5e5ef);
  border-radius: 14px; padding: 12px 14px;
}
.ar-top { display: flex; justify-content: space-between; align-items: center; }
.ar-vote {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11.5px; font-weight: 700; color: #059669;
}
.ar-vote.neg { color: #dc2626; }
.ar-date { font-size: 11.5px; color: var(--muted, #6b6478); }
.ar-prod { font-size: 13px; font-weight: 700; margin: 8px 0 2px; }
.ar-text { font-size: 14px; margin: 2px 0; color: var(--ink, #17141f); }
.ar-who { font-size: 12px; color: var(--muted, #6b6478); margin: 4px 0 0; }
.ar-reply {
  margin-top: 10px; padding: 8px 10px; border-left: 3px solid var(--brand-500, #4f46e5);
  background: var(--bg, #f6f6fb); border-radius: 0 10px 10px 0;
}
.ar-reply-tag { font-size: 10.5px; font-weight: 700; color: var(--brand-500, #4f46e5); text-transform: uppercase; letter-spacing: .04em; }
.ar-reply-text { font-size: 13px; margin: 3px 0 0; }
.ar-editor { margin-top: 10px; }
.ar-actions { display: flex; gap: 14px; margin-top: 10px; }
.ar-action {
  display: inline-flex; align-items: center; gap: 5px;
  border: 0; background: none; padding: 4px 0; cursor: pointer;
  font-size: 13px; font-weight: 600; color: var(--brand-500, #4f46e5);
}
.ar-action.danger { color: #dc2626; }
</style>
