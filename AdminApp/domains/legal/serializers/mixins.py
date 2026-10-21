
from rest_framework import serializers
from AdminApp.domains.legal.services import CreateContentReportQuery

"""

Configuramos los mixins para el dominio legal

"""

#=================================
# CONTENT REPORT VALIDATE
#=================================
class ContentReportValidate:
    def validate(self, attrs):
        kind            =   attrs.get('kind')
        original_work   =   attrs.get('original_work')
        errors          =   {}
        if kind in ('COPYRIGHT', 'TRADEMARK') and not original_work:
            errors['original_work'] =   'Identificá la obra, imagen, texto o marca afectada'
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

#=================================
# CONTENT REPORT CREATE METHOD
#=================================
class ContentReportCreateMethod:
    def create(self, validated_data):
        request     =   self.context.get('request')
        user        =   request.user if request and request.user.is_authenticated else None
        return CreateContentReportQuery(validated_data, user)
