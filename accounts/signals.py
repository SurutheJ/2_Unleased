"""
Keep UnleasedUser.edu_email in sync with the login email.

Signup (username/password) and Google login (A5 Part 2) only fill in the
standard `email` field. Our model also has a unique `edu_email`, so without
this, every new signup would be saved with an empty edu_email and the second
one would crash on the unique constraint.

Rule: any email may sign up, but only .edu addresses count as verified
students (is_edu_verified=True).
"""

from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import UnleasedUser


@receiver(pre_save, sender=UnleasedUser)
def sync_edu_email(sender, instance, **kwargs):
    if instance.email:
        instance.email = instance.email.strip().lower()
    if not instance.edu_email and instance.email:
        instance.edu_email = instance.email
    if not instance.edu_email:
        instance.edu_email = None          # store NULL, never ""
    if instance.edu_email and instance.edu_email.endswith('.edu'):
        instance.is_edu_verified = True
