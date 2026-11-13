import { http } from './http.js'

// =============================================================================
// Sincronización de la tienda del dueño (cola de operaciones web).
// GET  /api/stores/sync/      → {pending_count, last_sync_at, operations[]}
// POST /api/stores/sync/run/  → mismo shape tras procesar la cola
// operation: {id, op, status: pending|done|error, attempts, detail, created_at}
// =============================================================================

export const fetchSyncState = () => http.get('/stores/sync/').then((r) => r.data)
export const runSync = () => http.post('/stores/sync/run/').then((r) => r.data)
