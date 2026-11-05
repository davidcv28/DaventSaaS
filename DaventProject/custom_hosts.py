"""
Dominios propios verificados (StoreDomain) como Host header válido.

ALLOWED_HOSTS es estático y los dominios de clientes son arbitrarios y
dinámicos: no se puede listar `*` (envguard E009) ni cada dominio a mano.
Se envuelve django.http.request.validate_host: los hosts de plataforma
siguen por la lista estática y solo los que fallan ahí consultan
StoreDomain (status verified), con caché corta para no pegarle a la base
en cada request. La invalidación explícita corre en services/domains.py
(refresh_status) y en el viewset (POST/DELETE domain) vía
invalidate_domain_host().
"""
from django.core.cache import cache
from django.http import request as http_request

TTL     =   120
PREFIX  =   'cdh:'

def _domain_host_key(host):
    #El Host puede venir con puerto ('mitienda.com:443') y el dominio
    #guardado nunca lo tiene.
    return str(host or '').split(':')[0].strip().lower()

def is_verified_domain_host(host):
    domain  =   _domain_host_key(host)
    if not domain:
        return False
    key     =   f'{PREFIX}{domain}'
    ok      =   cache.get(key)
    if ok is None:
        try:
            from StoreApp.domains.stores.models import StoreDomain
            ok  =   StoreDomain.objects.filter(
                domain = domain, status = StoreDomain.STATUS_VERIFIED
            ).exists()
        except Exception:
            #Fail-closed: si la base no responde, el host se rechaza (400)
            #en vez de tumbar el request con un 500.
            return False
        cache.set(key, ok, TTL)
    return bool(ok)

def invalidate_domain_host(domain):
    cache.delete(f'{PREFIX}{_domain_host_key(domain)}')

_orig_validate_host    =   http_request.validate_host

def _validate_host(host, allowed_hosts):
    if _orig_validate_host(host, allowed_hosts):
        return True
    return is_verified_domain_host(host)

http_request.validate_host    =   _validate_host
