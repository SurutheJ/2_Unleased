from django.contrib import admin
from .models import Listing, VisitSlot, Inquiry, SavedListing


class VisitSlotInline(admin.TabularInline):
    """Inline slots so admins can see/add visit windows from within a listing."""
    model = VisitSlot
    extra = 1
    fields = ['slot_start', 'slot_end', 'seeker', 'is_booked', 'reminder_sent']
    readonly_fields = ['is_booked']


class InquiryInline(admin.TabularInline):
    """Inline inquiries so admins can see interest volume at a glance."""
    model = Inquiry
    extra = 0
    fields = ['seeker', 'status', 'created_at']
    readonly_fields = ['created_at']


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    """
    Main admin view for sublease listings.
    Designed to support admin verification workflow (confirming lease documents).
    """

    list_display = [
        'title', 'lister', 'monthly_rent', 'utilities_included',
        'status', 'is_property_verified', 'ai_parsed',
        'bedrooms', 'available_from', 'available_until',
        'view_count', 'save_count', 'inquiry_count',
    ]
    list_filter = [
        'status', 'is_property_verified', 'ai_parsed',
        'gender_preference', 'is_furnished', 'utilities_included',
    ]
    search_fields = ['title', 'lister__username', 'street_address', 'building_name']
    ordering = ['-created_at']
    readonly_fields = [
        'view_count', 'save_count', 'inquiry_count',
        'created_at', 'updated_at', 'ai_parsed', 'raw_whatsapp_text',
    ]
    date_hierarchy = 'available_from'
    inlines = [VisitSlotInline, InquiryInline]

    fieldsets = (
        ('Core Info', {
            'fields': ('lister', 'title', 'description', 'status'),
        }),
        ('Pricing', {
            'fields': ('monthly_rent', 'utilities_included'),
        }),
        ('Location', {
            'fields': (
                'building_name', 'street_address', 'unit_number',
                'city', 'state', 'zip_code',
            ),
        }),
        ('Unit Details', {
            'fields': (
                'bedrooms', 'bathrooms',
                'is_private_bedroom', 'is_private_bathroom', 'is_furnished',
                'has_in_unit_laundry', 'has_parking', 'has_balcony',
                'pets_allowed', 'ac_included',
            ),
        }),
        ('Availability & Preferences', {
            'fields': ('available_from', 'available_until', 'gender_preference'),
        }),
        ('Verification', {
            'fields': ('is_property_verified', 'lease_document', 'external_listing_url'),
        }),
        ('Engagement', {
            'fields': ('view_count', 'save_count', 'inquiry_count'),
            'classes': ('collapse',),
        }),
        ('AI Metadata', {
            'fields': ('ai_parsed', 'raw_whatsapp_text'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    actions = ['mark_verified', 'mark_filled']

    @admin.action(description='Mark selected listings as property-verified')
    def mark_verified(self, request, queryset):
        queryset.update(is_property_verified=True)

    @admin.action(description='Mark selected listings as filled')
    def mark_filled(self, request, queryset):
        queryset.update(status=Listing.Status.FILLED)


@admin.register(VisitSlot)
class VisitSlotAdmin(admin.ModelAdmin):
    """Admin view for managing visit scheduling slots."""

    list_display = ['listing', 'slot_start', 'slot_end', 'seeker', 'is_booked', 'reminder_sent']
    list_filter = ['is_booked', 'reminder_sent']
    search_fields = ['listing__title', 'seeker__username']
    ordering = ['slot_start']


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    """Admin view for seeker inquiries — useful for monitoring platform activity."""

    list_display = ['seeker', 'listing', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['seeker__username', 'listing__title']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SavedListing)
class SavedListingAdmin(admin.ModelAdmin):
    """Admin view for saved/favorited listings."""

    list_display = ['seeker', 'listing', 'saved_at']
    search_fields = ['seeker__username', 'listing__title']
    ordering = ['-saved_at']
