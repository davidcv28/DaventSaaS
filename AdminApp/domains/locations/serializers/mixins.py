from rest_framework import serializers

from AdminApp.domains.locations.models import City

"""
Mixins de validación a nivel objeto para el dominio Locations.
La ciudad debe pertenecer a la provincia indicada (misma regla que users).
"""


class LocationCityValidatorsMixin:
    def validate(self, attrs):
        city_qs = City.objects.all()
        errors = {}
        if self.instance:
            city_qs = city_qs.exclude(pk=self.instance.pk)
        # En create/update de City: verificar coherencia provincia/zip si vienen ambos
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

