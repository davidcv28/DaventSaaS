<script setup>
import { ref, computed, onMounted } from 'vue'
import { feedApi } from '../../api/feed.api.js'
import { extractApiError } from '../../api/http.js'
import { apiErr, fmtDateTime } from './commerce/shared.js'
import AppIcon from '../AppIcon.vue'
import AlertMessage from '../AlertMessage.vue'

// Panel del dueño para el dominio Feed ("Novedades" en la web pública).
// CRUD de posts (texto, foto, video, embed de redes y encuesta) en flujo
// de dos pasos para media (create → uploadMedia) + bandeja de moderación
// de comentarios. Beneficio has_feed: un 403 del list muestra el aviso
// del plan con el detail que manda el backend.

const loading = ref(true)
const loadErr = ref('')
const lockedMsg = ref('') // detail del 403 (plan sin has_feed)

const posts = ref([])
const notice = ref('')
const lastError = ref('')

// ---- Tipos de post: chips del form con icono ----
const KINDS = [
  { id: 'text',  label: 'Texto',    icon: 'type' },
  { id: 'image', label: 'Foto',     icon: 'image' },
  { id: 'video', label: 'Video',    icon: 'lucide:video' },
  { id: 'embed', label: 'De redes', icon: 'external-link' },
  { id: 'poll',  label: 'Encuesta', icon: 'lucide:chart-line' },
]
const KIND_LABEL = Object.fromEntries(KINDS.map((k) => [k.id, k.label]))

const MEDIA_ACCEPT = {
  image: 'image/*',
  video: 'video/mp4,video/webm,video/quicktime',
}
const PROVIDER_LABEL = {
  youtube: 'YouTube', tiktok: 'TikTok', instagram: 'Instagram',
  facebook: 'Facebook', x: 'X',
}

// ---- Form de alta / edición ----
const blankForm = () => ({
  kind: 'text', caption: '', embed_url: '',
  pollOptions: ['', ''],
})
const form = ref(blankForm())
const formOpen = ref(false)
const editing = ref(null) // post en edición (o null = alta)
const mediaFile = ref(null)
const fileInput = ref(null)
const saving = ref(false)
const formErr = ref('')

// En edición de encuesta: el backend reemplaza TODAS las opciones y los
// votos se pierden — por eso el aviso va siempre visible al editar una.
const pollDirty = computed(() => {
  if (!editing.value || editing.value.kind !== 'poll') return false
  const current = (editing.value.poll?.options || []).map((o) => o.label)
  const next = form.value.pollOptions.map((o) => o.trim()).filter(Boolean)
  return current.length !== next.length || current.some((l, i) => l !== next[i])
})

const canSubmit = computed(() => {
  const f = form.value
  const cap = f.caption.trim()
  if (f.kind === 'text') return Boolean(cap)
  if (f.kind === 'poll') return Boolean(cap) && f.pollOptions.filter((o) => o.trim()).length >= 2
  if (f.kind === 'embed') return Boolean(f.embed_url.trim())
  // image/video: caption opcional; en el alta el archivo puede subirse después.
  return true
})

function openCreate() {
  editing.value = null
  form.value = blankForm()
  mediaFile.value = null
  formErr.value = ''
  formOpen.value = true
}

function startEdit(post) {
  editing.value = post
  form.value = {
    kind: post.kind,
    caption: post.caption || '',
    embed_url: post.embed?.url || '',
    pollOptions: post.kind === 'poll'
      ? (post.poll?.options || []).map((o) => o.label)
      : ['', ''],
  }
  mediaFile.value = null
  formErr.value = ''
  formOpen.value = true
}

function cancelForm() {
  formOpen.value = false
  editing.value = null
  mediaFile.value = null
  formErr.value = ''
}

function setKind(kind) {
  // En edición el tipo no se cambia (el backend no lo permite).
  if (editing.value) return
  form.value.kind = kind
  mediaFile.value = null
}

function onFilePicked(e) {
  mediaFile.value = e.target.files?.[0] || null
}

