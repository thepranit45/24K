import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from booking.models import Service

# Deactivate existing services to prevent duplicates in the UI
Service.objects.all().update(is_active=False)

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
    Service.objects.create(
        name=data["name"],
        price=data["price"],
        duration=data["duration"],
        icon=data["icon"],
        description=data["description"],
        category=data["category"],
        sort_order=idx,
        is_active=True
    )
print("Successfully loaded new categorized services into the database!")
