from django.contrib.auth.models import AbstractUser
from django.db import models


class UnleasedUser(AbstractUser):
    """
    Represents a verified UIUC student on Unleased.
    Extends Django's built-in User with campus-specific fields.
    Every person who signs up — whether listing or seeking — is an UnleasedUser.
    .edu verification is tracked here so the platform stays student-only.
    """

    class Role(models.TextChoices):
        LISTER = 'lister', 'Lister'
        SEEKER = 'seeker', 'Seeker'
        BOTH   = 'both',   'Both'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.SEEKER,
        help_text="Whether this user is listing a place, seeking one, or both.",
    )
    edu_email = models.EmailField(
        unique=True,
        help_text="Must be a .edu address. Used for university verification.",
    )
    is_edu_verified = models.BooleanField(
        default=False,
        help_text="Set to True once the .edu email link is confirmed.",
    )
    bio = models.TextField(
        blank=True,
        help_text="Short personal description shown on the user's public profile.",
    )

    # Lifestyle preference fields — used for roommate compatibility scoring
    sleep_schedule = models.CharField(
        max_length=20,
        choices=[('early', 'Early bird'), ('night', 'Night owl'), ('flexible', 'Flexible')],
        blank=True,
    )
    cleanliness = models.CharField(
        max_length=20,
        choices=[('very_clean', 'Very clean'), ('moderate', 'Moderate'), ('relaxed', 'Relaxed')],
        blank=True,
    )
    noise_level = models.CharField(
        max_length=20,
        choices=[('quiet', 'Quiet'), ('moderate', 'Moderate'), ('social', 'Social/loud')],
        blank=True,
    )
    guests_policy = models.CharField(
        max_length=20,
        choices=[('rarely', 'Rarely'), ('sometimes', 'Sometimes'), ('often', 'Often')],
        blank=True,
    )
    pets_ok = models.BooleanField(default=False)

    # Trust signals shown on profile
    response_rate = models.FloatField(
        default=0.0,
        help_text="Percentage of inquiries responded to within 24 hours (0–100).",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Unleased User'
        verbose_name_plural = 'Unleased Users'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.edu_email})"


class UserReview(models.Model):
    """
    Represents a post-sublease review left by one student about another.
    Builds the trust layer that informal WhatsApp channels completely lack.
    A reviewer can rate a reviewee once per completed sublease interaction.
    """

    reviewer = models.ForeignKey(
        UnleasedUser,
        on_delete=models.CASCADE,          # If reviewer deletes account, their reviews go too
        related_name='reviews_given',
    )
    reviewee = models.ForeignKey(
        UnleasedUser,
        on_delete=models.CASCADE,          # If reviewee deletes account, reviews about them go too
        related_name='reviews_received',
    )
    rating = models.PositiveSmallIntegerField(
        help_text="1–5 star rating.",
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['reviewer', 'reviewee'],
                name='unique_review_per_pair',
                # One review per reviewer→reviewee pair; prevents spam reviews
            )
        ]
        verbose_name = 'User Review'
        verbose_name_plural = 'User Reviews'

    def __str__(self):
        return f"{self.reviewer} → {self.reviewee} ({self.rating}★)"
