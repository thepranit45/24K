import os
import django
from django.core.files import File

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from booking.models import Service

# The path to the newly generated Keratin image
img_path = r"C:\Users\thepr\.gemini\antigravity-ide\brain\21f4cbf4-1d7e-4368-94fa-284047a70444\keratin_treatment_1786350161837.png"

if os.path.exists(img_path):
    # Find Male and Female Keratin services
    keratin_services = Service.objects.filter(is_active=True, name__icontains="Keratin")
    for service in keratin_services:
        with open(img_path, 'rb') as f:
            service.image.save(f'service_{service.id}.png', File(f), save=True)
            print(f"Assigned generated image to {service.name} ({service.category})")
else:
    print("Image not found at path:", img_path)
