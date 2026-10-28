// Publicación unificada de la APK release firmada (APK_ROADMAP prompt 7):
//   1. Vite build con VITE_API_BASE_URL=/api + VITE_PLATFORM_DOMAIN=davent.com
//   2. npx cap sync android
//   3. gradlew assembleRelease (firma via keystore.properties / DAVENT_KEYSTORE_*)
//   4. Copia a apk-dist/davent-<versionName>-<versionCode>.apk
// Uso: npm run release:apk          → build + firma + staging
//      npm run release:apk -- --upload  → idem + sube a R2 via manage.py publish_apk
//      npm run release:apk -- --domain daventsaas.onrender.com
//        → build apuntando a otro backend (parchea server.hostname de
//          capacitor.config.json durante el build y lo restaura al final).
//          Sin --domain usa el hostname del config (hoy: davent.com).
import { spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, copyFileSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve, isAbsolute } from 'node:path'
import { fileURLToPath } from 'node:url'

const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const ANDROID = join(FRONTEND, 'android')
const APK_DIST = join(FRONTEND, 'apk-dist')
const REPO_ROOT = resolve(FRONTEND, '..')
const CAP_CONFIG = join(FRONTEND, 'capacitor.config.json')
const isWin = process.platform === 'win32'
const upload = process.argv.includes('--upload')
const domainArg = (() => { const i = process.argv.indexOf('--domain'); return i !== -1 ? process.argv[i + 1] : null })()

// Dominio del WebView: el origen same-site de la app (y del /api). Por defecto
// es el server.hostname commiteado en capacitor.config.json.
const capConfigText = readFileSync(CAP_CONFIG, 'utf8')
const capConfig = JSON.parse(capConfigText)
const domain = (domainArg || capConfig.server?.hostname || 'davent.com').toLowerCase()

// Con --domain distinto, parcheo el hostname solo durante el build — el
// archivo commiteado conserva el dominio de producción.
let capConfigBackup = null
if (capConfig.server?.hostname !== domain) {
  capConfigBackup = capConfigText
  capConfig.server = { ...(capConfig.server || {}), hostname: domain }
  writeFileSync(CAP_CONFIG, JSON.stringify(capConfig, null, 2) + '\n')
}

let failed = false
const fail = (msg) => { console.error(`✗ ${msg}`); failed = true }
const ok = (msg) => console.log(`✓ ${msg}`)

// ---------- Preflight ----------
console.log('— Preflight —')

// 1. Credenciales de firma: keystore.properties O env vars DAVENT_KEYSTORE_*.
const propsPath = join(ANDROID, 'keystore.properties')
const envSign = ['DAVENT_KEYSTORE_FILE', 'DAVENT_KEYSTORE_STORE_PASSWORD', 'DAVENT_KEYSTORE_KEY_ALIAS', 'DAVENT_KEYSTORE_KEY_PASSWORD']
  .every((k) => process.env[k])
if (existsSync(propsPath)) {
  const props = readFileSync(propsPath, 'utf8')
  if (props.includes('COMPLETAR_PASSWORD')) {
    fail('keystore.properties todavía tiene el placeholder COMPLETAR_PASSWORD — cargá la password real del keystore.')
  } else {
    const m = props.match(/^storeFile=(.+)$/m)
    const storeFile = m?.[1].trim().replace(/\\\\/g, '\\')
    if (storeFile && !existsSync(isAbsolute(storeFile) ? storeFile : join(ANDROID, storeFile))) {
      fail(`storeFile no existe: ${storeFile}`)
    } else ok('keystore.properties OK (storeFile presente)')
  }
} else if (!envSign) {
  fail('No hay android/keystore.properties ni env vars DAVENT_KEYSTORE_* — la release quedaría sin firma.')
} else ok('Firma via env vars DAVENT_KEYSTORE_*')

