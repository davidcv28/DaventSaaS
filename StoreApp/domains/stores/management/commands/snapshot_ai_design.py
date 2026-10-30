import json
from pathlib import Path

from django.core.management import BaseCommand

from StoreApp.domains.stores.models import Store
from StoreApp.domains.stores.services.ai_design import generate as generate_ai_design


class Command(BaseCommand):
    help = (
        'Guarda una snapshot reproducible de "Diseñar con IA" (payload + seed + '
        'propuestas) para el golden set de regresión visual (5.4).'
    )

    def add_arguments(self, parser):
        parser.add_argument('--store', required = True, help = 'Slug de la tienda.')
        parser.add_argument('--payload', default = '{}', help = 'Entrevista en JSON.')
        parser.add_argument('--out', default = 'docs/qa/ai_design', help = 'Carpeta de salida.')

    def handle(self, *args, **options):
        try:
            payload = json.loads(options['payload'])
        except json.JSONDecodeError as error:
            self.stderr.write(self.style.ERROR(f'Payload inválido: {error}'))
            return
        store   =   Store.objects.filter(slug = options['store']).first()
        if store is None:
            self.stderr.write(self.style.ERROR(f'No existe la tienda {options["store"]}.'))
            return
        data    =   generate_ai_design(store, payload)
        folder  =   Path(options['out'])
        folder.mkdir(parents = True, exist_ok = True)
        target  =   folder / f'{store.slug}-{data["seed"]}.json'
        target.write_text(
            json.dumps({'payload': payload, 'result': data}, ensure_ascii = False, indent = 2),
            encoding = 'utf-8',
        )
        self.stdout.write(self.style.SUCCESS(f'Snapshot guardada en {target} ({len(data["proposals"])} propuestas).'))
