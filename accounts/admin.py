from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import UnleasedUser, UserReview


@admin.register(UnleasedUser)
class UnleasedUserAdmin(UserAdmin):
    """Admin view for student accounts — shows verification status and role at a glance."""

    list_display = [
        'username', 'edu_email', 'get_full_name',
        'role', 'is_edu_verified', 'response_rate', 'date_joined',
    ]
    list_filter = ['role', 'is_edu_verified', 'sleep_schedule', 'cleanliness']
    search_fields = ['username', 'edu_email', 'first_name', 'last_name']
    ordering = ['-date_joined']

    # Add Unleased-specific fields to the UserAdmin fieldsets
    fieldsets = UserAdmin.fieldsets + (
        ('Unleased Profile', {
            'fields': ('role', 'edu_email', 'is_edu_verified', 'bio', 'response_rate'),
        }),
        ('Lifestyle Preferences', {
            'fields': ('sleep_schedule', 'cleanliness', 'noise_level', 'guests_policy', 'pets_ok'),
            'classes': ('collapse',),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Unleased Info', {
            'fields': ('edu_email', 'role'),
        }),
    )


@admin.register(UserReview)
class UserReviewAdmin(admin.ModelAdmin):
    """Admin view for the trust/review system."""

    list_display = ['reviewer', 'reviewee', 'rating', 'created_at']
    list_filter = ['rating']
    search_fields = ['reviewer__username', 'reviewee__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
