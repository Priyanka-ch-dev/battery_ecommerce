from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()

class IsAdminUserOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.ADMIN)

class IsSellerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in [User.Role.SELLER, User.Role.ADMIN])

class IsCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.CUSTOMER)

class IsProductOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners of a product to edit it.
    Assumes the model instance has a `seller` attribute.
    """
    def has_object_permission(self, request, view, obj):
        # Admin can always access
        if request.user.role == User.Role.ADMIN:
            return True
        
        # Check if user is a SELLER and owns the product
        if request.user.role == User.Role.SELLER:
            try:
                return obj.seller == request.user.seller_profile
            except AttributeError:
                return False
        
        return False
