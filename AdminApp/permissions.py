from rest_framework.permissions import BasePermission
#ANONIMOUS PERMISSION (solo anónimos: el registro no admite usuarios autenticados)
class IsAnonimous(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return False
        return True