<script setup>
// Página pública de descarga de la APK (distribución web directa — no va por
// Play Store). Hero con el botón de descarga directa, QR al mismo link para
// pasarla de la PC al teléfono, requisitos y el paso a paso de instalación
// con la aclaración honesta del aviso "archivo puede ser dañino".
import { ref, onMounted } from 'vue'
import LegalLayout from '../components/LegalLayout.vue'
import AppIcon from '../components/AppIcon.vue'
import { env } from '../config/env.js'
import { fetchAppInfo, isAndroidDevice } from '../api/app.api.js'

const apkUrl = ref(env.appApkUrl)
const versionName = ref('')
const qrDataUrl = ref('')
// En el propio teléfono el QR no aporta: se ve el botón directo.
const onAndroid = isAndroidDevice()

const steps = [
  { title: 'Tocá “Descargar para Android”', text: 'Se baja un archivo .apk, el instalador de la app.' },
  { title: 'Abrí el archivo descargado', text: 'Desde la notificación de descarga o la app Archivos del teléfono.' },
  { title: 'Permití la instalación', text: 'La primera vez Android pide autorizar “instalar apps de esta fuente”: aceptalo solo para tu navegador.' },
  { title: 'Tocá Instalar y entrá con tu cuenta', text: 'Mismo usuario y contraseña que en la web.' },
]

onMounted(async () => {
  // La URL que publica el server pisa al fallback estático.
  const info = await fetchAppInfo()
  if (info?.apk_url) apkUrl.value = info.apk_url
  if (info?.version_name) versionName.value = info.version_name
  try {
    const QRCode = (await import('qrcode')).default
    qrDataUrl.value = await QRCode.toDataURL(apkUrl.value, { margin: 1, width: 340 })
  } catch { /* el botón funciona igual sin QR */ }
})
</script>

<template>
  <LegalLayout title="Descargá la app" subtitle="DAVENT para Android — tu negocio en el bolsillo">
    <article class="legal-doc">
      <section class="dl-hero">
        <div class="dl-hero-copy">
          <span class="dl-badge"><AppIcon name="smartphone" :size="14" /> App para Android</span>
          <h2>Tu negocio, a un toque.</h2>
          <p>
            Gestioná tu web, tus productos y tus estadísticas desde el teléfono:
            la misma cuenta y la misma información que en la web, sin abrir el navegador.
          </p>
          <a class="btn dl-btn" :href="apkUrl">
            <AppIcon name="download" :size="17" /> Descargar para Android
          </a>
          <small class="dl-meta">
            {{ versionName ? `Versión ${versionName} · ` : '' }}Android 8 o superior · Gratis
          </small>
        </div>
        <div v-if="qrDataUrl && !onAndroid" class="dl-qr">
          <img :src="qrDataUrl" alt="Código QR con el link de descarga de la app de DAVENT" width="148" height="148" />
          <small>Escanealo con tu teléfono</small>
        </div>
      </section>

      <h2>Cómo instalarla</h2>
      <ol class="dl-steps">
        <li v-for="(s, i) in steps" :key="i">
          <span class="dl-step-n">{{ i + 1 }}</span>
          <div><strong>{{ s.title }}</strong><p>{{ s.text }}</p></div>
        </li>
      </ol>

      <div class="dl-warn" role="note">
        <AppIcon name="info" :size="18" />
        <p>
          Si el navegador avisa <em>“este archivo puede ser dañino”</em>, es el cartel
          estándar que Android muestra para cualquier app que no viene de Play Store —
          no significa que el archivo tenga un problema. La APK es oficial, está firmada
          por DAVENT y solo se distribuye desde nuestra web. Tocá <strong>“Descargar de todas formas”</strong>.
        </p>
      </div>

      <h2>Qué necesitás</h2>
      <ul class="dl-req">
        <li><AppIcon name="circle-check" :size="16" /> Android 8.0 o superior</li>
        <li><AppIcon name="circle-check" :size="16" /> Conexión a internet</li>
        <li><AppIcon name="circle-check" :size="16" /> Unos pocos MB de espacio</li>
      </ul>

      <h2>¿Por qué no está en Play Store?</h2>
      <p>
        La distribuimos directo desde nuestra web para actualizarla más rápido y sin
        trámites de publicación. Cuando haya una versión nueva la app te avisa sola y
        se actualiza encima de la instalada — sin desinstalar ni perder tu sesión.
      </p>
    </article>
  </LegalLayout>
