"""
seed_data.py — Realistic test data for Unleased
Run with: python seed_data.py
Populates: UnleasedUser, UserReview, Listing, VisitSlot, Inquiry, SavedListing
All data is fictional but modeled after real UIUC subleases (Champaign, IL).
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'unleased_project.settings.dev')
django.setup()

from datetime import date, timedelta
from django.utils import timezone
from django.db import IntegrityError
from accounts.models import UnleasedUser, UserReview
from listings.models import Listing, VisitSlot, Inquiry, SavedListing

print("Clearing old seed data...")
SavedListing.objects.all().delete()
Inquiry.objects.all().delete()
VisitSlot.objects.all().delete()
Listing.objects.all().delete()
UserReview.objects.all().delete()
UnleasedUser.objects.exclude(username__in=['admin', 'mohitg2', 'tester']).delete()

# ── 1. USERS ─────────────────────────────────────────────────────────────────

print("Creating users...")

parul = UnleasedUser.objects.create_user(
    username='parul_m',
    email='parul2@illinois.edu',
    password='test1234',
    first_name='Parul',
    last_name='Mudaliar',
    edu_email='parul2@illinois.edu',
    is_edu_verified=True,
    role='lister',
    bio='iSchool MS student. Clean, quiet, leaving for summer internship in SF.',
    sleep_schedule='early',
    cleanliness='very_clean',
    noise_level='quiet',
    guests_policy='rarely',
    pets_ok=False,
    response_rate=95.0,
)

suruthe = UnleasedUser.objects.create_user(
    username='suruthe_j',
    email='suruthe2@illinois.edu',
    password='test1234',
    first_name='Suruthe',
    last_name='Jayachandran',
    edu_email='suruthe2@illinois.edu',
    is_edu_verified=True,
    role='both',
    bio='CS junior. Looking for a sublease near Siebel for summer. Also have a place to list.',
    sleep_schedule='night',
    cleanliness='moderate',
    noise_level='moderate',
    guests_policy='sometimes',
    pets_ok=True,
    response_rate=88.0,
)

shithil = UnleasedUser.objects.create_user(
    username='shithil_s',
    email='shetty7@illinois.edu',
    password='test1234',
    first_name='Shithil',
    last_name='Shetty',
    edu_email='shetty7@illinois.edu',
    is_edu_verified=True,
    role='both',          # lists his own place AND is looking for a new one
    bio='ECE grad student arriving in August. Need a furnished room near Engineering.',
    sleep_schedule='flexible',
    cleanliness='moderate',
    noise_level='quiet',
    guests_policy='rarely',
    pets_ok=False,
    response_rate=0.0,
)

alex = UnleasedUser.objects.create_user(
    username='alex_kim',
    email='akim42@illinois.edu',
    password='test1234',
    first_name='Alex',
    last_name='Kim',
    edu_email='akim42@illinois.edu',
    is_edu_verified=True,
    role='lister',
    bio='Finance junior subleasing my room for summer — going to Chicago for internship.',
    sleep_schedule='night',
    cleanliness='moderate',
    noise_level='social',
    guests_policy='often',
    pets_ok=True,
    response_rate=72.0,
)

priya = UnleasedUser.objects.create_user(
    username='priya_r',
    email='priyar3@illinois.edu',
    password='test1234',
    first_name='Priya',
    last_name='Rajan',
    edu_email='priyar3@illinois.edu',
    is_edu_verified=False,
    role='seeker',
    bio='Incoming freshman looking for a sublease before official housing starts.',
    sleep_schedule='early',
    cleanliness='very_clean',
    noise_level='quiet',
    guests_policy='rarely',
    pets_ok=False,
    response_rate=0.0,
)

print(f"  Created {UnleasedUser.objects.exclude(username__in=['admin','mohitg2','tester']).count()} student users")

# ── 2. LISTINGS (5 rows — meets the 5–10 requirement) ────────────────────────

print("Creating listings...")

listing1 = Listing.objects.create(
    lister=parul,
    title='Private BR + Bath in Fully Furnished 3BD — 48 E John St',
    description=(
        'Subleasing my private bedroom with attached bathroom in a 3bed/3bath fully furnished '
        'apartment. Available immediately. Two chill female roommates. 1-min walk to MTD, '
        '1-min to Green Street. In-unit W/D, balcony, dishwasher, high-speed internet included.'
    ),
    monthly_rent=450.00,
    utilities_included=True,
    building_name='Smile Living — John Street',
    street_address='48 E John St',
    unit_number='209',
    city='Champaign',
    state='IL',
    zip_code='61820',
    bedrooms=3,
    bathrooms=3.0,
    is_private_bedroom=True,
    is_private_bathroom=True,
    is_furnished=True,
    has_in_unit_laundry=True,
    has_parking=False,
    has_balcony=True,
    pets_allowed=False,
    ac_included=True,
    available_from=date.today(),
    available_until=date(2026, 8, 5),
    gender_preference=Listing.GenderPreference.FEMALE,
    status=Listing.Status.AVAILABLE,
    is_property_verified=True,
    external_listing_url='https://www.smilestudentliving.com/listings/detail/15bd12e1-b550-4948-bd10-b7446b603da6',
    ai_parsed=True,
    raw_whatsapp_text='Summer Sublease – $450/month (ALL UTILITIES INCLUDED!)...',
    view_count=142,
    save_count=18,
    inquiry_count=7,
)

listing2 = Listing.objects.create(
    lister=suruthe,
    title='2BD/2BA 9th Floor Corner Unit on Green St — Spring & Summer 2027',
    description=(
        'Stunning corner unit on the 9th floor with floor-to-ceiling windows. '
        'Rooftop pool, gym, concierge in building. 30-second walk to bars, restaurants, '
        'and campus bus stops. Available December 19 for spring + summer sublet. '
        'One roommate (male, CS grad, very quiet).'
    ),
    monthly_rent=1150.00,
    utilities_included=False,
    building_name='HERE Champaign',
    street_address='309 S Sixth St',
    unit_number='910',
    city='Champaign',
    state='IL',
    zip_code='61820',
    bedrooms=2,
    bathrooms=2.0,
    is_private_bedroom=True,
    is_private_bathroom=True,
    is_furnished=True,
    has_in_unit_laundry=True,
    has_parking=True,
    has_balcony=True,
    pets_allowed=False,
    ac_included=True,
    available_from=date(2026, 12, 19),
    available_until=date(2027, 7, 31),
    gender_preference=Listing.GenderPreference.ANY,
    status=Listing.Status.AVAILABLE,
    is_property_verified=True,
    view_count=89,
    save_count=11,
    inquiry_count=4,
)

listing3 = Listing.objects.create(
    lister=shithil,
    title='URGENT — Male Only, 1 Room in Maywood Apts, Full Year Sublease',
    description=(
        'Need someone ASAP. Leaving for Chicago internship Aug 20. '
        'Shared 2BD/1BA apartment, your own bedroom. Quiet building, on-site laundry. '
        'Close to State Farm Center and engineering quad. Price negotiable for quick move-in.'
    ),
    monthly_rent=800.00,
    utilities_included=False,
    building_name='Maywood Apartments',
    street_address='1007 S Mattis Ave',
    unit_number='4B',
    city='Champaign',
    state='IL',
    zip_code='61821',
    bedrooms=2,
    bathrooms=1.0,
    is_private_bedroom=True,
    is_private_bathroom=False,
    is_furnished=False,
    has_in_unit_laundry=False,
    has_parking=True,
    has_balcony=False,
    pets_allowed=True,
    ac_included=True,
    available_from=date(2026, 8, 20),
    available_until=date(2027, 8, 6),
    gender_preference=Listing.GenderPreference.MALE,
    status=Listing.Status.PENDING,
    is_property_verified=False,
    view_count=203,
    save_count=9,
    inquiry_count=12,
)

# NEW — listing 4
listing4 = Listing.objects.create(
    lister=parul,
    title='Cozy Studio Near Siebel — Perfect for CS/ECE Students',
    description=(
        'Fully furnished studio available for summer. Utilities included. '
        'Walking distance to Siebel Center, Thomas Siebel Hall, and the Main Quad. '
        'Quiet building, great for focused study. No roommates — entire unit is yours.'
    ),
    monthly_rent=750.00,
    utilities_included=True,
    building_name='The Lofts at 309',
    street_address='309 E Green St',
    unit_number='305',
    city='Champaign',
    state='IL',
    zip_code='61820',
    bedrooms=1,
    bathrooms=1.0,
    is_private_bedroom=True,
    is_private_bathroom=True,
    is_furnished=True,
    has_in_unit_laundry=False,
    has_parking=False,
    has_balcony=False,
    pets_allowed=False,
    ac_included=True,
    available_from=date(2026, 5, 15),
    available_until=date(2026, 8, 15),
    gender_preference=Listing.GenderPreference.ANY,
    status=Listing.Status.AVAILABLE,
    is_property_verified=True,
    view_count=67,
    save_count=5,
    inquiry_count=2,
)

# NEW — listing 5
listing5 = Listing.objects.create(
    lister=shithil,
    title='Furnished Room in 4BD House — Minutes from ARC & State Farm',
    description=(
        'Subleasing one room in a spacious 4-bedroom house. Huge backyard, '
        'free street parking, full kitchen. Three friendly roommates staying. '
        'Great for anyone who wants a house vibe over apartment living. '
        'Pets welcome — we have a dog.'
    ),
    monthly_rent=620.00,
    utilities_included=False,
    building_name='Private House',
    street_address='604 W Nevada St',
    unit_number='',
    city='Urbana',
    state='IL',
    zip_code='61801',
    bedrooms=4,
    bathrooms=2.0,
    is_private_bedroom=True,
    is_private_bathroom=False,
    is_furnished=True,
    has_in_unit_laundry=True,
    has_parking=True,
    has_balcony=False,
    pets_allowed=True,
    ac_included=True,
    available_from=date(2026, 8, 1),
    available_until=date(2027, 7, 31),
    gender_preference=Listing.GenderPreference.ANY,
    status=Listing.Status.AVAILABLE,
    is_property_verified=False,
    view_count=44,
    save_count=3,
    inquiry_count=1,
)

print(f"  Created {Listing.objects.count()} listings")

# ── 3. VISIT SLOTS ────────────────────────────────────────────────────────────

print("Creating visit slots...")

now = timezone.now()

VisitSlot.objects.create(
    listing=listing1,
    slot_start=now + timedelta(days=2, hours=10),
    slot_end=now + timedelta(days=2, hours=11),
    is_booked=False,
)
VisitSlot.objects.create(
    listing=listing1,
    slot_start=now + timedelta(days=2, hours=14),
    slot_end=now + timedelta(days=2, hours=15),
    seeker=shithil,
    is_booked=True,
    reminder_sent=False,
)
VisitSlot.objects.create(
    listing=listing1,
    slot_start=now + timedelta(days=4, hours=11),
    slot_end=now + timedelta(days=4, hours=12),
    is_booked=False,
)
VisitSlot.objects.create(
    listing=listing2,
    slot_start=now + timedelta(days=10, hours=13),
    slot_end=now + timedelta(days=10, hours=14),
    is_booked=False,
)
VisitSlot.objects.create(
    listing=listing2,
    slot_start=now + timedelta(days=11, hours=15),
    slot_end=now + timedelta(days=11, hours=16),
    is_booked=False,
)

print(f"  Created {VisitSlot.objects.count()} visit slots")

# ── 4. INQUIRIES ──────────────────────────────────────────────────────────────

print("Creating inquiries...")

Inquiry.objects.create(
    listing=listing1,
    seeker=shithil,
    message=(
        "Hi! I'm a grad student arriving in August. Your place looks perfect — "
        "private bath and Green St proximity are exactly what I need. "
        "Would love to schedule a visit. Is the price firm?"
    ),
    status=Inquiry.Status.ACCEPTED,
)
Inquiry.objects.create(
    listing=listing1,
    seeker=suruthe,
    message="Interested in the room! Can I come by this weekend to see it?",
    status=Inquiry.Status.PENDING,
)
Inquiry.objects.create(
    listing=listing2,
    seeker=shithil,
    message=(
        "I'd love to see the 9th floor unit. Available for a visit next week. "
        "Does the parking spot come with the sublease or is it separate?"
    ),
    status=Inquiry.Status.PENDING,
)
Inquiry.objects.create(
    listing=listing3,
    seeker=suruthe,
    message="Still available? I can move in immediately and can pay first month upfront.",
    status=Inquiry.Status.ACCEPTED,
)

print(f"  Created {Inquiry.objects.count()} inquiries")

# ── 5. SAVED LISTINGS ─────────────────────────────────────────────────────────

print("Creating saved listings...")

SavedListing.objects.create(seeker=shithil, listing=listing1)
SavedListing.objects.create(seeker=shithil, listing=listing2)
SavedListing.objects.create(seeker=suruthe, listing=listing1)

print(f"  Created {SavedListing.objects.count()} saved listings")

# ── 6. USER REVIEWS ───────────────────────────────────────────────────────────

print("Creating user reviews...")

UserReview.objects.create(
    reviewer=parul,
    reviewee=suruthe,
    rating=5,
    comment="Great subleasee — paid on time, left the apartment cleaner than they found it. Would highly recommend.",
)
UserReview.objects.create(
    reviewer=suruthe,
    reviewee=parul,
    rating=5,
    comment="Parul was super responsive and the listing was exactly as described. Zero surprises.",
)
UserReview.objects.create(
    reviewer=alex,
    reviewee=shithil,
    rating=4,
    comment="Reliable and communicative. Took a couple days to respond initially but was great once we connected.",
)

print(f"  Created {UserReview.objects.count()} user reviews")

# ── 7. UNIQUENESS CONSTRAINT VALIDATION ───────────────────────────────────────

print("\nValidating uniqueness constraints...")

try:
    Inquiry.objects.create(
        listing=listing1, seeker=shithil,
        message="Duplicate inquiry — should fail.",
    )
    print("  FAIL: unique_inquiry_per_seeker_listing not enforced.")
except IntegrityError:
    print("  PASS: unique_inquiry_per_seeker_listing enforced correctly.")

try:
    SavedListing.objects.create(seeker=shithil, listing=listing1)
    print("  FAIL: unique_save_per_seeker_listing not enforced.")
except IntegrityError:
    print("  PASS: unique_save_per_seeker_listing enforced correctly.")

try:
    UserReview.objects.create(reviewer=parul, reviewee=suruthe, rating=1, comment="Duplicate.")
    print("  FAIL: unique_review_per_pair not enforced.")
except IntegrityError:
    print("  PASS: unique_review_per_pair enforced correctly.")

# ── 8. ON_DELETE BEHAVIOUR VALIDATION ────────────────────────────────────────

print("\nValidating on_delete behaviour...")

# ── CASCADE: deleting a Listing deletes its VisitSlots and Inquiries ──────────
temp_listing = Listing.objects.create(
    lister=parul,
    title='Temp listing — on_delete CASCADE test',
    description='Created to test CASCADE deletion. Will be deleted immediately.',
    monthly_rent=500.00,
    street_address='1 Test St',
    city='Champaign', state='IL', zip_code='61820',
    bedrooms=1, bathrooms=1.0,
    available_from=date.today(),
    available_until=date(2026, 8, 1),
)
VisitSlot.objects.create(
    listing=temp_listing,
    slot_start=now + timedelta(days=1),
    slot_end=now + timedelta(days=1, hours=1),
)
Inquiry.objects.create(
    listing=temp_listing,
    seeker=shithil,
    message='Test inquiry for CASCADE demo.',
)
slots_before   = VisitSlot.objects.filter(listing=temp_listing).count()
inquiries_before = Inquiry.objects.filter(listing=temp_listing).count()

temp_listing_id = temp_listing.id
temp_listing.delete()

slots_after    = VisitSlot.objects.filter(listing_id=temp_listing_id).count()
inquiries_after = Inquiry.objects.filter(listing_id=temp_listing_id).count()

if slots_after == 0 and inquiries_after == 0:
    print(f"  PASS: CASCADE — deleted Listing (id={temp_listing_id}), "
          f"its {slots_before} VisitSlot(s) and {inquiries_before} Inquiry(s) deleted too.")
else:
    print("  FAIL: CASCADE did not delete child records as expected.")

# ── SET_NULL: deleting a seeker NULLs VisitSlot.seeker, slot stays open ──────
temp_seeker = UnleasedUser.objects.create_user(
    username='temp_seeker_test',
    email='tempseeker@illinois.edu',
    password='test1234',
    edu_email='tempseeker@illinois.edu',
)
temp_slot = VisitSlot.objects.create(
    listing=listing1,
    slot_start=now + timedelta(days=20),
    slot_end=now + timedelta(days=20, hours=1),
    seeker=temp_seeker,
    is_booked=True,
)
temp_slot_id = temp_slot.id
temp_seeker.delete()

temp_slot.refresh_from_db()
if temp_slot.seeker is None and temp_slot.id == temp_slot_id:
    print("  PASS: SET_NULL — deleting seeker set VisitSlot.seeker to NULL "
          "(slot still exists and is now open for rebooking).")
else:
    print("  FAIL: SET_NULL did not behave as expected.")

# ── 9. SUMMARY ────────────────────────────────────────────────────────────────

print("\n── Seed complete ──────────────────────────────────────────────────────")
print(f"  Users (excl. superusers) : {UnleasedUser.objects.exclude(username__in=['admin','mohitg2','tester']).count()}")
print(f"  Listings                 : {Listing.objects.count()}")
print(f"  Visit Slots              : {VisitSlot.objects.count()}")
print(f"  Inquiries                : {Inquiry.objects.count()}")
print(f"  Saved Listings           : {SavedListing.objects.count()}")
print(f"  User Reviews             : {UserReview.objects.count()}")
print("───────────────────────────────────────────────────────────────────────")
print("Admin login → /admin/   username: admin   password: unleased_admin_2026")