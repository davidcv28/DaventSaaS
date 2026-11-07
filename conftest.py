"""Puente pytest → Django.

La suite canónica corre con `manage.py test` (así está en CI). pytest solo
lo usa el IDE para el discovery del panel de Testing: sin `django.setup()`
los módulos `test_*.py` que importan modelos fallan en colección con
`AppRegistryNotReady`.
"""
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
django.setup()