</template>

<style scoped>
.dl-hero {
  display: flex; flex-wrap: wrap; align-items: center; gap: 26px;
  padding: 26px 28px; border-radius: var(--radius); margin-bottom: 28px;
  background: linear-gradient(135deg, var(--brand-600), var(--accent));
  color: #fff; box-shadow: var(--shadow-md);
}
.dl-hero-copy { flex: 1 1 320px; min-width: 0; }
.dl-badge {
  display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px;
  border-radius: 999px; border: 1px solid rgba(255, 255, 255, .35);
  background: rgba(255, 255, 255, .12); font-size: 12px; font-weight: 700;
  letter-spacing: .06em; text-transform: uppercase;
}
.dl-hero h2 { margin: 14px 0 0; font-size: 26px; letter-spacing: -.02em; }
.dl-hero-copy > p { margin: 10px 0 0; color: rgba(255, 255, 255, .88); font-size: 14.5px; }
.dl-btn {
  margin-top: 20px; width: auto; padding: 13px 24px; font-size: 15.5px; font-weight: 700;
  background: #fff; color: var(--brand-600); border-color: #fff; border-radius: var(--radius-sm);
  box-shadow: 0 10px 26px -8px rgba(15, 17, 48, .55); text-decoration: none;
}
.dl-btn:hover { background: #eef0ff; }
.dl-meta { display: block; margin-top: 12px; color: rgba(255, 255, 255, .75); font-size: 12.5px; }
.dl-qr {
  flex: none; display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 14px; border-radius: var(--radius); background: #fff; color: var(--muted);
  font-size: 12px; font-weight: 600; box-shadow: var(--shadow-md);
}
.dl-qr img { display: block; border-radius: 6px; }

.dl-steps { list-style: none; margin: 14px 0 22px; padding: 0; display: grid; gap: 14px; }
.dl-steps li { display: flex; gap: 14px; align-items: flex-start; }
.dl-step-n {
  flex: none; width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center;
  background: var(--brand-soft); color: var(--brand-ink); font-weight: 800; font-size: 14px;
  border: 1px solid var(--brand-soft-line);
}
.dl-steps strong { color: var(--ink); font-size: 14.5px; }
.dl-steps p { margin: 2px 0 0; color: var(--ink-2); font-size: 14px; }

.dl-warn {
  display: flex; gap: 12px; align-items: flex-start; margin: 4px 0 22px;
  padding: 14px 16px; border-radius: var(--radius-sm);
  background: var(--warn-bg); border: 1px solid var(--warn-line);
  color: var(--ink-2);
}
.dl-warn svg { flex: none; margin-top: 2px; color: var(--warn); }
.dl-warn p { margin: 0; font-size: 13.5px; line-height: 1.55; }

.dl-req { list-style: none; margin: 10px 0 20px; padding: 0; display: flex; flex-wrap: wrap; gap: 10px; }
.dl-req li {
  display: inline-flex; align-items: center; gap: 7px; padding: 7px 13px;
  border-radius: 999px; border: 1px solid var(--line); background: var(--surface);
  color: var(--ink-2); font-size: 13px; font-weight: 600;
}
.dl-req svg { color: var(--ok); }

@media (max-width: 560px) {
  .dl-hero { padding: 22px 20px; }
  .dl-qr { margin: 0 auto; }
}
</style>
