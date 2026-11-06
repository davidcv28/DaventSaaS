from django.contrib import admin

from AdminApp.domains.notifications.models import ChangelogEntry, Notification

"""
Admin Django: el changelog se escribe acá (o vía POST /api/changelog/
del staff). Las notificaciones son de solo lectura — las genera el
sistema, no se editan a mano.
"""


@admin.register(ChangelogEntry)
class ChangelogEntryAdmin(admin.ModelAdmin):
    list_display        =   ('title', 'kind', 'position', 'is_published', 'published_at', 'created_at')
    list_filter         =   ('kind', 'is_published')
    search_fields       =   ('title', 'body')
    ordering            =   ('position', '-published_at', '-created_at')
    #La foto se sube vía POST /api/changelog/<id>/image/ (va a R2, no a MEDIA).


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display        =   ('user', 'kind', 'title', 'read_at', 'created_at')
    list_filter         =   ('kind', 'read_at')
    search_fields       =   ('user__username', 'title', 'body')
    readonly_fields     =   ('user', 'kind', 'dedupe_key', 'title', 'body', 'target', 'read_at', 'created_at', 'updated_at')
    ordering            =   ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj = None):
        return False
