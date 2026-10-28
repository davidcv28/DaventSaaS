"""
Re-cifra los campos cifrados de UserProfile con la llave maestra ACTIVA.

Uso tras rotar el keyring (agregar la nueva llave adelante en
SECRETS_MASTER_KEYS, dejando las viejas para descifrar):

    manage.py rotate_encrypted_fields [--batch 500]

Es idempotente y reanudable: solo reescribe las filas cuyo token aún está en
claro o fue cifrado con un kid que ya no es el activo. Una vez que el comando
no reporta `rotated`, la llave vieja se puede retirar del keyring.
"""
from django.core.management.base import BaseCommand
from django.db import connection

from AdminApp.domains.invoices.services import vault
from AdminApp.domains.users.models import UserProfile


class Command(BaseCommand):
    help = 'Re-cifra los EncryptedCharField de UserProfile con la llave activa del keyring'

    ENCRYPTED_FIELDS    =   ('document', 'phone', 'first_name', 'last_name', 'address', 'business_name')

    def add_arguments(self, parser):
        parser.add_argument('--batch', type = int, default = 500, help = 'Filas por lote (default 500)')

    def handle(self, *args, **opts):
        batch       =   max(int(opts['batch']), 1)
        table       =   UserProfile._meta.db_table
        id_col      =   UserProfile._meta.pk.column
        purposes    =   {name: UserProfile._meta.get_field(name).purpose for name in self.ENCRYPTED_FIELDS}
        active      =   vault.active_kid()
        columns     =   ', '.join((id_col,) + self.ENCRYPTED_FIELDS)
        total       =   rotated   =   0
        last_id     =   0
        with connection.cursor() as cursor:
            while True:
                cursor.execute(
                    f'SELECT {columns} FROM {table} WHERE {id_col} > %s ORDER BY {id_col} LIMIT %s',  # nosec B608: tabla/columnas salen de _meta y los valores van parametrizados
                    [last_id, batch],
                )
                rows    =   cursor.fetchall()
                if not rows:
                    break
                for row in rows:
                    record      =   dict(zip(('id',) + self.ENCRYPTED_FIELDS, row))
                    last_id     =   record['id']
                    total      +=   1
                    updates, params =   [], []
                    for name in self.ENCRYPTED_FIELDS:
                        raw     =   record[name]
                        if raw in (None, ''):
                            continue
                        if not vault.is_encrypted(raw):
                            #Resto de una migración cortada: se cifra de una.
                            updates.append(f'{name} = %s')
                            params.append(vault.encrypt_secret(str(raw).encode('utf-8'), purposes[name]))
                        elif vault.token_kid(raw) != active:
                            updates.append(f'{name} = %s')
                            params.append(vault.rotate_secret(raw, purposes[name]))
                    if updates:
                        rotated    +=   1
                        cursor.execute(
                            f'UPDATE {table} SET {", ".join(updates)} WHERE {id_col} = %s',  # nosec B608: tabla/columnas salen de _meta y los valores van parametrizados
                            params + [record['id']],
                        )
        self.stdout.write(self.style.SUCCESS(
            f'Listo: {total} perfiles revisados, {rotated} re-cifrados con kid "{active}".'
        ))
