# Prompt — Piel moderntec para auth y cuenta del comprador

Orquestá subagentes (`subagent_general`, background, ownership disjunto) para darle identidad `moderntec` a la autenticación y a la cuenta del COMPRADOR. Hoy se ven genéricas.

Lenguaje moderntec: "instrumento de laboratorio". Grafito `#06080c`, grilla fina, reglas de 1px, telemetría JetBrains Mono, display Outfit, acento cyan→violeta. Tokens `--mt-*` en `frontend/src/assets/store-moderntec.css` (leer solo el bloque de tokens, ~120 líneas).

## Wiring (hacer antes de lanzar los agentes)
1. Crear vacíos en `frontend/src/assets/`: `store-moderntec-auth.css`, `store-moderntec-account.css`, `store-moderntec-account-sections.css`.
2. En `frontend/src/views/StorePublicLayout.vue`, `TEMPLATE_CSS.moderntec` → `Promise.all` con `import()` de `store-moderntec.css` y las tres hojas.

## Subagentes
| Agente | Archivos propios (únicos que puede tocar) |
|---|---|
| Auth | `views/StoreAuthView.vue`, `components/ecommerce/StoreAuthForm.vue`, `components/ecommerce/StoreAuthModal.vue`, `assets/store-moderntec-auth.css` |
| Shell cuenta | `views/StoreAccountView.vue`, `components/ecommerce/account/AccountProfile.vue`, `assets/store-moderntec-account.css` |
| Secciones | `components/ecommerce/account/AccountOrders.vue`, `AccountAddresses.vue`, `AccountSubscriptions.vue`, `assets/store-moderntec-account-sections.css` |

## Reglas para todos
- Todo override scopeado con `.store-page[data-template='moderntec']`. Los `<style scoped>` de los componentes ganan por especificidad: usar `:is()`/`[data-store-template]` y `!important` solo si hace falta.
- Se puede agregar marcado (índices mono 01–05, chips de estado con datos reales, rail `01`) sin tocar lógica, props ni emits. Nada de telemetría inventada.
- Estados (pedido/suscripción) distinguibles sin depender solo del color (glifo + texto).
- Evitar clichés genéricos de IA (tarjeta centrada con gradiente, glow excesivo).
- Un `*/` dentro de un comentario CSS descarta el bloque entero.
- AA, `:focus-visible`, `prefers-reduced-motion`, 360px sin scroll horizontal.
- QA: `http://localhost:5173/mt-qa/ingresar` (`?mode=register|forgot`) y `/mt-qa/cuenta`. Verificar con screenshot (skill `browser-automation`).
- Sin `git commit` en los subagentes; el orquestador commitea solo los archivos de la tarea (el repo suele tener cambios ajenos sin commitear) y hace push a `main`.

## Pendiente conocido
- Estilar `PlanSubscribe` (hijo de Suscripciones).
- Timeline de pedidos (no existe en el marcado).
- Revisión visual de contraste, 360px y especificidad contra los `<style scoped>`.
- `npm run build` falló una vez por "Acceso denegado" en un temp de esbuild; reintentar.
