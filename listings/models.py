from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.urls import reverse
from django.utils import timezone


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

    def get_absolute_url(self):
        """
        Canonical URL for this listing's detail page.
        Templates call {{ listing.get_absolute_url }} instead of building
        the URL by hand, so if the URL pattern ever changes, only
        listings/urls.py needs to change.
        """
        return reverse('listings:detail', kwargs={'pk': self.pk})

    @property
    def popularity_score(self):
        """Simple weighted score for ranking listings on the homepage feed."""
        return (self.view_count * 1) + (self.save_count * 3) + (self.inquiry_count * 5)

    @property
    def photos(self):
        """Uploaded photos, in upload order (works with prefetch_related('media'))."""
        return [m for m in self.media.all() if m.kind == 'photo']

    @property
    def videos(self):
        return [m for m in self.media.all() if m.kind == 'video']

    @property
    def cover_photo(self):
        """First uploaded photo, used as the card and page image (None if there are none)."""
        photos = self.photos
        return photos[0] if photos else None


class ListingMedia(models.Model):
    """A photo or a short video attached to a listing (A9).

    Files live under MEDIA_ROOT/listing_media/. When a row is deleted (on its
    own, or because its listing was deleted) the file is removed from disk
    too, by the post_delete handler below, so the disk quota is not wasted.
    """

    class Kind(models.TextChoices):
        PHOTO = 'photo', 'Photo'
        VIDEO = 'video', 'Video'

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='media')
    kind = models.CharField(max_length=5, choices=Kind.choices)
    file = models.FileField(upload_to='listing_media/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at', 'id']
        verbose_name = 'Listing photo or video'
        verbose_name_plural = 'Listing photos and videos'

    def __str__(self):
        return f"{self.get_kind_display()} for listing {self.listing_id}"


@receiver(post_delete, sender=ListingMedia)
def delete_media_file(sender, instance, **kwargs):
    """Remove the file from disk when its ListingMedia row is deleted."""
    if instance.file:
        instance.file.delete(save=False)


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


class AIRequestLog(models.Model):
    """
    One row per request to the AI listing assistant (A10): what happened, how
    long each step took, and what came out. It feeds the analytics dashboard
    at /listings/ai-dashboard/. It stores no message text and no contact
    details, only counts, timings, field names and outcome labels.

    Rows with is_simulated=True were generated by `seed_ai_logs --simulated`
    to give the dashboard volume that local testing cannot produce; the
    dashboard labels them and can filter them out.
    """

    class Outcome(models.TextChoices):
        SUCCESS = 'success', 'Success (200)'
        TOO_SHORT = 'too_short', 'Too short (400)'
        SUSPICIOUS = 'suspicious', 'Suspicious input (400)'
        UNPARSEABLE = 'unparseable', 'Unreadable model output (422)'
        RATE_LIMITED = 'rate_limited', 'Rate limited (429)'
        UNAVAILABLE = 'unavailable', 'Model unavailable (503)'

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='ai_requests',
    )
    outcome = models.CharField(max_length=14, choices=Outcome.choices)
    status_code = models.PositiveSmallIntegerField()

    # Timings in milliseconds. local_ms covers the local model call, gemini_ms
    # the description step; both are 0 when that step did not run.
    total_ms = models.FloatField(default=0)
    local_ms = models.FloatField(default=0)
    gemini_ms = models.FloatField(default=0)
    cold_start = models.BooleanField(
        default=False,
        help_text="True if this request had to load the model first (the one-time ~16-20 s cost).",
    )

    message_chars = models.PositiveIntegerField(default=0, help_text="Length of the cleaned message.")
    found_count = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Fields filled, 0 to 11.")
    blanked_fields = models.JSONField(
        default=list, blank=True,
        help_text="Fields the model filled in but validation blanked (grounding, range, date checks).",
    )
    description_source = models.CharField(max_length=10, blank=True, help_text="'gemini' or 'fallback'.")

    listing_created = models.BooleanField(default=False, help_text="The user turned this preview into a listing.")
    listing = models.ForeignKey(
        Listing, null=True, blank=True, on_delete=models.SET_NULL, related_name='ai_request_logs',
    )
    is_simulated = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'AI request log'
        verbose_name_plural = 'AI request logs'

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.outcome} ({self.total_ms:.0f} ms)"
