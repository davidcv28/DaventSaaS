// Resolución y ejecución del driver de navegador para visual-qa.
//
// No hay puppeteer/playwright en node_modules (verificado en package.json y
// lockfiles): el driver es scripts/lib/pw_driver.py, que usa el Playwright
// de Python YA instalado en venv/ del repo (con Chromium descargado).
// Si en el futuro se instala `playwright` npm, este módulo es el único
// punto a extender — visual-qa.mjs no cambia.

import { execFile } from 'node:child_process'
import { existsSync, mkdirSync, writeFileSync, rmSync } from 'node:fs'
import { randomBytes } from 'node:crypto'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const LIB_DIR = dirname(fileURLToPath(import.meta.url))
const FRONTEND_DIR = resolve(LIB_DIR, '..', '..')
const REPO_ROOT = resolve(FRONTEND_DIR, '..')
export const DRIVER_PY = join(LIB_DIR, 'pw_driver.py')

function* pythonCandidates(configured) {
  if (configured) yield resolve(FRONTEND_DIR, configured)
  if (process.env.DAVENT_QA_PYTHON) yield resolve(FRONTEND_DIR, process.env.DAVENT_QA_PYTHON)
  yield join(REPO_ROOT, 'venv', 'Scripts', 'python.exe') // Windows (este repo)
  yield join(REPO_ROOT, 'venv', 'bin', 'python') // Linux/macOS
  yield 'python'
  yield 'py'
}

export function resolvePython(configured) {
  for (const cand of pythonCandidates(configured)) {
    if (cand.includes('/') || cand.includes('\\') || cand.endsWith('.exe')) {
      if (existsSync(cand)) return cand
    } else {
      return cand // 'python'/'py' del PATH: se prueba al ejecutar
    }
  }
  return null
}

// Corre UN job de página y devuelve el JSON de resultado del driver.
// Lanza Error con mensaje claro si el driver no arranca o no responde.
export function runPageJob(job, { python, timeoutMs = 90000 } = {}) {
  return new Promise((res, rej) => {
    const py = python || resolvePython()
    if (!py) {
      rej(new Error('No se encontró intérprete de Python para el driver visual-qa (venv/Scripts/python.exe). Configurá "python" en visual-qa.config.json o DAVENT_QA_PYTHON.'))
      return
    }
    // El job va a un archivo dentro de visual-qa/ (no al TEMP del OS: en
    // este repo %TEMP% puede apuntar a OneDrive y bloquear mkdtemp).
    const jobsDir = join(FRONTEND_DIR, 'visual-qa', '.jobs')
    mkdirSync(jobsDir, { recursive: true })
    const jobFile = join(jobsDir, `job-${process.pid}-${randomBytes(4).toString('hex')}.json`)
    writeFileSync(jobFile, JSON.stringify(job), 'utf8')
    // TEMP/TMP del OS puede apuntar a OneDrive y romper el mkdtemp que hace
    // Playwright al lanzar el browser: se redirige a visual-qa/.tmp.
    const tmpDir = join(FRONTEND_DIR, 'visual-qa', '.tmp')
    mkdirSync(tmpDir, { recursive: true })
    const child = execFile(
      py,
      [DRIVER_PY, jobFile],
      {
        timeout: timeoutMs,
        maxBuffer: 16 * 1024 * 1024,
        windowsHide: true,
        env: { ...process.env, TEMP: tmpDir, TMP: tmpDir, PYTHONIOENCODING: 'utf-8' }
      },
      (err, stdout, stderr) => {
        try {
          rmSync(jobFile, { force: true })
        } catch {}
        if (err) {
          rej(new Error(`driver falló (${py}): ${err.message}${stderr ? ' :: ' + stderr.slice(0, 500) : ''}`))
          return
        }
        try {
          const data = JSON.parse(stdout.trim().split('\n').pop())
          res(data)
        } catch {
          rej(new Error(`driver devolvió salida no-JSON: ${(stdout || '').slice(0, 300)}`))
        }
      }
    )
    child.on('error', (e) => {
      try { rmSync(jobFile, { force: true }) } catch {}
      rej(new Error(`no se pudo ejecutar ${py}: ${e.message}`))
    })
  })
}
