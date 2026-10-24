// Horarios de atención: el dueño los carga como texto libre en pares
// {label, value} (ej. "Lun a vie" / "9 a 13 y 16 a 20 h"). Este módulo los
// interpreta con criterio conservador: si no logra entender ningún renglón
// devuelve null y la web no muestra estado (nunca afirmamos "Abierto" a ciegas).

const DAY_KEYS = ['dom', 'lun', 'mar', 'mie', 'jue', 'vie', 'sab']
const DAY_NAMES = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
const SCHEMA_DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

const plain = (s) => String(s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')

function parseDays(label) {
  const text = plain(label)
  if (/todos los dias|diario|todos|24\/7/.test(text) && !DAY_KEYS.some((k) => text.includes(k))) return [0, 1, 2, 3, 4, 5, 6]
  const tokens = [...text.matchAll(/(lun|mar|mie|jue|vie|sab|dom)[a-z]*/g)]
  if (!tokens.length) return null
  const days = new Set()
  tokens.forEach((t, i) => {
    const day = DAY_KEYS.indexOf(t[1])
    days.add(day)
    const prev = tokens[i - 1]
    if (!prev) return
    const between = text.slice(prev.index + prev[0].length, t.index)
    if (/(^|\s)(a|al|hasta)(\s|$)|[-–—]/.test(between) && !/,|\sy\s/.test(between)) {
      for (let d = (DAY_KEYS.indexOf(prev[1]) + 1) % 7; d !== day; d = (d + 1) % 7) days.add(d)
    }
  })
  return [...days]
}

const toMin = (h, m) => Number(h) * 60 + Number(m || 0)

// Devuelve los tramos [inicio, fin] en minutos del día; fin > 1440 = cruza medianoche.
function parseRanges(value) {
  const text = plain(value)
  if (/cerrado|no atiende|sin atencion/.test(text)) return []
  if (/24\s*(h|hs|horas)\b|24\/7|las 24/.test(text) && !/\d\s*(a|-)\s*\d/.test(text.replace(/24\s*(h|hs|horas)/, ''))) return [[0, 1440]]
  const ranges = []
  for (const m of text.matchAll(/(\d{1,2})(?:[:.](\d{2}))?\s*(?:h|hs)?\s*(?:a|-|–|—|hasta)\s*(\d{1,2})(?:[:.](\d{2}))?/g)) {
    const start = toMin(m[1], m[2])
    let end = toMin(m[3], m[4])
    if (start > 1440 || end > 1440 || Number(m[2] || 0) > 59 || Number(m[4] || 0) > 59) continue
    if (end <= start) end += 1440
    ranges.push([start, end])
  }
  return ranges.length ? ranges : null
}

// -> null | Array(7) indexado por getDay() con los tramos de cada día.
export function parseHours(hours) {
  if (!Array.isArray(hours) || !hours.length) return null
  const week = Array.from({ length: 7 }, () => [])
  let understood = false
  for (const row of hours) {
    const days = parseDays(row?.label)
    const ranges = parseRanges(row?.value)
    if (!days || !ranges) continue
    understood = true
    days.forEach((d) => week[d].push(...ranges))
  }
  return understood ? week : null
}

const fmt = (min) => {
  const m = min % 1440
  const h = Math.floor(m / 60)
  const mm = m % 60
  return mm ? `${h}:${String(mm).padStart(2, '0')}` : `${h} h`
}

// -> null | {state: 'open'|'closed', text}
export function openStatus(hours, now = new Date()) {
  const week = parseHours(hours)
  if (!week) return null
  const day = now.getDay()
  const minute = now.getHours() * 60 + now.getMinutes()
  const prev = week[(day + 6) % 7]
  const spill = prev.find(([, end]) => end > 1440 && minute < end - 1440)
  if (spill) return { state: 'open', text: `Abierto ahora · hasta ${fmt(spill[1])}` }
  const today = week[day].find(([start, end]) => minute >= start && minute < end)
  if (today) return { state: 'open', text: `Abierto ahora · hasta ${fmt(today[1])}` }
  const later = week[day].filter(([start]) => start > minute).sort((a, b) => a[0] - b[0])[0]
  if (later) return { state: 'closed', text: `Cerrado ahora · abre hoy ${fmt(later[0])}` }
  for (let i = 1; i <= 7; i++) {
    const d = (day + i) % 7
    const first = [...week[d]].sort((a, b) => a[0] - b[0])[0]
    if (first) return { state: 'closed', text: `Cerrado ahora · abre ${i === 1 ? 'mañana' : DAY_NAMES[d].toLowerCase()} ${fmt(first[0])}` }
  }
  return { state: 'closed', text: 'Cerrado ahora' }
}

// -> openingHoursSpecification de schema.org
export function schemaHours(hours) {
  const week = parseHours(hours)
  if (!week) return []
  const pad = (min) => { const m = Math.min(min, 1439); return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}` }
  return week.flatMap((ranges, d) => ranges.map(([start, end]) => ({
    '@type': 'OpeningHoursSpecification',
    dayOfWeek: SCHEMA_DAYS[d],
    opens: pad(start),
    closes: pad(end)
  })))
}
