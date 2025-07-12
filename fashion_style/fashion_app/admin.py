from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, OTP

class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_verified', 'is_disabled', 'date_created')
    list_filter = ('role', 'is_verified', 'is_disabled', 'date_created')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    ordering = ('email',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('phone_number', 'role', 'is_verified', 'is_disabled', 'profile_image', 
                      'conversation', 'outfits', 'is_anonymous')
        }),
    )

admin.site.register(User, CustomUserAdmin)
admin.site.register(OTP)