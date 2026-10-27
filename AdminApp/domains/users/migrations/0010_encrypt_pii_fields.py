# Migración de datos: cifra en reposo la PII fiscal/de contacto del perfil.
#
# Estrategia (reversible y reanudable):
# - Las 6 columnas de texto pasan a TEXT (el token enc:v1: supera max_length
#   original) y quedan encriptadas AES-256-GCM con su purpose propio (AAD).
# - document_hash/phone_hash (HMAC-SHA256, SECRETS_HASH_KEY) reciben la
#   unicidad/búsqueda por igualdad que antes tenía el texto plano.
# - El RunPython procesa por lotes keyset-paginados (id > último) y solo
#   reescribe lo que siga en claro -> re-ejecutarlo o reintentar tras un corte
#   no rompe nada; el reverse descifra y deja el estado previo.
from django.db import migrations, models

import AdminApp.domains.users.models.fields as profile_fields

ENCRYPTED_FIELDS    =   ('document', 'phone', 'first_name', 'last_name', 'address', 'business_name')
BATCH_SIZE          =   500


def _row_plaintexts(record, purposes):
    """Devuelve el valor en claro de cada columna (descifrando tokens viejos)."""
    from AdminApp.domains.invoices.services import vault
    plain = {}
    for name in ENCRYPTED_FIELDS:
        raw = record[name]
        if raw in (None, ''):
            plain[name] = raw
        elif vault.is_encrypted(raw):
            plain[name] = vault.decrypt_secret(raw, purposes[name]).decode('utf-8')
        else:
            plain[name] = raw
    return plain


def encrypt_existing(apps, schema_editor):
    from AdminApp.domains.invoices.services import vault

    UserProfile = apps.get_model('users', 'UserProfile')
    table       = UserProfile._meta.db_table
    id_col      = UserProfile._meta.pk.column
    purposes    = {name: UserProfile._meta.get_field(name).purpose for name in ENCRYPTED_FIELDS}
    columns     = ', '.join((id_col,) + ENCRYPTED_FIELDS)
    last_id     = 0
    with schema_editor.connection.cursor() as cursor:
        while True:
            cursor.execute(
                f'SELECT {columns} FROM {table} WHERE {id_col} > %s ORDER BY {id_col} LIMIT %s',
                [last_id, BATCH_SIZE],
            )
            rows    =   cursor.fetchall()
            if not rows:
                break
            for row in rows:
                record          =   dict(zip(('id',) + ENCRYPTED_FIELDS, row))
                last_id         =   record['id']
                plain           =   _row_plaintexts(record, purposes)
                #Solo se reescribe lo que sigue en claro -> idempotente.
                updates, params =   [], []
                for name in ENCRYPTED_FIELDS:
                    if plain[name] in (None, '') or vault.is_encrypted(record[name]):
                        continue
                    updates.append(f'{name} = %s')
                    params.append(vault.encrypt_secret(str(plain[name]).encode('utf-8'), purposes[name]))
                doc_hash        =   profile_fields.digest_for('document', plain['document']) if plain['document'] else None
                phone_hash      =   profile_fields.digest_for('phone', plain['phone']) if plain['phone'] else None
                updates        +=   ['document_hash = %s', 'phone_hash = %s']
                params         +=   [doc_hash, phone_hash]
                cursor.execute(
                    f'UPDATE {table} SET {", ".join(updates)} WHERE {id_col} = %s',
                    params + [record['id']],
                )


def decrypt_back(apps, schema_editor):
    """Reverse: devuelve texto plano a las columnas (las *_hash las droppea el
    rollback de schema, que corre después por el orden inverso de las ops)."""
    from AdminApp.domains.invoices.services import vault

    UserProfile = apps.get_model('users', 'UserProfile')
    table       = UserProfile._meta.db_table
    id_col      = UserProfile._meta.pk.column
    purposes    = {name: UserProfile._meta.get_field(name).purpose for name in ENCRYPTED_FIELDS}
    columns     = ', '.join((id_col,) + ENCRYPTED_FIELDS)
    last_id     = 0
    with schema_editor.connection.cursor() as cursor:
        while True:
            cursor.execute(
                f'SELECT {columns} FROM {table} WHERE {id_col} > %s ORDER BY {id_col} LIMIT %s',
                [last_id, BATCH_SIZE],
            )
            rows    =   cursor.fetchall()
            if not rows:
                break
            for row in rows:
                record          =   dict(zip(('id',) + ENCRYPTED_FIELDS, row))
                last_id         =   record['id']
                updates, params =   [], []
                for name in ENCRYPTED_FIELDS:
                    raw     =   record[name]
                    if raw and vault.is_encrypted(raw):
                        updates.append(f'{name} = %s')
                        params.append(vault.decrypt_secret(raw, purposes[name]).decode('utf-8'))
                if updates:
                    cursor.execute(
                        f'UPDATE {table} SET {", ".join(updates)} WHERE {id_col} = %s',
                        params + [record['id']],
                    )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_remove_userprofile_whatsapp_digest_and_more'),
    ]

    operations = [
        #El índice compuesto viejo apuntaba al texto plano.
        migrations.RemoveIndex(
            model_name = 'userprofile',
            name = 'idx_type_document',
        ),
        migrations.AddField(
            model_name = 'userprofile',
            name = 'document_hash',
            field = models.CharField(blank = True, editable = False, max_length = 64, null = True, unique = True, verbose_name = 'Huella del documento'),
        ),
        migrations.AddField(
            model_name = 'userprofile',
            name = 'phone_hash',
            field = models.CharField(blank = True, editable = False, max_length = 64, null = True, unique = True, verbose_name = 'Huella del celular'),
        ),
        migrations.AlterField(
            model_name = 'userprofile',
            name = 'document',
            field = profile_fields.EncryptedCharField(aad = 'UserProfile.document', blank = True, max_length = 11, verbose_name = 'Documento'),
        ),
        migrations.AlterField(
            model_name = 'userprofile',
            name = 'phone',
            field = profile_fields.EncryptedCharField(aad = 'UserProfile.phone', blank = True, max_length = 16, verbose_name = 'Número telefonico'),
        ),
        migrations.AlterField(
            model_name = 'userprofile',
            name = 'first_name',
            field = profile_fields.EncryptedCharField(aad = 'UserProfile.first_name', blank = True, max_length = 150, verbose_name = 'Nombre'),
        ),
        migrations.AlterField(
            model_name = 'userprofile',
            name = 'last_name',
            field = profile_fields.EncryptedCharField(aad = 'UserProfile.last_name', blank = True, max_length = 150, verbose_name = 'Apellido'),
        ),
        migrations.AlterField(
            model_name = 'userprofile',
            name = 'address',
            field = profile_fields.EncryptedCharField(aad = 'UserProfile.address', blank = True, max_length = 255, verbose_name = 'Domicilio'),
        ),
        migrations.AlterField(
            model_name = 'userprofile',
            name = 'business_name',
            field = profile_fields.EncryptedCharField(aad = 'UserProfile.business_name', blank = True, max_length = 255, verbose_name = 'Nombre comercial'),
        ),
        migrations.AddIndex(
            model_name = 'userprofile',
            index = models.Index(fields = ['type_document', 'document_hash'], name = 'idx_type_document'),
        ),
        migrations.RunPython(encrypt_existing, decrypt_back),
    ]