function addOption() {
  if (form.value.pollOptions.length < 6) form.value.pollOptions.push('')
}
function removeOption(i) {
  if (form.value.pollOptions.length > 2) form.value.pollOptions.splice(i, 1)
}

function buildPayload() {
  const f = form.value
  const payload = { kind: f.kind, caption: f.caption.trim() }
  if (f.kind === 'embed') payload.embed_url = f.embed_url.trim()
  if (f.kind === 'poll') {
    // Solo se mandan si cambiaron respecto del post: reemplaza todas y
    // los votos se pierden (aviso visible en el form).
    if (!editing.value || pollDirty.value) {
      payload.options = f.pollOptions.map((o) => o.trim()).filter(Boolean)
    }
  }
  return payload
}

async function savePost() {
  if (!canSubmit.value || saving.value) return
  saving.value = true
  formErr.value = ''
  lastError.value = ''
  notice.value = ''
  try {
    if (editing.value) {
      const { item } = await feedApi.update(editing.value.id, buildPayload())
      const i = posts.value.findIndex((p) => p.id === item.id)
      if (i !== -1) posts.value[i] = item
      notice.value = 'Publicación actualizada.'
    } else {
      const { item } = await feedApi.create(buildPayload())
      // Alta en dos pasos para foto/video: el archivo sube recién ahora
      // que el post ya existe (el backend necesita el id para el media).
      if (mediaFile.value && (item.kind === 'image' || item.kind === 'video')) {
        try {
          const res = await feedApi.uploadMedia(item.id, mediaFile.value)
          posts.value.unshift(res.item)
        } catch (e) {
          posts.value.unshift(item)
          lastError.value = `Se creó la publicación pero no se pudo subir el archivo: ${apiErr(e)}`
          cancelForm()
          return
        }
      } else {
        posts.value.unshift(item)
      }
      notice.value = 'Publicación creada.'
    }
    cancelForm()
  } catch (e) {
    formErr.value = apiErr(e)
  } finally {
    saving.value = false
  }
}

async function togglePublish(post) {
  lastError.value = ''
  notice.value = ''
  try {
    const { item } = await feedApi.update(post.id, { is_published: !post.is_published })
    const i = posts.value.findIndex((p) => p.id === item.id)
    if (i !== -1) posts.value[i] = item
    notice.value = item.is_published ? 'Publicación visible en tu web.' : 'Publicación despublicada.'
  } catch (e) {
    lastError.value = apiErr(e)
  }
}

async function removePost(post) {
  if (!window.confirm('¿Borrar esta publicación? Se eliminan también sus comentarios y votos.')) return
  lastError.value = ''
  notice.value = ''
  try {
    await feedApi.remove(post.id)
    posts.value = posts.value.filter((p) => p.id !== post.id)
    comments.value = comments.value.filter((c) => c.post !== post.id)
    if (commentsFilter.value === post.id) commentsFilter.value = null
    notice.value = 'Publicación eliminada.'
  } catch (e) {
    lastError.value = apiErr(e)
  }
}

async function changeMedia(post, e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  lastError.value = ''
  notice.value = ''
  try {
    const { item } = await feedApi.uploadMedia(post.id, file)
    const i = posts.value.findIndex((p) => p.id === item.id)
    if (i !== -1) posts.value[i] = item
    notice.value = 'Archivo actualizado.'
  } catch (err) {
    lastError.value = apiErr(err)
  }
}

async function removeMedia(post) {
  if (!window.confirm('¿Quitar el archivo de esta publicación?')) return
  lastError.value = ''
  notice.value = ''
  try {
    const { item } = await feedApi.removeMedia(post.id)
    const i = posts.value.findIndex((p) => p.id === item.id)
    if (i !== -1) posts.value[i] = item
    notice.value = 'Archivo eliminado.'
  } catch (e) {
    lastError.value = apiErr(e)
  }
}

// ---- Comentarios ----
const comments = ref([])
const commentsLoading = ref(false)
const commentsErr = ref('')
const commentsFilter = ref(null) // postId o null = todos

