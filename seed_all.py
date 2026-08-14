import os
import django
from datetime import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from booking.models import BusinessHour, Barber, Service

print("--- Seeding Business Hours ---")
for day_idx in range(7):
    bh, created = BusinessHour.objects.get_or_create(
        day=day_idx,
        defaults={
            'opening_time': time(9, 0),
            'closing_time': time(21, 0),
            'is_closed': False,
        }
    )
    if created:
        print(f"Created BusinessHour for day {day_idx}")
    else:
        bh.opening_time = time(9, 0)
        bh.closing_time = time(21, 0)
        bh.is_closed = False
        bh.save()
        print(f"Updated BusinessHour for day {day_idx}")

print("--- Seeding Barbers ---")
BARBERS = [
    {
        'name': 'Vikram Sharma',
        'title': 'Senior Master Barber',
        'bio': '10+ years of precision haircutting, fade artistry, and luxury beard sculpting.',
        'avatar_icon': 'user-tie',
        'specialties': 'Skin Fade, Hot Towel Shave, Royal Grooming',
        'rating': 4.9,
        'experience_years': 10,
        'is_active': True,
    },
    {
        'name': 'Rahul Verma',
        'title': 'Beard & Styling Specialist',
        'bio': 'Master of classic razor shaves, sharp line-ups, and modern textured styles.',
        'avatar_icon': 'scissors',
        'specialties': 'Beard Sculpting, Hair Design, Line Up',
        'rating': 4.9,
        'experience_years': 7,
        'is_active': True,
    },
    {
        'name': 'Karan Malhotra',
        'title': 'Textured Crop & Fade Artist',
        'bio': 'Specialist in modern European haircut trends, pompadours, and taper fades.',
        'avatar_icon': 'crown',
        'specialties': 'Textured Crop, Taper Fade, Hair Color',
        'rating': 4.8,
        'experience_years': 6,
        'is_active': True,
    },
    {
        'name': 'Sameer Khan',
        'title': 'Classic Grooming Master',
        'bio': 'Expert in traditional scissors techniques, soothing head massage, and facial treatment.',
        'avatar_icon': 'user-doctor',
        'specialties': 'Classic Scissor Cut, Head Spa, Beard Trim',
        'rating': 4.9,
        'experience_years': 8,
        'is_active': True,
    },
]

for bdata in BARBERS:
    barber, created = Barber.objects.get_or_create(
        name=bdata['name'],
        defaults=bdata
    )
    if not created:
        for k, v in bdata.items():
            setattr(barber, k, v)
        barber.save()
        print(f"Updated Barber: {barber.name}")
    else:
        print(f"Created Barber: {barber.name}")

print("--- Seeding Services ---")
services_data = [
    # Male / General
    {"name": "Hair cut", "price": 150, "duration": 25, "icon": "scissors", "description": "Classic men's haircut.", "category": "MALE"},
    {"name": "Hair wash", "price": 50, "duration": 15, "icon": "sink", "description": "Refreshing hair wash.", "category": "MALE"},
    {"name": "Hair colour", "price": 150, "duration": 30, "icon": "palette", "description": "Hair coloring for men.", "category": "MALE"},
    {"name": "Beard colour", "price": 30, "duration": 5, "icon": "brush", "description": "Quick beard coloring.", "category": "MALE"},
    {"name": "Beard", "price": 100, "duration": 20, "icon": "cut", "description": "Beard trimming and shaping.", "category": "MALE"},
    {"name": "Beard trimmer", "price": 50, "duration": 10, "icon": "bolt", "description": "Quick machine trim for beard.", "category": "MALE"},
    {"name": "Threading", "price": 40, "duration": 10, "icon": "leaf", "description": "Eyebrow and facial threading.", "category": "MALE"},
    {"name": "D tan", "price": 350, "duration": 30, "icon": "sun", "description": "Tan removal treatment.", "category": "MALE"},
    {"name": "Clin up", "price": 350, "duration": 30, "icon": "sparkles", "description": "Face clean up for a fresh look.", "category": "MALE"},
    {"name": "Hair spa", "price": 600, "duration": 40, "icon": "spa", "description": "Relaxing hair spa treatment.", "category": "MALE"},
    {"name": "Facial", "price": 1500, "duration": 60, "icon": "smile", "description": "Complete facial treatment.", "category": "MALE"},
    {"name": "03+ facial", "price": 2000, "duration": 120, "icon": "gem", "description": "Premium O3+ facial treatment.", "category": "MALE"},
    {"name": "Head massage", "price": 200, "duration": 30, "icon": "hands", "description": "Relaxing head massage.", "category": "MALE"},
    {"name": "Keratin", "price": 1000, "duration": 90, "icon": "magic", "description": "Keratin hair smoothing treatment.", "category": "MALE"},

    # Female
    {"name": "Hair cut", "price": 200, "duration": 30, "icon": "scissors", "description": "Professional women's haircut.", "category": "FEMALE"},
    {"name": "Haircut with wash", "price": 300, "duration": 30, "icon": "sink", "description": "Haircut and wash for women.", "category": "FEMALE"},
    {"name": "Hair spa", "price": 1000, "duration": 60, "icon": "spa", "description": "Nourishing hair spa for women.", "category": "FEMALE"},
    {"name": "Root touch up", "price": 1000, "duration": 60, "icon": "palette", "description": "Hair root color touch up.", "category": "FEMALE"},
    {"name": "Global hair colour", "price": 2500, "duration": 90, "icon": "paintbrush", "description": "Full global hair coloring.", "category": "FEMALE"},
    {"name": "Highlights", "price": 150, "duration": 90, "icon": "star", "description": "Hair highlights, charged per strip.", "category": "FEMALE"},
    {"name": "Ironing", "price": 500, "duration": 90, "icon": "fire", "description": "Professional hair straightening/ironing.", "category": "FEMALE"},
    {"name": "Keratin", "price": 3000, "duration": 240, "icon": "wand-magic-sparkles", "description": "Premium keratin treatment for women.", "category": "FEMALE"},
]

for idx, data in enumerate(services_data):
    s, created = Service.objects.get_or_create(
        name=data["name"],
        category=data["category"],
        defaults={
            "price": data["price"],
            "duration": data["duration"],
            "icon": data["icon"],
            "description": data["description"],
            "sort_order": idx,
            "is_active": True,
        }
    )
    if not created:
        s.price = data["price"]
        s.duration = data["duration"]
        s.icon = data["icon"]
        s.description = data["description"]
        s.sort_order = idx
        s.is_active = True
        s.save()
        print(f"Updated Service: {s.name} ({s.category})")
    else:
        print(f"Created Service: {s.name} ({s.category})")

print("Seeding completed successfully!")
