import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from booking.models import Barber

barber_users = list(User.objects.filter(barber_profile__isnull=False))
admin_user = User.objects.filter(username='admin').first()

all_targets = set(barber_users)
if admin_user:
    all_targets.add(admin_user)

# Also check any other staff accounts or barbers
for b in Barber.objects.all():
    if b.user:
        all_targets.add(b.user)

for u in all_targets:
    u.set_password('admin')
    u.is_staff = True
    u.save()
    print(f"Updated password to 'admin' for: {u.username} (email: {u.email}, is_staff: {u.is_staff})")

print("Done setting passwords.")