const visibleComments = computed(() =>
  commentsFilter.value == null
    ? comments.value
    : comments.value.filter((c) => c.post === commentsFilter.value))

function postOf(comment) {
  return posts.value.find((p) => p.id === comment.post) || null
}

async function loadComments(postId = null) {
  commentsLoading.value = true
  commentsErr.value = ''
  try {
    const { comments: list } = await feedApi.comments(postId)
    comments.value = list
  } catch (e) {
    commentsErr.value = apiErr(e)
  } finally {
    commentsLoading.value = false
  }
}

function filterComments(postId) {
  commentsFilter.value = commentsFilter.value === postId ? null : postId
}

async function toggleHidden(comment) {
  lastError.value = ''
  notice.value = ''
  try {
    const { item } = await feedApi.moderateComment(comment.id, !comment.is_hidden)
    const i = comments.value.findIndex((c) => c.id === item.id)
    if (i !== -1) comments.value[i] = item
    notice.value = item.is_hidden ? 'Comentario oculto en tu web.' : 'Comentario visible de nuevo.'
  } catch (e) {
    lastError.value = apiErr(e)
  }
}

async function removeComment(comment) {
  if (!window.confirm('¿Eliminar este comentario? Esta acción no se puede deshacer.')) return
  lastError.value = ''
  notice.value = ''
  try {
    await feedApi.removeComment(comment.id)
    comments.value = comments.value.filter((c) => c.id !== comment.id)
    notice.value = 'Comentario eliminado.'
  } catch (e) {
    lastError.value = apiErr(e)
  }
}

