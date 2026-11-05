import os
from pathlib import Path
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
import django
django.setup()
from StoreApp.domains.design.models import DesignPattern
from StoreApp.domains.design.services.pattern_preview import preview_pattern
from StoreApp.domains.design.services.pattern_document import SURFACE_CSS

p = DesignPattern.objects.get(slug='calzado')
for theme in ('light', 'dark'):
    d = preview_pattern(p, theme=theme)
    html = ('<!doctype html><html lang=es data-ds-theme="%s" data-ds-surface="landing">'
            '<head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">'
            '<style>html,body{margin:0}%s%s</style></head><body>%s<script>%s</script></body></html>'
            % (theme, SURFACE_CSS, d['css'], d['html'], d['js']))
    Path('_tmp_%s.html' % theme).write_text(html, encoding='utf-8')
print('ok')
