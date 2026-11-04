#!/usr/bin/env python
"""
Servidor MCP de DAVENT con FastMCP (SDK oficial `mcp`).

Dos transportes:
  - stdio (default): herramientas de catálogo público. Las tools my_*
    quedan ciegas: no hay sesión, devuelven ToolError.
  - http (streamable-http): el usuario llega por `Authorization: Bearer
    <JWT>` (el mismo access token de la API). Se valida con
    JWTAuthentication y solo habilita tools del usuario en sesión.

Regla de seguridad: las tools my_* NUNCA reciben user_id/store/slug por
argumento — el usuario se resuelve del token de la request. El servidor
es ciego a la DB general: solo ve datos del dueño del token, y solo si
tiene plan pago vigente (mcp_user_access: básico/estándar/premium).

Uso:
    venv/Scripts/python.exe McpApp/fastmcp_server.py            # stdio
    venv/Scripts/python.exe McpApp/fastmcp_server.py http 8100  # HTTP :8100/mcp
"""

import os
import sys
from pathlib import Path

BASE_DIR    =   Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')

import django  # noqa: E402

django.setup()

from mcp.server.fastmcp import Context, FastMCP  # noqa: E402
from mcp.server.fastmcp.exceptions import ToolError  # noqa: E402

from McpApp.domains.skills.services import (  # noqa: E402
    call_tool,
    mcp_user_access,
)

mcp =   FastMCP(
    'davent',
    instructions = (
        'Servidor MCP de DAVENT. Las tools my_* devuelven datos EXCLUSIVOS '
        'del usuario autenticado por Bearer JWT con plan pago vigente; '
        'nunca aceptan identificadores de otros usuarios.'
    ),
)

DENIED  =   'Se requiere sesión con plan pago vigente (básico, estándar o premium).'


def _session_user(ctx : Context):
    """Resuelve el User desde el Bearer JWT de la request HTTP. En stdio
    (o sin header) devuelve None — nunca hay fallback a otro usuario."""
    request =   getattr(getattr(ctx, 'request_context', None), 'request', None)
    headers =   getattr(request, 'headers', None) or {}
    token   =   (headers.get('authorization') or headers.get('Authorization') or '')
    if not token.startswith('Bearer '):
        return None
    from rest_framework.request import Request
    from rest_framework.test import APIRequestFactory
    from rest_framework_simplejwt.authentication import JWTAuthentication
    try:
        django_request  =   APIRequestFactory().get('/')
        django_request.META['HTTP_AUTHORIZATION']   =   token
        result          =   JWTAuthentication().authenticate(Request(django_request))
        return result[0] if result else None
    except Exception:
        return None


def _require_user(ctx : Context):
    user    =   _session_user(ctx)
    if not mcp_user_access(user):
        raise ToolError(DENIED)
    return user


#=========================================
# CATÁLOGO PÚBLICO (solo lectura)
#=========================================
@mcp.tool()
def search_design_styles(query : str = '', categoria : str = '', limit : int = 10) -> dict:
    """Búsqueda de estilos de diseño por texto libre, categoría y tags."""
    return call_tool('search_design_styles', {'query': query, 'categoria': categoria, 'limit': limit})


@mcp.tool()
def design_catalog_summary(limit : int = 50) -> dict:
    """Catálogo compacto de estilos (slug, nombre, categoría, tags)."""
    return call_tool('design_catalog_summary', {'limit': limit})


@mcp.tool()
def get_design_style(slug : str) -> dict:
    """Estilo completo por slug: tokens de diseño y bloques HTML."""
    return call_tool('get_design_style', {'slug': slug})


#=========================================
# USUARIO EN SESIÓN (ciego al resto de la DB)
#=========================================
@mcp.tool()
def my_profile(ctx : Context) -> dict:
    """TU perfil de cuenta: email, negocio, condición fiscal, ubicación y verificaciones."""
    return call_tool('my_profile', {}, user = _require_user(ctx))


@mcp.tool()
def my_plan_summary(ctx : Context) -> dict:
    """TU plan vigente: nombre, precio, estado y vencimiento."""
    return call_tool('my_plan_summary', {}, user = _require_user(ctx))


@mcp.tool()
def my_payments(ctx : Context, limit : int = 10) -> dict:
    """TUS últimos pagos: monto, estado y fecha."""
    return call_tool('my_payments', {'limit': limit}, user = _require_user(ctx))


@mcp.tool()
def my_invoices(ctx : Context, limit : int = 10) -> dict:
    """TUS últimas facturas: tipo, número, total y estado ARCA."""
    return call_tool('my_invoices', {'limit': limit}, user = _require_user(ctx))


@mcp.tool()
def my_store_summary(ctx : Context) -> dict:
    """Resumen de TU tienda: slug, publicación y conteos."""
    return call_tool('my_store_summary', {}, user = _require_user(ctx))


@mcp.tool()
def my_store_visits(ctx : Context, days : int = 30) -> dict:
    """Visitas de TU web pública en los últimos N días (máx 90)."""
    return call_tool('my_store_visits', {'days': days}, user = _require_user(ctx))


@mcp.tool()
def search_my_products(ctx : Context, query : str = '', limit : int = 10) -> dict:
    """Busca productos SOLO en TU catálogo (nombre/descripción)."""
    return call_tool('search_my_products', {'query': query, 'limit': limit}, user = _require_user(ctx))


@mcp.tool()
def list_my_categories(ctx : Context) -> dict:
    """TUS categorías con cantidad de productos."""
    return call_tool('list_my_categories', {}, user = _require_user(ctx))


@mcp.tool()
def list_my_brands(ctx : Context) -> dict:
    """TUS marcas con cantidad de productos."""
    return call_tool('list_my_brands', {}, user = _require_user(ctx))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'http':
        port    =   int(sys.argv[2]) if len(sys.argv) > 2 else 8100
        mcp.run(transport = 'streamable-http', host = '127.0.0.1', port = port)
    else:
        mcp.run(transport = 'stdio')
