<script setup>
// Página "Novedades" de la web pública (beneficio has_feed, Estándar+):
// feed social de la tienda — posts de texto, fotos, videos propios,
// publicaciones embebidas de redes (TikTok/YouTube/Instagram/Facebook/X)
// y encuestas. La lectura es anónima; likear, comentar y votar piden
// cuenta de comprador (customer JWT — modal global de auth).
import { computed, inject, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { feedApi } from '../api/feed.api.js'
import { storeHostSlug } from '../config/env.js'
import { useCartStore } from '../stores/cart.store.js'
import { useCustomerStore } from '../stores/customer.store.js'

const ctx = inject('storePage')
const cartStore = useCartStore()
const customerStore = useCustomerStore()

const slug = computed(() => ctx?.slug?.value || '')
const store = computed(() => ctx?.store?.value || null)
const enabled = computed(() => Boolean(store.value?.feed_enabled))
const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${slug.value}` }))

const authed = computed(() => customerStore.isAuthenticated)
const posts = ref([])
const status = ref('loading') // loading | success | error
const sessionReady = ref(false)

const comments = reactive({})     // postId -> { status, items, open, draft, busy, error }
const likeBusy = reactive({})
const voteBusy = reactive({})

const PROVIDER_LABELS = {
  youtube: 'YouTube', tiktok: 'TikTok', instagram: 'Instagram',
  facebook: 'Facebook', x: 'X'
}

async function load() {
  status.value = 'loading'
  try {
    const data = await feedApi.publicList(slug.value, authed.value)
    posts.value = data.posts || []
    status.value = 'success'
  } catch {
    status.value = 'error'
  }
}

function openAuth() {
  cartStore.openAuth('login', { route: { path: route_path() } })
}
function route_path() {
  return storeHostSlug ? '/novedades' : `/${slug.value}/novedades`
}

async function toggleLike(post) {
  if (!authed.value) return openAuth()
  if (likeBusy[post.id]) return
  likeBusy[post.id] = true
  try {
    const data = await feedApi.like(slug.value, post.id)
    post.likes_count = data.likes_count
    post.my_like = data.liked
  } catch { /* el toast global de sesión cubre el 401 */ } finally {
    likeBusy[post.id] = false
  }
}

async function vote(post, option) {
  if (!authed.value) return openAuth()
  if (voteBusy[post.id]) return
  voteBusy[post.id] = true
  try {
    post.poll = await feedApi.vote(slug.value, post.id, option.id)
  } catch { /* 401 lo cubre la sesión */ } finally {
    voteBusy[post.id] = false
  }
}

function commentState(postId) {
  if (!comments[postId]) comments[postId] = { status: 'idle', items: [], open: false, draft: '', busy: false, error: '' }
  return comments[postId]
}

async function toggleComments(post) {
  const c = commentState(post.id)
  c.open = !c.open
  if (c.open && c.status === 'idle') {
    c.status = 'loading'
    try {
      const data = await feedApi.publicComments(slug.value, post.id, authed.value)
      c.items = data.comments || []
      c.status = 'success'
    } catch {
      c.status = 'error'
    }
  }
}

async function sendComment(post) {
  if (!authed.value) return openAuth()
  const c = commentState(post.id)
  const body = (c.draft || '').trim()
  if (!body || c.busy) return
  c.busy = true
  c.error = ''
  try {
    const data = await feedApi.comment(slug.value, post.id, body)
    c.items.push(data.item)
    c.draft = ''
    post.comments_count++
  } catch (e) {
    c.error = 'No pudimos publicar tu comentario. Probá de nuevo.'
  } finally {
    c.busy = false
  }
}

async function removeComment(post, comment) {
  try {
    await feedApi.removeMyComment(slug.value, comment.id)
    const c = commentState(post.id)
    c.items = c.items.filter((i) => i.id !== comment.id)
    post.comments_count = Math.max(0, post.comments_count - 1)
  } catch { /* noop */ }
}

function whenLabel(iso) {
  if (!iso) return ''
  const then = new Date(iso).getTime()
  const diff = Date.now() - then
  const min = Math.floor(diff / 60000)
  if (min < 1) return 'ahora'
  if (min < 60) return `hace ${min} min`
  const h = Math.floor(min / 60)
  if (h < 24) return `hace ${h} h`
  const d = Math.floor(h / 24)
  if (d < 30) return `hace ${d} d`
  return new Date(iso).toLocaleDateString('es-AR', { day: 'numeric', month: 'short', year: 'numeric' })
}

onMounted(async () => {
  sessionReady.value = await customerStore.ensureSession().then(() => true).catch(() => true)
  if (enabled.value) load()
})
watch(authed, () => { if (status.value === 'success') load() })
</script>

<template>
  <div v-if="!enabled" class="sp-state sp-state-page">
    <span class="sp-state-icon"><AppIcon name="lucide:newspaper" :size="26" /></span>
    <h1>Novedades no disponibles</h1>
    <p>Esta tienda no tiene página de novedades por ahora.</p>
    <RouterLink :to="homeTo" class="sp-btn">Volver al inicio</RouterLink>
  </div>

  <main v-else class="feed-page">
    <header class="feed-head">
      <h1>Novedades</h1>
      <p>Lo último de {{ store?.business_name || 'la tienda' }}: fotos, videos y encuestas.</p>
    </header>

    <div v-if="status === 'loading'" class="feed-state"><span class="spinner spinner-brand"></span><p>Cargando publicaciones…</p></div>
    <div v-else-if="status === 'error'" class="feed-state">
      <p>No pudimos cargar las novedades.</p>
      <button type="button" class="sp-btn ghost" @click="load">Reintentar</button>
    </div>
    <div v-else-if="!posts.length" class="feed-state">
      <span class="feed-state-icon"><AppIcon name="lucide:newspaper" :size="28" /></span>
      <p>Todavía no hay publicaciones. Volvé pronto.</p>
    </div>

    <ol v-else class="feed-list">
      <li v-for="post in posts" :key="post.id" class="feed-card">
        <p v-if="post.caption" class="feed-caption">{{ post.caption }}</p>

        <figure v-if="post.media_kind === 'image' && post.media_url" class="feed-media">
          <img :src="post.media_url" :alt="post.caption || 'Imagen de la publicación'" loading="lazy" />
        </figure>
        <div v-else-if="post.media_kind === 'video' && post.media_url" class="feed-media">
          <video :src="post.media_url" controls playsinline preload="metadata"></video>
        </div>

        <div v-if="post.embed" class="feed-embed">
          <iframe
            v-if="post.embed.iframe"
            :src="post.embed.iframe"
            class="feed-embed-frame"
            :class="`is-${post.embed.provider}`"
            loading="lazy"
            allowfullscreen
            referrerpolicy="strict-origin-when-cross-origin"
            :title="`Publicación de ${PROVIDER_LABELS[post.embed.provider] || 'red social'}`"
          ></iframe>
          <a v-else class="feed-embed-link" :href="post.embed.url" target="_blank" rel="noopener noreferrer">
            <AppIcon name="lucide:external-link" :size="18" />
            <span>Ver la publicación en {{ PROVIDER_LABELS[post.embed.provider] || 'la red social' }}</span>
          </a>
        </div>

        <div v-if="post.poll" class="feed-poll" role="group" aria-label="Encuesta">
          <template v-if="post.poll.my_vote || !authed">
            <div
              v-for="opt in post.poll.options" :key="opt.id"
              class="feed-poll-result" :class="{ voted: opt.id === post.poll.my_vote }"
            >
              <span class="feed-poll-bar" :style="{ width: opt.percent + '%' }"></span>
              <span class="feed-poll-label">{{ opt.label }}</span>
              <span class="feed-poll-pct">{{ opt.percent }}%</span>
            </div>
            <p class="feed-poll-total">{{ post.poll.total }} {{ post.poll.total === 1 ? 'voto' : 'votos' }}</p>
            <p v-if="!authed" class="feed-poll-hint">
              <button type="button" class="feed-linklike" @click="openAuth">Ingresá para votar</button>
            </p>
          </template>
          <template v-else>
            <button
              v-for="opt in post.poll.options" :key="opt.id"
              type="button" class="feed-poll-option"
              :disabled="voteBusy[post.id]"
              @click="vote(post, opt)"
            >{{ opt.label }}</button>
          </template>
        </div>

        <footer class="feed-foot">
          <time class="feed-when">{{ whenLabel(post.created_at) }}</time>
          <div class="feed-actions">
            <button
              type="button" class="feed-act" :class="{ on: post.my_like }"
              :aria-pressed="post.my_like" :disabled="likeBusy[post.id]"
              @click="toggleLike(post)"
            >
              <AppIcon :name="post.my_like ? 'lucide:heart' : 'lucide:heart'" :size="17" />
              <span>{{ post.likes_count }}</span>
            </button>
            <button type="button" class="feed-act" :class="{ on: commentState(post.id).open }" @click="toggleComments(post)">
              <AppIcon name="lucide:message-circle" :size="17" />
              <span>{{ post.comments_count }}</span>
            </button>
          </div>
        </footer>

        <section v-if="commentState(post.id).open" class="feed-comments">
          <div v-if="commentState(post.id).status === 'loading'" class="feed-cstate"><span class="spinner spinner-brand"></span></div>
          <p v-else-if="commentState(post.id).status === 'error'" class="feed-cstate">No pudimos cargar los comentarios.</p>
          <p v-else-if="!commentState(post.id).items.length" class="feed-cstate">Sé el primero en comentar.</p>
          <ul v-else class="feed-clist">
            <li v-for="c in commentState(post.id).items" :key="c.id" class="feed-comment">
              <span class="feed-cava" aria-hidden="true">{{ c.avatar }}</span>
              <div class="feed-cbody">
                <p class="feed-cmeta"><strong>{{ c.author }}</strong> <time>{{ whenLabel(c.created_at) }}</time></p>
                <p class="feed-ctext">{{ c.body }}</p>
              </div>
              <button
                v-if="c.mine" type="button" class="feed-cdel"
                title="Borrar mi comentario" aria-label="Borrar mi comentario"
                @click="removeComment(post, c)"
              ><AppIcon name="lucide:trash-2" :size="14" /></button>
            </li>
          </ul>
          <form v-if="authed" class="feed-cform" @submit.prevent="sendComment(post)">
            <input
              v-model="commentState(post.id).draft" class="sp-input" type="text"
              maxlength="600" placeholder="Escribí un comentario o consulta…"
            />
            <button type="submit" class="sp-btn" :disabled="commentState(post.id).busy || !commentState(post.id).draft.trim()">Enviar</button>
          </form>
          <p v-else class="feed-cgate">
            <button type="button" class="feed-linklike" @click="openAuth">Ingresá o creá tu cuenta</button> para comentar.
          </p>
          <p v-if="commentState(post.id).error" class="feed-cerror">{{ commentState(post.id).error }}</p>
        </section>
      </li>
    </ol>
  </main>
</template>

<style scoped>
.feed-page{ max-width: 680px; margin: 0 auto; padding: 28px 16px 64px; display: flex; flex-direction: column; gap: 20px; }
.feed-head h1{ margin: 0; font-size: 30px; letter-spacing: -.02em; color: var(--sp-ink); }
.feed-head p{ margin: 6px 0 0; color: var(--sp-muted); font-size: 14.5px; }
.feed-state{ display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 60px 20px; color: var(--sp-muted); text-align: center; }
.feed-state-icon{ color: var(--store-accent-ink); }
.feed-list{ list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 16px; }
.feed-card{ background: var(--sp-surface); border: 1px solid var(--sp-line); border-radius: var(--sp-radius, 16px); padding: 16px; display: flex; flex-direction: column; gap: 12px; }
.feed-caption{ margin: 0; color: var(--sp-ink); font-size: 15px; line-height: 1.55; white-space: pre-line; overflow-wrap: anywhere; }
.feed-media{ margin: 0; border-radius: 12px; overflow: hidden; border: 1px solid var(--sp-line); background: color-mix(in srgb, var(--sp-line) 30%, transparent); }
.feed-media img, .feed-media video{ display: block; width: 100%; max-height: 560px; object-fit: contain; background: #000; }
.feed-embed-frame{ display: block; width: 100%; border: 0; border-radius: 12px; background: #000; aspect-ratio: 16/9; }
.feed-embed-frame.is-tiktok, .feed-embed-frame.is-instagram{ aspect-ratio: 9/14; max-height: 640px; }
.feed-embed-link{ display: flex; align-items: center; gap: 10px; padding: 14px; border: 1px solid var(--sp-line); border-radius: 12px; color: var(--store-accent-ink); text-decoration: none; font-weight: 600; font-size: 14px; }
.feed-embed-link:hover{ border-color: var(--store-accent); }
.feed-poll{ display: flex; flex-direction: column; gap: 8px; }
.feed-poll-option{ display: block; width: 100%; min-height: 44px; padding: 10px 14px; border-radius: 10px; border: 1px solid var(--sp-line); background: transparent; color: var(--sp-ink); font: inherit; font-weight: 600; text-align: left; cursor: pointer; transition: border-color .15s, background .15s; }
.feed-poll-option:hover{ border-color: var(--store-accent); background: var(--store-accent-soft); }
.feed-poll-result{ position: relative; display: flex; justify-content: space-between; gap: 10px; padding: 10px 14px; border: 1px solid var(--sp-line); border-radius: 10px; overflow: hidden; font-size: 14px; }
.feed-poll-result.voted{ border-color: var(--store-accent); }
.feed-poll-bar{ position: absolute; inset: 0 auto 0 0; background: color-mix(in srgb, var(--store-accent) 18%, transparent); pointer-events: none; }
.feed-poll-label{ position: relative; color: var(--sp-ink); overflow-wrap: anywhere; }
.feed-poll-pct{ position: relative; color: var(--sp-muted); font-variant-numeric: tabular-nums; }
.feed-poll-total{ margin: 0; font-size: 12.5px; color: var(--sp-muted); }
.feed-poll-hint{ margin: 0; font-size: 13px; }
.feed-foot{ display: flex; align-items: center; justify-content: space-between; gap: 12px; border-top: 1px solid var(--sp-line); padding-top: 10px; }
.feed-when{ font-size: 12.5px; color: var(--sp-muted); }
.feed-actions{ display: flex; gap: 6px; }
.feed-act{ display: inline-flex; align-items: center; gap: 6px; min-height: 36px; padding: 6px 12px; border-radius: 99px; border: 1px solid transparent; background: transparent; color: var(--sp-muted); font: inherit; font-size: 13.5px; font-weight: 600; cursor: pointer; transition: color .15s, border-color .15s, background .15s; }
.feed-act:hover{ color: var(--store-accent-ink); border-color: var(--sp-line); }
.feed-act.on{ color: var(--store-accent-ink); background: var(--store-accent-soft); }
.feed-comments{ border-top: 1px solid var(--sp-line); padding-top: 12px; display: flex; flex-direction: column; gap: 12px; }
.feed-cstate{ margin: 0; color: var(--sp-muted); font-size: 13.5px; text-align: center; }
.feed-clist{ list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.feed-comment{ display: flex; gap: 10px; align-items: flex-start; }
.feed-cava{ display: grid; place-items: center; flex: none; width: 30px; height: 30px; border-radius: 50%; background: var(--store-accent-soft); color: var(--store-accent-ink); font-size: 12px; font-weight: 700; }
.feed-cbody{ min-width: 0; }
.feed-cmeta{ margin: 0; font-size: 12.5px; color: var(--sp-muted); display: flex; gap: 8px; }
.feed-cmeta strong{ color: var(--sp-ink); }
.feed-ctext{ margin: 2px 0 0; font-size: 14px; color: var(--sp-ink); line-height: 1.5; overflow-wrap: anywhere; }
.feed-cdel{ flex: none; margin-left: auto; border: 0; background: transparent; color: var(--sp-muted); cursor: pointer; padding: 6px; border-radius: 8px; }
.feed-cdel:hover{ color: #b91c1c; }
.feed-cform{ display: flex; gap: 8px; }
.feed-cform .sp-input{ flex: 1; }
.feed-cgate{ margin: 0; font-size: 13.5px; color: var(--sp-muted); }
.feed-linklike{ border: 0; background: none; padding: 0; color: var(--store-accent-ink); font: inherit; font-weight: 700; cursor: pointer; text-decoration: underline; text-underline-offset: 3px; }
.feed-cerror{ margin: 0; font-size: 13px; color: #b91c1c; }
</style>
