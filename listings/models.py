from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Listing(models.Model):
    """
    Represents a sublease listing posted by a UIUC student (the Lister).
    This is the core entity of Unleased — a structured, verified alternative
    to the WhatsApp messages students currently use to find subleases.
    Each listing has one owner, one address, and one availability window.
    """

    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        PENDING   = 'pending',   'Pending'
        FILLED    = 'filled',    'Filled'

    class GenderPreference(models.TextChoices):
        ANY     = 'any',     'Any'
        MALE    = 'male',    'Males only'
        FEMALE  = 'female',  'Females only'

    lister = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,          # Listing disappears if lister deletes account
        related_name='listings',
    )

    # --- Core listing info ---
    title = models.CharField(max_length=200)
    description = models.TextField(
        help_text="Full description. Can be AI-generated from a pasted WhatsApp message.",
    )
    monthly_rent = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    utilities_included = models.BooleanField(
        default=False,
        help_text="True if electricity, water, internet are all bundled into the rent.",
    )

    # --- Location (address stays private until inquiry accepted) ---
    building_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Public-facing building name shown before address is revealed.",
    )
    street_address = models.CharField(
        max_length=300,
        help_text="Full address — only revealed to seekers after an inquiry is accepted.",
    )
    unit_number = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100, default='Champaign')
    state = models.CharField(max_length=2, default='IL')
    zip_code = models.CharField(max_length=10, default='61820')

    # --- Unit specs ---
    bedrooms = models.PositiveSmallIntegerField()
    bathrooms = models.DecimalField(max_digits=3, decimal_places=1)
    is_private_bedroom = models.BooleanField(
        default=True,
        help_text="True if the subleasee gets a private, lockable bedroom.",
    )
    is_private_bathroom = models.BooleanField(default=False)
    is_furnished = models.BooleanField(default=False)

    # --- Amenities ---
    has_in_unit_laundry = models.BooleanField(default=False)
    has_parking = models.BooleanField(default=False)
    has_balcony = models.BooleanField(default=False)
    pets_allowed = models.BooleanField(default=False)
    ac_included = models.BooleanField(default=True)

    # --- Availability ---
    available_from = models.DateField()
    available_until = models.DateField()

    # --- Preferences & status ---
    gender_preference = models.CharField(
        max_length=10,
        choices=GenderPreference.choices,
        default=GenderPreference.ANY,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )

    # --- Trust & verification ---
    is_property_verified = models.BooleanField(
        default=False,
        help_text="True once the lister has uploaded proof of lease.",
    )
    lease_document = models.FileField(
        upload_to='lease_docs/',
        null=True,
        blank=True,
        help_text="Private document — only visible to admins for verification.",
    )
    external_listing_url = models.URLField(
        blank=True,
        help_text="Optional link to official property manager listing (e.g. Smile Living).",
    )

    # --- Engagement signals (used for popularity ranking) ---
    view_count = models.PositiveIntegerField(default=0)
    save_count = models.PositiveIntegerField(default=0)
    inquiry_count = models.PositiveIntegerField(default=0)

    # --- AI metadata ---
    ai_parsed = models.BooleanField(
        default=False,
        help_text="True if this listing was created via the WhatsApp message parser.",
    )
    raw_whatsapp_text = models.TextField(
        blank=True,
        help_text="Original pasted WhatsApp message stored for audit/re-parsing.",
    )

    saved_by_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='SavedListing',
        related_name='favorites',
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['lister', 'street_address', 'unit_number', 'available_from'],
                name='unique_listing_per_lister_unit_date',
                # Prevents a lister from accidentally posting the same unit/date twice
            )
        ]
        verbose_name = 'Listing'
        verbose_name_plural = 'Listings'

    def __str__(self):
        return f"{self.title} — ${self.monthly_rent}/mo ({self.status})"

    @property
    def popularity_score(self):
        """Simple weighted score for ranking listings on the homepage feed."""
        return (self.view_count * 1) + (self.save_count * 3) + (self.inquiry_count * 5)


class VisitSlot(models.Model):
    """
    Represents a single time window a Lister has opened for in-person visits.
    Seekers book from these slots rather than coordinating over WhatsApp text chains.
    Each slot belongs to exactly one listing and can be booked by at most one seeker.
    """

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,          # Slots disappear when a listing is removed
        related_name='visit_slots',
    )
    seeker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,         # Slot becomes open again if seeker deletes account
        null=True,
        blank=True,
        related_name='booked_visits',
    )
    slot_start = models.DateTimeField()
    slot_end = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    reminder_sent = models.BooleanField(
        default=False,
        help_text="True once the 24-hour reminder notification has been dispatched.",
    )

    class Meta:
        ordering = ['slot_start']
        constraints = [
            models.UniqueConstraint(
                fields=['listing', 'slot_start'],
                name='unique_slot_per_listing_time',
                # A listing cannot have two open slots starting at the same time
            )
        ]
        verbose_name = 'Visit Slot'
        verbose_name_plural = 'Visit Slots'

    def __str__(self):
        status = f"booked by {self.seeker}" if self.is_booked else "open"
        return f"{self.listing.title} @ {self.slot_start:%b %d, %Y %H:%M} ({status})"


class Inquiry(models.Model):
    """
    Represents a seeker's formal expression of interest in a listing.
    Tracks the conversation thread between seeker and lister.
    When accepted, the listing's address is revealed to the seeker.
    An inquiry is the gateway to a visit — seekers can't book a slot without one.
    """

    class Status(models.TextChoices):
        PENDING  = 'pending',  'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        DECLINED = 'declined', 'Declined'

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='inquiries',
    )
    seeker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inquiries_sent',
    )
    message = models.TextField(
        help_text="Seeker's initial message to the lister.",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['listing', 'seeker'],
                name='unique_inquiry_per_seeker_listing',
                # A seeker can only send one inquiry per listing
            )
        ]
        verbose_name = 'Inquiry'
        verbose_name_plural = 'Inquiries'

    def __str__(self):
        return f"{self.seeker} → {self.listing.title} ({self.status})"


class SavedListing(models.Model):
    """
    Represents a seeker saving/favoriting a listing for later reference.
    Used to drive save_count on Listing and to power the Favorites tab
    in the UI. A seeker can only save a given listing once.
    """

    seeker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_listings',
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='saved_by',
    )
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-saved_at']
        constraints = [
            models.UniqueConstraint(
                fields=['seeker', 'listing'],
                name='unique_save_per_seeker_listing',
            )
        ]
        verbose_name = 'Saved Listing'
        verbose_name_plural = 'Saved Listings'

    def __str__(self):
        return f"{self.seeker} saved → {self.listing.title}"
