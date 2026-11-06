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
    image_url   =   serializers.SerializerMethodField()

    class Meta:
        model   =   ChangelogEntry
        fields  =   [
            'id', 'kind', 'title', 'summary', 'body', 'features', 'icon',
            'image_key', 'image_url', 'position',
            'is_published', 'published_at', 'created_at',
        ]
        read_only_fields =   ['image_key', 'published_at', 'created_at']

    def get_image_url(self, obj):
        if not obj.image_key:
            return None
        from StoreApp.domains.stores.services.storage import object_url
        return object_url(obj.image_key)
