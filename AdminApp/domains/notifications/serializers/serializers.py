from rest_framework import serializers

from AdminApp.domains.notifications.models import ChangelogEntry, Notification

"""
Serializers del dominio notifications: payload mínimo (título, detalle,
fecha y destino) — el cliente nunca ve dedupe_key ni datos de otros.
"""

#=========================================
# NOTIFICATION SERIALIZER
#=========================================
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model   =   Notification
        fields  =   ['id', 'kind', 'title', 'body', 'target', 'read_at', 'created_at']


#=========================================
# CHANGELOG SERIALIZER
#=========================================
class ChangelogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model   =   ChangelogEntry
        fields  =   ['id', 'title', 'body', 'is_published', 'published_at', 'created_at']
        read_only_fields =   ['published_at', 'created_at']