// 2. JDK 21 en JAVA_HOME.
const javaHome = process.env.JAVA_HOME
if (!javaHome) {
  fail('JAVA_HOME no está definido (esperado: E:\\apps\\jdk-21).')
} else {
  const javaBin = join(javaHome, 'bin', isWin ? 'java.exe' : 'java')
  if (!existsSync(javaBin)) fail(`JAVA_HOME inválido: no existe ${javaBin}`)
  else {
    // java -version imprime en stderr.
    const r = spawnSync(javaBin, ['-version'], { encoding: 'utf8' })
    const ver = `${r.stdout || ''}${r.stderr || ''}`
    const major = parseInt(ver.match(/version "(\d+)/)?.[1] || '0', 10)
    if (major === 21) ok(`JDK 21 (${javaHome})`)
    else fail(`JAVA_HOME apunta a JDK ${major || '?'} — Gradle de este proyecto requiere JDK 21 (E:\\apps\\jdk-21).`)
  }
}

// 3. Android SDK.
const sdkHome = process.env.ANDROID_HOME || process.env.ANDROID_SDK_ROOT
if (!sdkHome) fail('ANDROID_HOME/ANDROID_SDK_ROOT no definido (esperado: E:\\apps\\android-sdk).')
else if (!existsSync(join(sdkHome, 'platform-tools'))) fail(`Android SDK inválido en ${sdkHome} (falta platform-tools).`)
else ok(`Android SDK (${sdkHome})`)

if (!existsSync(join(ANDROID, isWin ? 'gradlew.bat' : 'gradlew'))) fail('No existe gradlew en frontend/android/.')
else ok('gradlew presente')
if (!existsSync(join(FRONTEND, 'node_modules'))) fail('Falta npm install en frontend/.')
else ok('node_modules presente')

if (failed) {
  console.error('\nPreflight falló — corregí los puntos y reintentá.')
  process.exit(1)
}

// ---------- Build ----------
function step(title, cmd, args, opts = {}) {
  console.log(`\n— ${title} —`)
  // Con shell:true, cmd+args se concatenan y pasan por cmd.exe → cualquier
  // path con espacios ("SaaS DAVENT") hay que entrecomillarlo o se parte.
  const useShell = opts.shell ?? isWin
  const q = (s) => (isWin && useShell && /\s/.test(s) && !s.startsWith('"') ? `"${s}"` : s)
  const r = spawnSync(q(cmd), args.map(q), { cwd: FRONTEND, stdio: 'inherit', shell: isWin, env: process.env, ...opts })
  if (r.status !== 0) {
    throw new Error(`Falló: ${title} (exit ${r.status})`)
  }
}

// Versión desde la fuente de verdad (android/app-version.properties).
const vp = readFileSync(join(ANDROID, 'app-version.properties'), 'utf8')
const versionName = vp.match(/^versionName=(.+)$/m)?.[1].trim()
const versionCode = vp.match(/^versionCode=(.+)$/m)?.[1].trim()
console.log(`\nVersión objetivo: ${versionName} (${versionCode})`)
console.log(`Origen WebView / API: https://${domain}  (/api same-site)`)

try {
  // 1. Vite build — /api resuelve same-site en el WebView; VITE_PLATFORM_DOMAIN
  //    controla la detección de subdominios de tienda.
  step('Vite build (producción APK)', 'npx', ['vite', 'build'], {
    env: { ...process.env, VITE_API_BASE_URL: '/api', VITE_PLATFORM_DOMAIN: domain },
  })

  // 2. Sync web assets + plugins al proyecto Android.
  step('cap sync android', 'npx', ['cap', 'sync', 'android'])

  // 3. assembleRelease firmado (el path se cita solo en step() por el espacio
  //    de "SaaS DAVENT").
  step('gradlew assembleRelease', join(ANDROID, isWin ? 'gradlew.bat' : 'gradlew'), ['assembleRelease'], { cwd: ANDROID })

  // 4. Staging: copiar el APK firmado con nombre de versión.
  const src = join(ANDROID, 'app', 'build', 'outputs', 'apk', 'release', 'app-release.apk')
  if (!existsSync(src)) {
    throw new Error(`No se generó ${src}`)
  }
  mkdirSync(APK_DIST, { recursive: true })
  const dest = join(APK_DIST, `davent-${versionName}-${versionCode}.apk`)
  copyFileSync(src, dest)
  console.log(`\n✓ APK firmado: ${dest}`)

  // 5. Publicación en R2 (opcional): versionado + davent-latest.apk.
  if (upload) {
    const py = join(REPO_ROOT, 'venv', 'Scripts', 'python.exe')
    if (!existsSync(py)) {
      throw new Error(`--upload: no existe ${py}`)
    }
    step('publish_apk → R2', py, [join(REPO_ROOT, 'manage.py'), 'publish_apk', '--file', dest, '--version-name', versionName, '--version-code', versionCode], { cwd: REPO_ROOT })
  }

  console.log(`
Listo. Pasos de publicación:
  1. Subir a R2:   venv/Scripts/python.exe manage.py publish_apk --file "${dest}" --version-name ${versionName} --version-code ${versionCode}
     (o relanzar este script con --upload)
  2. Actualizar el env del server:
       APP_APK_VERSION_NAME=${versionName}
       APP_APK_VERSION_CODE=${versionCode}
       APP_APK_URL=<url pública del APK en R2>
  3. El update checker in-app y /descargar leen esos valores vía GET /api/config/.
`)
} catch (e) {
  console.error(`\n✗ ${e.message}`)
  process.exitCode = 1
} finally {
  if (capConfigBackup) {
    writeFileSync(CAP_CONFIG, capConfigBackup)
    console.log('\n(capacitor.config.json restaurado al hostname de producción)')
  }
}
