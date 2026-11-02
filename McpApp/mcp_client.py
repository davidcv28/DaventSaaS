#!/usr/bin/env python
"""
Cliente stdio del servidor MCP propio (davent-skills).

Prototipo mínimo: levanta `McpApp/mcp_server.py` como subproceso, negocia
el handshake (`initialize` + `notifications/initialized`) y despacha
`tools/list` / `tools/call` por JSON-RPC delimitado por líneas.

Uso:
    venv/Scripts/python.exe McpApp/mcp_client.py list
    venv/Scripts/python.exe McpApp/mcp_client.py call search_design_styles "{\\"query\\": \\"oscuro neon\\"}"
    venv/Scripts/python.exe McpApp/mcp_client.py demo
"""

import json
import subprocess
import sys
from pathlib import Path

BASE_DIR    =   Path(__file__).resolve().parent.parent
SERVER      =   [sys.executable, str(BASE_DIR / 'McpApp' / 'mcp_server.py')]


class McpClient:
    """Handshake + request/response sobre stdio (JSON-RPC por línea)."""

    def __init__(self):
        self.proc   =   subprocess.Popen(
            SERVER,
            stdin   =   subprocess.PIPE,
            stdout  =   subprocess.PIPE,
            stderr  =   subprocess.DEVNULL,
            text    =   True,
            cwd     =   str(BASE_DIR),
        )
        self._id    =   0
        self._request('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'mcp-client', 'version': '1.0.0'}})
        self._notify('notifications/initialized')

    # -- transporte ------------------------------------------------------
    def _next_id(self):
        self._id    +=  1
        return self._id

    def _send(self, payload):
        self.proc.stdin.write(json.dumps(payload, ensure_ascii = False) + '\n')
        self.proc.stdin.flush()

    def _read(self):
        line    =   self.proc.stdout.readline()
        if not line:
            raise RuntimeError('El servidor MCP cerró stdout.')
        return json.loads(line)

    def _request(self, method, params = None):
        msg_id  =   self._next_id()
        self._send({'jsonrpc': '2.0', 'id': msg_id, 'method': method, 'params': params or {}})
        response    =   self._read()
        if 'error' in response:
            raise RuntimeError(f"{response['error'].get('code')}: {response['error'].get('message')}")
        return response.get('result')

    def _notify(self, method, params = None):
        self._send({'jsonrpc': '2.0', 'method': method, 'params': params or {}})

    # -- API -------------------------------------------------------------
    def tools(self):
        return self._request('tools/list').get('tools', [])

    def call(self, name, arguments = None):
        result      =   self._request('tools/call', {'name': name, 'arguments': arguments or {}})
        content     =   (result or {}).get('content') or []
        #El server devuelve el payload como JSON dentro de un bloque text.
        for block in content:
            if block.get('type') == 'text':
                try:
                    return json.loads(block['text'])
                except (json.JSONDecodeError, TypeError):
                    return block['text']
        return result

    def close(self):
        try:
            self.proc.terminate()
            self.proc.wait(timeout = 5)
        except Exception:
            self.proc.kill()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def _demo(client):
    """Recorrido del prototipo: listar, buscar y aplicar un estilo."""
    tools   =   client.tools()
    print(f'{len(tools)} herramientas: ' + ', '.join(t["name"] for t in tools))
    hits    =   client.call('search_design_styles', {'query': 'oscuro neon gamer', 'limit': 3})
    styles  =   hits.get('styles') or []
    for s in styles:
        print(f"  {s.get('slug'):<28} {s.get('categoria', ''):<12} {', '.join((s.get('tags') or [])[:4])}")
    if styles:
        applied =   client.call('apply_design_style', {'slug': styles[0]['slug']})
        tokens  =   applied.get('tokens_diseno') or {}
        print(f"\napplied {styles[0]['slug']}: primary={tokens.get('primary')} font={tokens.get('font')}")


def main(argv):
    args    =   argv[1:]
    with McpClient() as client:
        if not args or args[0] == 'demo':
            _demo(client)
        elif args[0] == 'list':
            print(json.dumps(client.tools(), indent = 2, ensure_ascii = False))
        elif args[0] == 'call' and len(args) >= 2:
            params  =   json.loads(args[2]) if len(args) > 2 else {}
            print(json.dumps(client.call(args[1], params), indent = 2, ensure_ascii = False))
        else:
            print(__doc__)
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
