from django.contrib import admin
from .models import User, Address, Wishlist, State, City, ServiceableCity

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'email', 'role']
    search_fields = ['username', 'email']

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'city', 'state', 'address_type']

@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'state']
    list_filter = ['state']

@admin.register(ServiceableCity)
class ServiceableCityAdmin(admin.ModelAdmin):
    list_display = ['id', 'city', 'is_service_available']
    list_filter = ['is_service_available']
    search_fields = ['city__name']
