import json
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand

from StoreApp.domains.stores.site_theme import _SECTION_SPECS

"""

Fuente única del contrato site_theme: vuelca _SECTION_SPECS (backend) a un
JSON que el frontend puede diffear contra contract.js — hoy una clave nueva
(p. ej. typography.subheading) exige tocar _SECTION_SPECS + contract.js +
CSS a mano y el drift solo se nota cuando algo se descarta en silencio.

  manage.py export_contract [--out frontend/src/studio/contract-spec.json]

"""


class Command(BaseCommand):
    help = 'Exporta el contrato site_theme (_SECTION_SPECS) a JSON para el frontend.'

    def add_arguments(self, parser):
        parser.add_argument('--out', default = 'frontend/src/studio/contract-spec.json',
                            help = 'Destino del JSON (default: frontend/src/studio/contract-spec.json).')

    def handle(self, *args, **options):
        sections    =   {}
        for section, keys in _SECTION_SPECS.items():
            entry   =   {}
            if not isinstance(keys, dict):
                continue
            for key, descriptor in keys.items():
                if not isinstance(descriptor, tuple) or not descriptor:
                    continue
                kind            =   descriptor[0]
                item            =   {'kind': kind}
                if kind == 'enum' and len(descriptor) > 1:
                    item['values']  =   list(descriptor[1])
                elif kind == 'int' and len(descriptor) > 2:
                    item['min'], item['max']    =   descriptor[1], descriptor[2]
                entry[key]      =   item
            sections[section]   =   entry
        payload     =   {
            'generated_by'  :   'manage.py export_contract — no editar a mano',
            'sections'      :   sections,
        }
        out         =   Path(settings.BASE_DIR) / options['out']
        out.parent.mkdir(parents = True, exist_ok = True)
        out.write_text(json.dumps(payload, indent = 2, ensure_ascii = False) + '\n', encoding = 'utf-8')
        self.stdout.write(self.style.SUCCESS(f'Contrato exportado a {out}'))
