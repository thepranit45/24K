import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from booking.models import Barber

BARBERS = [
    {
        'name': 'Vikram Sharma',
        'title': 'Senior Master Barber',
        'bio': '10+ years of precision haircutting, fade artistry, and luxury beard sculpting.',
        'avatar_icon': 'user-tie',
        'specialties': 'Skin Fade, Hot Towel Shave, Royal Grooming',
        'rating': 4.9,
        'experience_years': 10,
    },
    {
        'name': 'Rahul Verma',
        'title': 'Beard & Styling Specialist',
        'bio': 'Master of classic razor shaves, sharp line-ups, and modern textured styles.',
        'avatar_icon': 'scissors',
        'specialties': 'Beard Sculpting, Hair Design, Line Up',
        'rating': 4.9,
        'experience_years': 7,
    },
    {
        'name': 'Karan Malhotra',
        'title': 'Textured Crop & Fade Artist',
        'bio': 'Specialist in modern European haircut trends, pompadours, and taper fades.',
        'avatar_icon': 'crown',
        'specialties': 'Textured Crop, Taper Fade, Hair Color',
        'rating': 4.8,
        'experience_years': 6,
    },
    {
        'name': 'Sameer Khan',
        'title': 'Classic Grooming Master',
        'bio': 'Expert in traditional scissors techniques, soothing head massage, and facial treatment.',
        'avatar_icon': 'user-doctor',
        'specialties': 'Classic Scissor Cut, Head Spa, Beard Trim',
        'rating': 4.9,
        'experience_years': 8,
    },
]

for bdata in BARBERS:
    barber, created = Barber.objects.get_or_create(
        name=bdata['name'],
        defaults=bdata
    )
    if created:
        print(f"Created Barber: {barber.name}")
    else:
        print(f"Barber already exists: {barber.name}")
