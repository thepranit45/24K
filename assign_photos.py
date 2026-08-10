import os
import django
from django.core.files import File

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from booking.models import Service

# Assign Male services
male_services = Service.objects.filter(is_active=True, category='MALE').order_by('id')
for i, service in enumerate(male_services):
    img_path = f'd:\\QC\\barbershop\\media\\services\\male_service_{i}.png'
    if os.path.exists(img_path):
        with open(img_path, 'rb') as f:
            service.image.save(f'service_{service.id}.png', File(f), save=True)
            print(f"Assigned image to {service.name} (Male)")

# Assign Female services
female_services = Service.objects.filter(is_active=True, category='FEMALE').order_by('id')
for i, service in enumerate(female_services):
    img_idx = 14 + i
    img_path = f'd:\\QC\\barbershop\\media\\services\\male_service_{img_idx}.png'
    if os.path.exists(img_path):
        with open(img_path, 'rb') as f:
            service.image.save(f'service_{service.id}.png', File(f), save=True)
            print(f"Assigned image to {service.name} (Female)")

print("All photos assigned!")
