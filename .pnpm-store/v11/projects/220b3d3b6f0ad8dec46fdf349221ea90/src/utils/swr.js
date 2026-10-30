// Cache SWR (stale-while-revalidate) en sessionStorage para el dashboard:
// al volver al panel las vistas pintan al instante con lo último cargado y
// el store revalida en segundo plano — el spinner completo solo aparece en
// la primera carga real. No lleva user id en la key: resetSessionStores()
// (login/logout) purga todas las claves davent:swr:* junto con los stores.
const NS = 'davent:swr:'

// Devuelve el valor cacheado o undefined si no hay entrada (null serializa
// bien y se distingue de "sin cache": suscripción inexistente cacheada ≠ miss).
export function swrGet(key) {
  try {
    const raw = sessionStorage.getItem(NS + key)
    return raw ? JSON.parse(raw).v : undefined
  } catch {
    return undefined
  }
}

export function swrSet(key, value) {
  try {
    sessionStorage.setItem(NS + key, JSON.stringify({ v: value }))
  } catch { /* cuota llena o storage bloqueado: el panel igual funciona */ }
}

export function swrClear() {
  try {
    const doomed = []
    for (let i = 0; i < sessionStorage.length; i++) {
      const k = sessionStorage.key(i)
      if (k && k.startsWith(NS)) doomed.push(k)
    }
    doomed.forEach((k) => sessionStorage.removeItem(k))
  } catch { /* storage bloqueado */ }
}
