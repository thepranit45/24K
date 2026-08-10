from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    extra = 0
    fields = ['phone']


class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    list_display = ['username', 'email', 'first_name', 'last_name', 'get_phone', 'is_active', 'date_joined']

    def get_phone(self, obj):
        try:
            return obj.profile.phone or '—'
        except UserProfile.DoesNotExist:
            return '—'
    get_phone.short_description = 'Phone'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
