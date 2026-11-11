"""
Correos de la cuenta de comprador (verificación de email y reset de
contraseña). Mismo patrón que AdminApp/domains/users/services: HTML
brand DAVENT + texto plano, envío tolerante a fallos de SMTP (se loguea
y no rompe el flujo) y encolado por Celery desde los services.

Contrato de links con el frontend (los resuelve Track I/J):
- Con contexto de tienda (`store_slug` conocido): el link cuelga de la
  web pública de ESA tienda — `{FRONTEND_URL}/<slug>/cuenta/<accion>`.
- Sin contexto: página de cuenta de la plataforma —
  `{FRONTEND_URL}/cuenta/<accion>` (rutas propias del router, fuera de
  StorePublicLayout: no dependen de que la tienda siga disponible).
Acciones: `verificar?token=<firmado>` y `restablecer?uid=<b64>&token=<firmado>`.
"""
import logging

from decouple import config
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger              =   logging.getLogger(__name__)
#Misma resolución que users/services: env con fallback de dev.
FRONTEND_URL        =   config('FRONTEND_URL', default = '') or 'http://localhost:5173'
#Client ID central de Google para el login social de compradores cuando
#la tienda no configuró el suyo (StoreOAuthConfig BYO). Misma env var que
#el login social DAVENT — vacío = feature apagada para tiendas sin BYO.
GOOGLE_CLIENT_ID    =   config('GOOGLE_CLIENT_ID', default = '')


def account_url(store_slug, action_path):
    """URL absoluta de la página de cuenta (ver docstring del módulo)."""
    base    =   FRONTEND_URL.rstrip('/')
    slug    =   (store_slug or '').strip().lower()
    if slug:
        return f'{base}/{slug}{action_path}'
    #action_path ya trae el '/cuenta/...' completo: duplicarlo generaba
    #/{base}/cuenta/cuenta/... → el router lo leía como slug='cuenta' y
    #la web mostraba "Tienda no disponible".
    return f'{base}{action_path}'


def _mail_html(title, intro, button_label, link, note):
    #Misma presentación de marca que el correo de facturas/usuarios.
    return f"""<!doctype html>
<html lang="es">
<body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif;color:#0f172a;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;overflow:hidden;">
        <tr>
          <td style="background:#4f46e5;padding:24px 32px;">
            <span style="color:#ffffff;font-size:20px;font-weight:700;letter-spacing:.08em;">DAVENT</span><br />
            <span style="color:#c7d2fe;font-size:12px;">Comprá en tus tiendas favoritas</span>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            <h1 style="margin:0 0 8px;font-size:20px;line-height:1.3;">{title}</h1>
            <p style="margin:0 0 24px;font-size:14px;line-height:1.6;color:#475569;">{intro}</p>
            <p style="margin:0 0 24px;text-align:center;">
              <a href="{link}" style="display:inline-block;background:#4f46e5;color:#ffffff;text-decoration:none;font-size:14px;font-weight:700;padding:12px 28px;border-radius:10px;">{button_label}</a>
            </p>
            <p style="margin:0;font-size:12.5px;line-height:1.6;color:#64748b;">{note}</p>
          </td>
        </tr>
        <tr>
          <td style="padding:18px 32px;background:#f8fafc;border-top:1px solid #e2e8f0;font-size:11.5px;line-height:1.6;color:#94a3b8;">
            Si el botón no abre, copiá este enlace en tu navegador:<br />
            <span style="word-break:break-all;">{link}</span><br /><br />
            Este correo se generó automáticamente; no respondas a esta dirección.
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_branded_mail(customer, *, subject, body, html):
    """Envío tolerante: un fallo de correo se loguea y no rompe el flujo."""
    try:
        mail    =   EmailMultiAlternatives(
            subject     =   subject,
            body        =   body,
            from_email  =   settings.DEFAULT_FROM_EMAIL,
            to          =   [customer.email.strip()],
        )
        mail.attach_alternative(html, 'text/html')
        mail.send(fail_silently = False)
    except Exception:
        logger.exception('No se pudo enviar el correo "%s" al cliente %s', subject, customer.pk)
