import uuid
import random
import string
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


def generate_booking_id():
    """Generate a unique booking ID like BK-A3F8D2."""
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"BK-{suffix}"


class Service(models.Model):
    CATEGORY_CHOICES = [
        ('MALE', 'Male Services'),
        ('FEMALE', 'Female Services'),
    ]
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='MALE')
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    image = models.ImageField(upload_to='services/', null=True, blank=True)
    icon = models.CharField(
        max_length=50,
        default='scissors',
        help_text="Font Awesome icon name (e.g. scissors, star, spa)"
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'price']
        verbose_name = 'Service'
        verbose_name_plural = 'Services'

    def __str__(self):
        return f"{self.name} — ₹{self.price}"

    @property
    def price_display(self):
        return f"₹{int(self.price):,}"


class ShopSetting(models.Model):
    """Simple key/value store for shop-wide configuration (e.g. slot step)."""
    key = models.CharField(max_length=50, unique=True)
    value = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        verbose_name = 'Shop Setting'
        verbose_name_plural = 'Shop Settings'

    def __str__(self):
        return f"{self.key} = {self.value}"


def get_shop_setting(key, default=''):
    try:
        return ShopSetting.objects.get(key=key).value
    except ShopSetting.DoesNotExist:
        return default


def slot_step_minutes():
    """How many minutes each time slot lasts (configurable from the dashboard)."""
    try:
        return max(5, min(int(get_shop_setting('slot_step', '30')), 120))
    except (TypeError, ValueError):
        return 30


class BusinessHour(models.Model):
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    day = models.IntegerField(choices=DAY_CHOICES, unique=True)
    opening_time = models.TimeField(default='10:00')
    closing_time = models.TimeField(default='21:00')
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ['day']
        verbose_name = 'Business Hour'
        verbose_name_plural = 'Business Hours'

    def __str__(self):
        if self.is_closed:
            return f"{self.get_day_display()} — Closed"
        return f"{self.get_day_display()} — {self.opening_time.strftime('%I:%M %p')} to {self.closing_time.strftime('%I:%M %p')}"


class Barber(models.Model):
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=100, default='Master Barber')
    bio = models.TextField(blank=True, default='Expert in precision cuts, fades, and traditional hot towel grooming.')
    photo = models.ImageField(upload_to='barbers/', null=True, blank=True)
    avatar_icon = models.CharField(
        max_length=50,
        default='user-tie',
        help_text="Font Awesome icon name (e.g. user-tie, user-ninja, user-doctor, crown)"
    )
    specialties = models.CharField(max_length=200, default='Skin Fade, Beard Styling, Hair Design')
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.9)
    experience_years = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='barber_profile',
        help_text="Optional shop account that signs this barber into their personal dashboard."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Barber'
        verbose_name_plural = 'Barbers'

    def __str__(self):
        return f"{self.name} ({self.title})"

    @property
    def specialty_list(self):
        """Specialties as a list for template chips."""
        return [s.strip() for s in self.specialties.split(',') if s.strip()]

    @property
    def initials(self):
        """Initials for avatar fallback (e.g. 'KM' for Karan Malhotra)."""
        parts = [p for p in self.name.split() if p]
        if not parts:
            return '?'
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[1][0]).upper()


class Booking(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_CONFIRMED = 'CONFIRMED'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    booking_id = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name='bookings')
    barber = models.ForeignKey(Barber, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')

    booking_date = models.DateField()
    booking_time = models.TimeField()

    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField()
    special_request = models.TextField(blank=True)

    # Amount is frozen from service price at time of booking
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['booking_date', 'booking_time']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['booking_id']),
        ]

    def save(self, *args, **kwargs):
        if not self.booking_id:
            # Ensure unique booking ID
            uid = generate_booking_id()
            while Booking.objects.filter(booking_id=uid).exists():
                uid = generate_booking_id()
            self.booking_id = uid
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.booking_id} | {self.customer_name} | {self.service.name} | {self.booking_date}"

    @property
    def amount_display(self):
        return f"₹{int(self.amount):,}"

    @property
    def can_be_cancelled(self):
        """Booking can be cancelled if it's upcoming and not already cancelled/completed."""
        from datetime import date, datetime, time
        if self.status in (self.STATUS_CANCELLED, self.STATUS_COMPLETED):
            return False
        booking_dt = timezone.make_aware(
            datetime.combine(self.booking_date, self.booking_time)
        )
        return booking_dt > timezone.now()

    @property
    def is_upcoming(self):
        from datetime import datetime
        booking_dt = timezone.make_aware(
            datetime.combine(self.booking_date, self.booking_time)
        )
        return booking_dt > timezone.now() and self.status in (self.STATUS_PENDING, self.STATUS_CONFIRMED)


class Payment(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_PAID = 'PAID'
    STATUS_FAILED = 'FAILED'
    STATUS_REFUNDED = 'REFUNDED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PAID, 'Paid'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_REFUNDED, 'Refunded'),
    ]

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    payment_method = models.CharField(max_length=50, default='MOCK')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self):
        return f"Payment [{self.status}] for {self.booking.booking_id} — ₹{self.amount}"
