from rest_framework import serializers

from StoreApp.domains.design.models import DesignPattern, DesignStyle

"""

Serializers del dominio Design.

Lectura del catálogo para cualquier usuario autenticado; alta/edición
solo staff. El listado de patrones no manda HTML/CSS/JS (payload
grande): el detalle sí, que es lo que aplica el front.

"""
CODE_MAX        =   200_000
TOKENS_MAX_KEYS =   80

#=========================================
# VALIDACIONES COMUNES
#=========================================
def validate_tokens(value):
    if not isinstance(value, dict):
        raise serializers.ValidationError('Los tokens deben ser un objeto.')
    if len(value) > TOKENS_MAX_KEYS:
        raise serializers.ValidationError(f'Los tokens admiten hasta {TOKENS_MAX_KEYS} claves.')
    return value


def validate_layout(value):
    if not isinstance(value, dict):
        raise serializers.ValidationError('El layout debe ser un objeto por superficie.')
    return value


def validate_code(value, label):
    if len(value) > CODE_MAX:
        raise serializers.ValidationError(f'{label} supera el máximo de {CODE_MAX} caracteres.')
    return value

#=========================================
# DESIGN STYLE SERIALIZER (catálogo de temas)
#=========================================
class DesignStyleSerializer(serializers.ModelSerializer):
    tokens              =   serializers.JSONField(required = False)
    class Meta:
        model           =   DesignStyle
        fields          =   [
            'id', 'slug', 'nombre', 'categoria', 'descripcion', 'tier',
            'template', 'layout', 'layout_spec', 'page_theme', 'tokens', 'tags',
            'is_default', 'is_active', 'position', 'created_at', 'updated_at',
        ]
        read_only_fields    =   ['id', 'created_at', 'updated_at']
    def validate_tokens(self, value):
        return validate_tokens(value)
    def validate_layout(self, value):
        return validate_layout(value)
    def validate_page_theme(self, value):
        if value not in ('light', 'dark'):
            raise serializers.ValidationError('El modo debe ser light o dark.')
        return value
#=========================================
# DESIGN STYLE LIST SERIALIZER (payload mínimo del catálogo)
#=========================================
class DesignStyleListSerializer(serializers.ModelSerializer):
    class Meta:
        model           =   DesignStyle
        fields          =   [
            'id', 'slug', 'nombre', 'categoria', 'descripcion', 'tier',
            'template', 'layout', 'layout_spec', 'page_theme', 'tokens', 'tags',
            'is_default', 'is_active', 'position',
        ]
#=========================================
# DESIGN PATTERN SERIALIZER (detalle: patrón aplicable)
#=========================================
class DesignPatternSerializer(serializers.ModelSerializer):
    tokens              =   serializers.JSONField(required = False)
    style               =   serializers.SlugRelatedField(
        slug_field = 'slug',
        queryset = DesignStyle.objects.all(),
        required = False,
        allow_null = True,
    )
    class Meta:
        model           =   DesignPattern
        fields          =   [
            'id', 'slug', 'nombre', 'categoria', 'descripcion', 'tier',
            'template', 'layout', 'html', 'css', 'js', 'tokens', 'tags',
            'preview', 'style', 'is_default', 'is_active', 'position',
            'created_at', 'updated_at',
        ]
        read_only_fields    =   ['id', 'created_at', 'updated_at']
    def validate_tokens(self, value):
        return validate_tokens(value)
    def validate_layout(self, value):
        return validate_layout(value)
    def validate_html(self, value):
        return validate_code(value, 'El HTML')
    def validate_css(self, value):
        return validate_code(value, 'El CSS')
    def validate_js(self, value):
        return validate_code(value, 'El JS')
#=========================================
# DESIGN PATTERN LIST SERIALIZER (sin HTML/CSS/JS)
#=========================================
class DesignPatternListSerializer(serializers.ModelSerializer):
    style               =   serializers.SlugRelatedField(slug_field = 'slug', read_only = True)
    has_markup          =   serializers.SerializerMethodField()
    class Meta:
        model           =   DesignPattern
        fields          =   [
            'id', 'slug', 'nombre', 'categoria', 'descripcion', 'tier',
            'template', 'layout', 'tokens', 'tags', 'preview', 'style',
            'has_markup', 'is_default', 'is_active', 'position',
        ]
    def get_has_markup(self, obj):
        # El listado no manda HTML/CSS/JS; el front pide el detalle solo si
        # hay markup propio (diseño importado) para previsualizarlo.
        return bool(obj.html or obj.css or obj.js)
