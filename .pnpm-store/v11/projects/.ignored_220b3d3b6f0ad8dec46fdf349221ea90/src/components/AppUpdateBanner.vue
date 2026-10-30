<script setup>
// Aviso de actualización de la APK: banner inferior descartable cuando hay
// versión nueva, modal bloqueante cuando el server exige min_supported.
// Solo se muestra dentro de la app nativa (el estado lo llena appUpdate.js).
import { computed } from 'vue'
import { Capacitor } from '@capacitor/core'
import AppIcon from './AppIcon.vue'
import { appUpdate, dismissAppUpdate, openAppUpdate } from '../utils/appUpdate.js'

const isNative = Capacitor.isNativePlatform()
const info = computed(() => appUpdate.available)
const versionLabel = computed(() => info.value?.version_name ? ` ${info.value.version_name}` : '')
</script>

<template>
  <template v-if="isNative && info">
    <!-- Bloqueante: versión instalada por debajo del mínimo soportado -->
    <div v-if="appUpdate.required" class="apk-upd-block" role="alertdialog" aria-modal="true" aria-label="Actualización obligatoria">
      <div class="apk-upd-block-card">
        <span class="apk-upd-ico"><AppIcon name="download" :size="22" /></span>
        <h2>Actualización necesaria</h2>
        <p>
          Esta versión de la app quedó atrás y ya no es compatible.
          Actualizá a la versión{{ versionLabel }} para seguir usándola — se instala
          encima y no perdés nada.
        </p>
        <button type="button" class="btn" @click="openAppUpdate">
          <AppIcon name="download" :size="16" /> Actualizar ahora
        </button>
      </div>
    </div>
    <!-- Descartable: hay versión nueva pero la instalada sigue sirviendo -->
    <div v-else class="apk-upd" role="status">
      <span class="apk-upd-ico"><AppIcon name="download" :size="17" /></span>
      <p>Hay una versión nueva{{ versionLabel }} disponible.</p>
      <div class="apk-upd-actions">
        <button type="button" class="apk-upd-go" @click="openAppUpdate">Actualizar</button>
        <button type="button" class="apk-upd-later" @click="dismissAppUpdate">Ahora no</button>
      </div>
    </div>
  </template>
</template>

<style scoped>
/* Banner inferior: por encima del contenido pero por debajo de los modales
   de la app (chat z-96, SupportBot z-90). */
.apk-upd {
  position: fixed; left: 12px; right: 12px; bottom: calc(14px + env(safe-area-inset-bottom, 0px));
  z-index: 80; display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding: 12px 14px; border-radius: var(--radius);
  background: var(--card); border: 1px solid var(--line);
  box-shadow: var(--shadow); color: var(--ink);
}
.apk-upd-ico {
  flex: none; width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center;
  background: var(--brand-soft); color: var(--brand-ink);
}
.apk-upd p { flex: 1 1 140px; margin: 0; font-size: 13.5px; font-weight: 600; }
.apk-upd-actions { display: flex; gap: 8px; margin-left: auto; }
.apk-upd-go {
  border: none; border-radius: var(--radius-sm); padding: 8px 14px; cursor: pointer;
  background: var(--brand-600); color: #fff; font: inherit; font-size: 13px; font-weight: 700;
}
.apk-upd-later {
  border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 8px 12px; cursor: pointer;
  background: transparent; color: var(--muted); font: inherit; font-size: 13px; font-weight: 600;
}
.apk-upd-go:focus-visible, .apk-upd-later:focus-visible { box-shadow: var(--ring); outline: none; }

/* Modal bloqueante a pantalla completa. */
.apk-upd-block {
  position: fixed; inset: 0; z-index: 200; display: grid; place-items: center; padding: 24px;
  background: rgba(9, 12, 30, .72); -webkit-backdrop-filter: blur(6px); backdrop-filter: blur(6px);
}
.apk-upd-block-card {
  width: min(360px, 100%); padding: 28px 24px; border-radius: var(--radius); text-align: center;
  background: var(--card); border: 1px solid var(--line); box-shadow: var(--shadow);
  display: grid; justify-items: center; gap: 6px;
}
.apk-upd-block-card .apk-upd-ico { width: 52px; height: 52px; border-radius: 16px; margin-bottom: 6px; }
.apk-upd-block-card h2 { margin: 0; font-size: 19px; color: var(--ink); }
.apk-upd-block-card p { margin: 4px 0 14px; font-size: 14px; line-height: 1.55; color: var(--ink-2); }
.apk-upd-block-card .btn { width: 100%; }
</style>
