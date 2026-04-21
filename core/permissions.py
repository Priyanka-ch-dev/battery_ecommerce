from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()

class IsAdminUser(permissions.BasePermission):
    """
    Allows access only to Admin users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.ADMIN)

class IsDeliveryPerson(permissions.BasePermission):
    """
    Allows access only to Approved Delivery (Seller) users.
    """
    def has_permission(self, request, view):
        is_seller = bool(request.user and request.user.is_authenticated and request.user.role == User.Role.SELLER)
        if not is_seller:
            return False
        # Check if the associated SellerProfile is approved
        try:
            return request.user.seller_profile.is_approved
        except AttributeError:
            return False

class IsCustomer(permissions.BasePermission):
    """
    Allows access only to Customer users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.CUSTOMER)

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allows write access to Admins and read access to others.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.ADMIN)

class IsAdminOrDeliveryPerson(permissions.BasePermission):
    """
    Allows access to Admins or Approved Delivery staff.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
            
        if request.user.role == User.Role.ADMIN:
            return True
            
        if request.user.role == User.Role.SELLER:
            try:
                return request.user.seller_profile.is_approved
            except AttributeError:
                return False
                
        return False

class IsApprovedSeller(permissions.BasePermission):
    """
    Allows access only to Sellers who have been approved by an Admin.
    """
    def has_permission(self, request, view):
        is_seller = bool(request.user and request.user.is_authenticated and request.user.role == User.Role.SELLER)
        if not is_seller:
            return False
        
        # Check if the associated SellerProfile is approved
        try:
            return request.user.seller_profile.is_approved
        except AttributeError:
            return False

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object (or admins) to edit it.
    Checks for `user` attribute or `cart.user` attribute.
    """
    def has_object_permission(self, request, view, obj):
        # Admins can do anything
        if request.user and request.user.is_authenticated and request.user.role == User.Role.ADMIN:
            return True
            
        # Check ownership (direct user attribute)
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
            
        # Check ownership (via cart)
        if hasattr(obj, 'cart') and hasattr(obj.cart, 'user') and obj.cart.user == request.user:
            return True
            
        return False
