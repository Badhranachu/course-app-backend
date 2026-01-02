from rest_framework.permissions import BasePermission

class IsStudent(BasePermission):
    def has_permission(self, request, view):
        print("USER:", request.user)
        print("AUTH:", request.user.is_authenticated)
        print("ROLE:", getattr(request.user, "role", None))

        return (
            request.user.is_authenticated
            and request.user.role == "student"
        )


class IsAdminUserRole(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "admin"
            and request.user.is_active
        )
