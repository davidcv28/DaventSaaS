"""
Sanitización de logs: ningún secreto (PEM, tokens, Authorization/Bearer,
JWT, passwords, rutas de claves, CUITs, tokens enc:v1:) debe llegar a stdout
aunque un dev nuevo loguee el objeto equivocado (request.data, un dict de MP,
una excepción con la traza cruda).

`scrub()` es el mismo redactor que usa afip.scrub para `afip_error` (los
patrones viven acá: una sola fuente); `ScrubSecretsFilter` se cuelga del
handler 'console' en LOGGING y limpia msg, args y exc_text de TODOS los
loggers que salen por stdout — incluido django.request (los 500 con traza).
"""
import logging
import re

#El orden importa: PEM (bloque multilínea) primero, después claves sueltas.
SECRET_PATTERNS     =   (
    (re.compile(r'-----BEGIN [A-Z ]+-----.*?(-----END [A-Z ]+-----|$)', re.S), '[PEM]'),
    (re.compile(r'(?i)(token|sign|cms|authorization|bearer)(["\'>=:\s]+)[A-Za-z0-9+/=_.\-]{16,}'), r'\1\2[REDACTED]'),
    #JWT compacto (3 tramos base64url; los ID tokens de Google arrancan 'eyJ').
    (re.compile(r'eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}'), '[JWT]'),
    (re.compile(r'enc:v1:[A-Za-z0-9_.\-:]+'), '[ENC]'),
    (re.compile(r'(?i)(password|passwd|passphrase)(["\'>=:\s]+)[^\s"\']{4,}'), r'\1\2[REDACTED]'),
    (re.compile(r'(?:[A-Za-z]:)?[\\/](?:[\w.\- ]+[\\/])+[\w.\-]+'), '[PATH]'),
    (re.compile(r'\b\d{11}\b'), '[CUIT]'),
)


def scrub(message, limit : int = 500, tail : bool = False) -> str:
    """Redacta patrones de secretos y acota el largo. `tail` conserva el
    final (las trazas ponen la excepción abajo — es lo que importa)."""
    text    =   str(message)
    for pattern, replacement in SECRET_PATTERNS:
        text    =   pattern.sub(replacement, text)
    if len(text) > limit:
        text    =   text[-limit:] if tail else text[:limit]
    return text


class ScrubSecretsFilter(logging.Filter):
    """Filtro global: aplica scrub() al mensaje, a cada arg y a la traza.
    Corre antes del Formatter, así que exc_text se compone acá (sanitizado)
    y exc_info se baja para que el handler no la vuelva a volcar en crudo."""

    def filter(self, record : logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg      =   scrub(record.msg, limit = 4000)
        if record.args:
            if isinstance(record.args, dict):
                record.args =   {k: (scrub(v, limit = 4000) if isinstance(v, str) else v)
                                 for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args =   tuple(scrub(v, limit = 4000) if isinstance(v, str) else v
                                      for v in record.args)
        if record.exc_info:
            #La traza puede llevar paths de claves o datos de la excepción:
            #se formatea una sola vez, sanitizada y conservando el tail.
            record.exc_text =   scrub(logging.Formatter().formatException(record.exc_info),
                                      limit = 8000, tail = True)
            record.exc_info =   None
        elif record.exc_text:
            record.exc_text =   scrub(record.exc_text, limit = 8000, tail = True)
        return True
