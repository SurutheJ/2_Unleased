"""
seed_photos.py: give listings sample photos from seed_media/listings/.

Used two ways:
  python seed_photos.py   Adds 3 photos to every existing listing that has
                          none yet. Safe to run on a database with real
                          listings: it never deletes or changes anything else.
  seed_data.py            Calls attach_photos() for the sample listings it creates.

Each listing gets a cover photo (a living or dining area) plus two more rooms,
rotating through the sample photos so neighbouring cards look different.
The originals stay in seed_media/; Django copies them into MEDIA_ROOT
(media/listing_media/...), so deleting a listing never removes a source photo.
"""

import os
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent / 'seed_media' / 'listings'

# Photo sets, cycled per listing. The first photo in each set is the cover.
PHOTO_SETS = [
    ['living-open-plan.webp', 'bedroom.webp', 'dining-kitchen.webp'],
    ['living-room.webp', 'bedroom.webp', 'bathroom.webp'],
    ['dining-living.webp', 'bedroom.webp', 'dining-kitchen.webp'],
    ['dining-kitchen.webp', 'living-room.webp', 'bathroom.webp'],
    ['living-open-plan.webp', 'bathroom.webp', 'dining-living.webp'],
    ['living-room.webp', 'dining-kitchen.webp', 'bedroom.webp'],
]


def attach_photos(listings, only_without_media=True):
    """Attach a photo set to each listing. Returns the number of photos added."""
    from django.core.files import File
    from listings.models import ListingMedia

    if not SEED_DIR.is_dir():
        print(f'  No sample photos found in {SEED_DIR}, so listings keep the placeholder image.')
        return 0
    added = 0
    for index, listing in enumerate(listings):
        if only_without_media and listing.media.exists():
            continue
        for name in PHOTO_SETS[index % len(PHOTO_SETS)]:
            path = SEED_DIR / name
            if not path.exists():
                continue
            with path.open('rb') as handle:
                ListingMedia.objects.create(listing=listing, kind=ListingMedia.Kind.PHOTO,
                                            file=File(handle, name=name))
            added += 1
    return added


if __name__ == '__main__':
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'unleased_project.settings.dev')
    django.setup()
    from listings.models import Listing
    count = attach_photos(Listing.objects.order_by('id'))
    print(f'Added {count} photo(s) to listings that had none.')
