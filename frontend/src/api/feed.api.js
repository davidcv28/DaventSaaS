import { http, publicHttp } from './http.js'
import { customerHttp } from './customer.http.js'

// =============================================================================
// Feed social de la tienda ("Novedades" en la web pública).
//   - Dueño (sesión DAVENT): CRUD de posts, media y moderación de comentarios.
//   - Público: lectura anónima por publicHttp; las interacciones (like,
//     comentar, votar) van por customerHttp con el JWT del comprador — la
//     lectura también puede ir por customerHttp para marcar my_like/my_vote.
// =============================================================================

const base = (slug) => `/stores/public/${slug}/feed`

export const feedApi = {
  // ---- Dueño ----
  list: () => http.get('/store-feed/posts/').then((r) => r.data),
  create: (payload) => http.post('/store-feed/posts/', payload).then((r) => r.data),
  update: (id, payload) => http.patch(`/store-feed/posts/${id}/`, payload).then((r) => r.data),
  remove: (id) => http.delete(`/store-feed/posts/${id}/`).then((r) => r.data),
  uploadMedia: (id, file) => {
    const form = new FormData()
    form.append('file', file)
    return http.post(`/store-feed/posts/${id}/media/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then((r) => r.data)
  },
  removeMedia: (id) => http.delete(`/store-feed/posts/${id}/media/`).then((r) => r.data),
  comments: (postId = null) => http.get('/store-feed/comments/', {
    params: postId ? { post: postId } : {}
  }).then((r) => r.data),
  moderateComment: (id, isHidden) => http.patch(`/store-feed/comments/${id}/`, { is_hidden: isHidden }).then((r) => r.data),
  removeComment: (id) => http.delete(`/store-feed/comments/${id}/`).then((r) => r.data),

  // ---- Público (lectura anónima o con sesión de comprador) ----
  publicList: (slug, authenticated = false) => {
    const client = authenticated ? customerHttp : publicHttp
    return client.get(`${base(slug)}/`).then((r) => r.data)
  },
  publicComments: (slug, postId, authenticated = false) => {
    const client = authenticated ? customerHttp : publicHttp
    return client.get(`${base(slug)}/${postId}/comments/`).then((r) => r.data)
  },
  comment: (slug, postId, body) =>
    customerHttp.post(`${base(slug)}/${postId}/comments/`, { body }).then((r) => r.data),
  removeMyComment: (slug, commentId) =>
    customerHttp.delete(`${base(slug)}/comments/${commentId}/`).then((r) => r.data),
  like: (slug, postId) =>
    customerHttp.post(`${base(slug)}/${postId}/like/`).then((r) => r.data),
  vote: (slug, postId, option) =>
    customerHttp.post(`${base(slug)}/${postId}/vote/`, { option }).then((r) => r.data)
}
