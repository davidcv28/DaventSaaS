"""
Cifra (AES-256-GCM) un secreto fiscal para pegarlo en el .env, o lo re-cifra
con la llave activa tras una rotación. El plaintext se lee de un archivo o
stdin — nunca de argv (quedaría en el historial de la shell).

  manage.py encrypt_secret --purpose AFIP_KEY --file clave.key
  manage.py encrypt_secret --purpose AFIP_KEY --rotate "enc:v1:old:..."
  manage.py encrypt_secret --gen-master-key k2
"""
import sys

from django.core.management.base import BaseCommand, CommandError

from AdminApp.domains.invoices.services import vault


class Command(BaseCommand):
    help = 'Cifra o rota secretos fiscales (AFIP_KEY / AFIP_CERT) con AES-256-GCM'

    def add_arguments(self, parser):
        parser.add_argument('--purpose', choices = ['AFIP_KEY', 'AFIP_CERT', 'AFIP_KEY_PASSPHRASE'])
        parser.add_argument('--file', help = 'Archivo PEM a cifrar (default: stdin)')
        parser.add_argument('--rotate', help = 'Token enc:v1:... a re-cifrar con la llave activa')
        parser.add_argument('--gen-master-key', metavar = 'KID', help = 'Genera una llave maestra nueva')

    def handle(self, *args, **opts):
        if opts['gen_master_key']:
            self.stdout.write(vault.generate_master_key(opts['gen_master_key']))
            return
        if not opts['purpose']:
            raise CommandError('--purpose es obligatorio')
        try:
            if opts['rotate']:
                self.stdout.write(vault.rotate_secret(opts['rotate'], opts['purpose']))
                return
            if opts['file']:
                with open(opts['file'], 'rb') as fh:
                    data    =   fh.read()
            else:
                data    =   sys.stdin.buffer.read()
            if not data.strip():
                raise CommandError('Entrada vacía')
            self.stdout.write(vault.encrypt_secret(data, opts['purpose']))
        except vault.VaultError as exc:
            raise CommandError(str(exc))