// ---- Carga inicial ----
async function loadAll() {
  loading.value = true
  loadErr.value = ''
  lockedMsg.value = ''
  try {
    const data = await feedApi.list()
    posts.value = data.posts || []
    loadComments()
  } catch (e) {
    // 403 = el plan no incluye has_feed: el detail explica desde qué plan está.
    if (extractApiError(e)?.status === 403) lockedMsg.value = apiErr(e)
    else loadErr.value = apiErr(e)
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<template>
  <div>
    <AlertMessage v-if="notice" kind="success" :message="notice" />
    <AlertMessage v-if="lastError" kind="error" :message="lastError" />

    <!-- Loading inicial -->
    <div v-if="loading" class="card">
      <div class="empty-mini"><span class="spinner spinner-brand" aria-hidden="true"></span><p>Cargando tus publicaciones…</p></div>
    </div>

    <!-- Plan sin el beneficio has_feed -->
    <div v-else-if="lockedMsg" class="empty">
      <div class="empty-icon"><AppIcon name="lock" :size="28" /></div>
      <h3>Novedades está disponible desde el plan Premium</h3>
      <p>{{ lockedMsg }}</p>
      <div class="btn-row" style="justify-content:center">
        <button type="button" class="btn btn-auto" @click="loadAll"><AppIcon name="refresh" :size="15" /> Reintentar</button>
      </div>
    </div>

    <!-- Error general con reintento -->
    <div v-else-if="loadErr" class="empty">
      <div class="empty-icon"><AppIcon name="circle-alert" :size="28" /></div>
      <h3>No pudimos cargar tu feed</h3>
      <p>{{ loadErr }}</p>
      <div class="btn-row" style="justify-content:center">
        <button type="button" class="btn btn-auto" @click="loadAll"><AppIcon name="refresh" :size="15" /> Reintentar</button>
      </div>
    </div>

    <template v-else>
      <!-- ===== Nueva publicación ===== -->
      <section class="card">
        <div class="feed-cardhead">
          <h3><AppIcon name="lucide:newspaper" :size="18" /> Publicaciones</h3>
          <button v-if="!formOpen" type="button" class="btn btn-auto" @click="openCreate"><AppIcon name="plus" :size="15" /> Nueva publicación</button>
        </div>

        <!-- Form de alta / edición -->
        <form v-if="formOpen" class="feed-form" @submit.prevent="savePost">
          <!-- Selector de tipo: solo en el alta -->
          <div class="feed-kinds" role="group" aria-label="Tipo de publicación">
            <button
              v-for="k in KINDS" :key="k.id" type="button"
              class="feed-kind" :class="{ on: form.kind === k.id }"
              :disabled="Boolean(editing)"
              @click="setKind(k.id)"
            ><AppIcon :name="k.icon" :size="15" /> {{ k.label }}</button>
          </div>

          <label class="field">
            <span class="field-label">{{ form.kind === 'poll' ? 'Pregunta de la encuesta' : 'Texto de la publicación' }}<span v-if="form.kind !== 'text' && form.kind !== 'poll'" class="hint"> (opcional)</span></span>
            <textarea
              v-model="form.caption" class="textarea" rows="3" maxlength="2000"
              :placeholder="form.kind === 'poll' ? '¿Qué querés preguntarle a tus clientes?' : 'Contales algo nuevo…'"
            ></textarea>
          </label>

          <!-- Foto / video: archivo opcional (sube después de crear) -->
          <div v-if="form.kind === 'image' || form.kind === 'video'" class="field">
            <span class="field-label">{{ form.kind === 'image' ? 'Foto' : 'Video' }}</span>
            <input
              ref="fileInput" type="file" class="sr-only"
              :accept="MEDIA_ACCEPT[form.kind]" @change="onFilePicked"
            />
            <div class="feed-file">
              <button type="button" class="btn ghost btn-auto" @click="fileInput?.click()"><AppIcon name="upload" :size="15" /> {{ mediaFile ? 'Cambiar archivo' : 'Elegir archivo' }}</button>
              <span class="hint">{{ mediaFile ? mediaFile.name : 'Podés publicar sin archivo y subirlo después.' }}</span>
            </div>
            <!-- En edición: el post puede tener media cargada -->
            <div v-if="editing?.media_url" class="feed-file">
              <span class="hint">Ya tiene un archivo cargado.</span>
              <button type="button" class="btn ghost btn-auto" @click="removeMedia(editing)"><AppIcon name="trash" :size="14" /> Quitar archivo</button>
            </div>
          </div>

          <!-- Embed de redes -->
          <label v-if="form.kind === 'embed'" class="field">
            <span class="field-label">Link de la publicación</span>
            <input v-model="form.embed_url" class="input" type="url" maxlength="500" placeholder="https://… (TikTok, YouTube, Instagram, Facebook o X)" />
            <span class="hint">Pegá el link público del post o video: lo embebemos en tu feed.</span>
          </label>

          <!-- Encuesta: 2 a 6 opciones -->
          <div v-if="form.kind === 'poll'" class="field">
            <span class="field-label">Opciones (de 2 a 6)</span>
            <div class="feed-opts">
              <div v-for="(opt, i) in form.pollOptions" :key="i" class="feed-opt">
                <input v-model="form.pollOptions[i]" class="input" maxlength="80" :placeholder="`Opción ${i + 1}`" :aria-label="`Opción ${i + 1}`" />
                <button type="button" class="icon-btn danger" :disabled="form.pollOptions.length <= 2" :aria-label="`Quitar opción ${i + 1}`" @click="removeOption(i)"><AppIcon name="x" :size="14" /></button>
              </div>
            </div>
            <button v-if="form.pollOptions.length < 6" type="button" class="btn ghost btn-auto" @click="addOption"><AppIcon name="plus" :size="14" /> Agregar opción</button>
            <p v-if="editing && editing.kind === 'poll'" class="hint feed-warn">
              <AppIcon name="triangle-alert" :size="13" /> Al guardar, las opciones reemplazan a todas las actuales y los votos se reinician.
            </p>
          </div>

          <AlertMessage v-if="formErr" kind="error" :message="formErr" />
          <div class="btn-row">
            <button type="submit" class="btn btn-auto" :disabled="!canSubmit || saving">
              {{ saving ? 'Guardando…' : (editing ? 'Guardar cambios' : 'Publicar') }}
            </button>
            <button type="button" class="btn ghost btn-auto" :disabled="saving" @click="cancelForm">Cancelar</button>
          </div>
        </form>

        <!-- Lista de posts -->
        <div v-if="!posts.length && !formOpen" class="empty" style="padding:28px 12px">
          <div class="empty-icon"><AppIcon name="lucide:newspaper" :size="26" /></div>
          <h3>Todavía no publicaste nada</h3>
          <p>Creá tu primera publicación: texto, foto, video, un post de tus redes o una encuesta.</p>
        </div>

        <ul v-if="posts.length" class="feed-posts">
          <li v-for="post in posts" :key="post.id" class="feed-post" :class="{ off: !post.is_published }">
            <div class="feed-post-head">
              <span class="pill muted">{{ KIND_LABEL[post.kind] || post.kind }}</span>
              <span v-if="!post.is_published" class="pill warn">Despublicado</span>
              <span v-if="post.embed" class="pill">{{ PROVIDER_LABEL[post.embed.provider] || 'Embed' }}</span>
              <time class="feed-when">{{ fmtDateTime(post.created_at) }}</time>
              <div class="feed-post-actions">
                <button
                  type="button" class="icon-btn"
                  :title="post.is_published ? 'Despublicar' : 'Publicar'"
                  :aria-label="post.is_published ? 'Despublicar' : 'Publicar'"
                  @click="togglePublish(post)"
                ><AppIcon :name="post.is_published ? 'eye-off' : 'eye'" :size="15" /></button>
                <button type="button" class="icon-btn" title="Editar" aria-label="Editar" @click="startEdit(post)"><AppIcon name="pencil" :size="15" /></button>
                <button type="button" class="icon-btn danger" title="Borrar" aria-label="Borrar" @click="removePost(post)"><AppIcon name="trash" :size="15" /></button>
              </div>
            </div>

            <p v-if="post.caption" class="feed-caption">{{ post.caption }}</p>

            <!-- Preview de media -->
            <figure v-if="post.media_kind === 'image' && post.media_url" class="feed-media">
              <img :src="post.media_url" :alt="post.caption || 'Imagen de la publicación'" loading="lazy" />
            </figure>
            <div v-else-if="post.media_kind === 'video' && post.media_url" class="feed-media">
              <video :src="post.media_url" controls preload="metadata"></video>
            </div>
            <div v-else-if="(post.kind === 'image' || post.kind === 'video') && !post.media_url" class="feed-media-pending">
              <AppIcon :name="post.kind === 'image' ? 'image' : 'lucide:video'" :size="16" />
              <span>Sin archivo todavía</span>
              <label class="btn ghost btn-auto feed-upload-lbl">
                <input type="file" class="sr-only" :accept="MEDIA_ACCEPT[post.kind]" @change="changeMedia(post, $event)" />
                <AppIcon name="upload" :size="14" /> Subir
              </label>
            </div>

            <!-- Embed -->
            <a v-if="post.embed" class="feed-embed-link" :href="post.embed.url" target="_blank" rel="noopener noreferrer">
              <AppIcon name="external-link" :size="15" /> Ver en {{ PROVIDER_LABEL[post.embed.provider] || 'la red' }}
            </a>

            <!-- Encuesta: opciones con resultados -->
            <div v-if="post.poll" class="feed-poll">
              <div v-for="opt in post.poll.options" :key="opt.id" class="feed-poll-row">
                <span class="feed-poll-bar" :style="{ width: (opt.percent || 0) + '%' }"></span>
                <span class="feed-poll-label">{{ opt.label }}</span>
                <span class="feed-poll-pct">{{ opt.percent || 0 }}%</span>
              </div>
              <p class="hint" style="margin:0">{{ post.poll.total }} {{ post.poll.total === 1 ? 'voto' : 'votos' }}</p>
            </div>

            <div class="feed-post-foot">
              <span class="feed-count"><AppIcon name="heart" :size="14" /> {{ post.likes_count }}</span>
              <button type="button" class="feed-count feed-count-btn" :class="{ on: commentsFilter === post.id }" @click="filterComments(post.id)">
                <AppIcon name="message-circle" :size="14" /> {{ post.comments_count }} comentarios
              </button>
            </div>
          </li>
        </ul>
      </section>

      <!-- ===== Comentarios ===== -->
      <section class="card" style="margin-top:14px">
        <div class="feed-cardhead">
          <h3><AppIcon name="message-circle" :size="18" /> Comentarios</h3>
          <div class="btn-row" style="margin:0">
            <button v-if="commentsFilter != null" type="button" class="btn ghost btn-auto" @click="commentsFilter = null">Ver todos</button>
            <button type="button" class="icon-btn" title="Recargar" aria-label="Recargar comentarios" :disabled="commentsLoading" @click="loadComments()"><AppIcon name="refresh" :size="15" /></button>
          </div>
        </div>
        <p v-if="commentsFilter != null" class="hint" style="margin:-6px 0 10px">
          Mostrando solo los comentarios de «{{ postOf({ post: commentsFilter })?.caption?.slice(0, 60) || 'la publicación' }}».
        </p>

        <div v-if="commentsLoading" class="empty-mini"><span class="spinner spinner-brand" aria-hidden="true"></span><p>Cargando comentarios…</p></div>
        <AlertMessage v-else-if="commentsErr" kind="error" :message="commentsErr" />
        <div v-else-if="!visibleComments.length" class="empty-mini"><p>Sin comentarios{{ commentsFilter != null ? ' en esta publicación' : ' todavía' }}.</p></div>

        <ul v-else class="feed-comments">
          <li v-for="c in visibleComments" :key="c.id" class="feed-comment" :class="{ off: c.is_hidden }">
            <span class="feed-cava" aria-hidden="true">{{ c.avatar }}</span>
            <div class="feed-cbody">
              <p class="feed-cmeta">
                <strong>{{ c.author }}</strong>
                <span v-if="c.email" class="feed-cemail">{{ c.email }}</span>
                <span v-if="c.is_hidden" class="pill danger">Oculto</span>
              </p>
              <p class="feed-ctext">{{ c.body }}</p>
              <p class="feed-cfoot">
                <span v-if="postOf(c)">En «{{ postOf(c).caption?.slice(0, 50) || 'publicación' }}»</span>
                <time>{{ fmtDateTime(c.created_at) }}</time>
              </p>
            </div>
            <div class="feed-cactions">
              <button
                type="button" class="icon-btn"
                :title="c.is_hidden ? 'Mostrar' : 'Ocultar'"
                :aria-label="c.is_hidden ? 'Mostrar comentario' : 'Ocultar comentario'"
                @click="toggleHidden(c)"
              ><AppIcon :name="c.is_hidden ? 'eye' : 'eye-off'" :size="15" /></button>
              <button type="button" class="icon-btn danger" title="Eliminar" aria-label="Eliminar comentario" @click="removeComment(c)"><AppIcon name="trash" :size="15" /></button>
            </div>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

<style scoped>
.field-label { font-size: 12.5px; font-weight: 600; color: var(--ink-2); display: block; margin-bottom: 5px; }
.hint { font-size: 12.5px; color: var(--muted); }
.field { display: block; margin-bottom: 12px; }

.feed-cardhead { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }
.feed-cardhead h3 { margin: 0; }

.feed-form { border: 1px solid var(--line); border-radius: var(--radius, 14px); padding: 14px; margin-bottom: 14px; display: flex; flex-direction: column; gap: 2px; }
.feed-kinds { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; }
.feed-kind {
  display: inline-flex; align-items: center; gap: 6px; padding: 7px 13px;
  border: 1px solid var(--line); border-radius: 999px; background: transparent;
  color: var(--ink-2); font: inherit; font-size: 13px; font-weight: 600; cursor: pointer;
  transition: border-color .15s, background .15s, color .15s;
}
.feed-kind:hover { border-color: var(--accent); }
.feed-kind.on { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 10%, transparent); color: var(--ink); }
.feed-kind:disabled { opacity: .55; cursor: default; }

.feed-file { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }

.feed-opts { display: grid; gap: 8px; margin-bottom: 8px; }
.feed-opt { display: flex; align-items: center; gap: 8px; }
.feed-opt .input { flex: 1; }
.feed-warn { display: flex; align-items: center; gap: 6px; color: var(--muted); margin: 8px 0 0; }

.feed-posts { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }
.feed-post { border: 1px solid var(--line); border-radius: var(--radius, 14px); padding: 13px 14px; display: flex; flex-direction: column; gap: 10px; }
.feed-post.off { opacity: .65; }
.feed-post-head { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.feed-when { font-size: 12px; color: var(--muted); margin-left: auto; }
.feed-post-actions { display: flex; gap: 4px; }
.feed-caption { margin: 0; font-size: 14.5px; line-height: 1.55; color: var(--ink); white-space: pre-line; overflow-wrap: anywhere; }

.feed-media { margin: 0; border-radius: 12px; overflow: hidden; border: 1px solid var(--line); }
.feed-media img, .feed-media video { display: block; width: 100%; max-height: 380px; object-fit: contain; background: #000; }
.feed-media-pending {
  display: flex; align-items: center; gap: 8px; padding: 10px 12px;
  border: 1.5px dashed var(--line-strong); border-radius: 12px;
  font-size: 13px; color: var(--muted);
}
.feed-upload-lbl { cursor: pointer; }

.feed-embed-link {
  display: inline-flex; align-items: center; gap: 8px; padding: 10px 13px;
  border: 1px solid var(--line); border-radius: 12px;
  color: var(--accent, var(--brand-ink)); text-decoration: none; font-weight: 600; font-size: 13.5px;
  width: fit-content;
}
.feed-embed-link:hover { border-color: var(--accent); }

.feed-poll { display: grid; gap: 6px; }
.feed-poll-row {
  position: relative; display: flex; justify-content: space-between; gap: 10px;
  padding: 8px 12px; border: 1px solid var(--line); border-radius: 10px; overflow: hidden; font-size: 13.5px;
}
.feed-poll-bar { position: absolute; inset: 0 auto 0 0; background: color-mix(in srgb, var(--accent, #4f46e5) 15%, transparent); pointer-events: none; }
.feed-poll-label { position: relative; color: var(--ink); overflow-wrap: anywhere; }
.feed-poll-pct { position: relative; color: var(--muted); font-variant-numeric: tabular-nums; }

.feed-post-foot { display: flex; align-items: center; gap: 14px; }
.feed-count { display: inline-flex; align-items: center; gap: 5px; font-size: 13px; color: var(--muted); }
.feed-count-btn { background: none; border: 0; padding: 0; font: inherit; cursor: pointer; }
.feed-count-btn:hover, .feed-count-btn.on { color: var(--accent, var(--brand-ink)); }

.feed-comments { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.feed-comment {
  display: flex; gap: 10px; align-items: flex-start;
  border: 1px solid var(--line); border-radius: 12px; padding: 11px 12px;
}
.feed-comment.off { opacity: .6; }
.feed-cava {
  flex: none; width: 34px; height: 34px; border-radius: 50%;
  display: grid; place-items: center;
  background: color-mix(in srgb, var(--accent, #4f46e5) 12%, transparent);
  color: var(--ink); font-weight: 700; font-size: 13px; text-transform: uppercase;
}
.feed-cbody { flex: 1; min-width: 0; }
.feed-cmeta { margin: 0 0 2px; font-size: 13px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.feed-cemail { color: var(--muted); font-size: 12px; }
.feed-ctext { margin: 0; font-size: 14px; color: var(--ink); overflow-wrap: anywhere; white-space: pre-line; }
.feed-cfoot { margin: 4px 0 0; font-size: 12px; color: var(--muted); display: flex; gap: 10px; flex-wrap: wrap; }
.feed-cactions { display: flex; gap: 4px; flex: none; }
</style>
