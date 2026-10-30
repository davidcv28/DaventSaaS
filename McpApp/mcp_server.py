#!/usr/bin/env python
"""
Servidor MCP (stdio) del dominio skills de DAVENT.

Transporte JSON-RPC delimitado por líneas, el que usan los clientes MCP
locales (Claude Desktop/Code, agentes de terminal). Cada request corre
contra la base real del proyecto.

Uso:
    venv/Scripts/python.exe McpApp/mcp_server.py
"""

import json
import os
import sys
from pathlib import Path

BASE_DIR    =   Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')

import django  # noqa: E402

django.setup()

from McpApp.domains.skills.services import (  # noqa: E402
    SERVER_NAME,
    SERVER_VERSION,
    call_tool,
    tools_list,
)


def _result(msg_id, result):
    return {'jsonrpc': '2.0', 'id': msg_id, 'result': result}


def _error(msg_id, code, message):
    return {'jsonrpc': '2.0', 'id': msg_id, 'error': {'code': code, 'message': message}}


def handle(payload : dict) -> dict | None:
    method  =   payload.get('method', '')
    msg_id  =   payload.get('id')
    params  =   payload.get('params') or {}
    #Notificaciones (sin id) no llevan respuesta.
    if msg_id is None and method.startswith('notifications/'):
        return None
    if method == 'initialize':
        return _result(msg_id, {
            'protocolVersion'   :   '2024-11-05',
            'capabilities'      :   {'tools': {}},
            'serverInfo'        :   {'name': SERVER_NAME, 'version': SERVER_VERSION},
        })
    if method == 'tools/list':
        return _result(msg_id, {'tools': tools_list()})
    if method == 'tools/call':
        try:
            data    =   call_tool(params.get('name', ''), params.get('arguments') or {})
        except ValueError as exc:
            return _error(msg_id, -32602, str(exc))
        except Exception as exc:  # noqa: BLE001 — nunca tumbar el servidor
            return _error(msg_id, -32603, f'Error interno: {exc}')
        return _result(msg_id, {'content': [{'type': 'text', 'text': json.dumps(data, ensure_ascii = False)}]})
    if method == 'ping':
        return _result(msg_id, {})
    return _error(msg_id, -32601, f'Método no soportado: {method}')


def main():
    for line in sys.stdin:
        line    =   line.strip()
        if not line:
            continue
        try:
            payload =   json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps(_error(None, -32700, 'JSON inválido')) + '\n')
            sys.stdout.flush()
            continue
        response    =   handle(payload)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii = False) + '\n')
            sys.stdout.flush()


if __name__ == '__main__':
    main()
