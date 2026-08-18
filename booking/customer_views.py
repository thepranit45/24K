"""
Customer REST API — for the Android Booking App (no payment, pay at shop).

Endpoints:
  GET  /api/customer/home/                       -> services, barbers, dates
  GET  /api/customer/slots/?date=&service_id=&barber_id=
  POST /api/customer/bookings/                   -> create booking (pending)
  GET  /api/customer/bookings/?phone=            -> my bookings by phone
  POST /api/customer/bookings/<booking_id>/cancel/
"""

import json
import logging
from datetime import datetime, timedelta

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from .api_views import _booking_dict, _error, _ok
from .models import Barber, Booking, BusinessHour, Payment, Service
from .views import _available_dates, _generate_slots, _booked_times

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Catalog
# ──────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["GET"])
def customer_home(request):
    """
    GET /api/customer/home/
    Returns active services, barbers and bookable dates.
    """
    def ser(s):
        return {
            'id': s.pk,
            'name': s.name,
            'category': s.category,
            'description': s.description,
            'price': str(s.price),
            'price_display': s.price_display,
            'duration': s.duration,
            'icon': s.icon,
        }

    def br(b):
        return {
            'id': b.pk,
            'name': b.name,
            'title': b.title,
            'bio': b.bio,
            'photo_url': request.build_absolute_uri(b.photo.url) if b.photo else None,
            'avatar_icon': b.avatar_icon,
            'specialties': b.specialties,
            'rating': str(b.rating),
            'experience_years': b.experience_years,
        }

    male = Service.objects.filter(is_active=True, category='MALE')
    female = Service.objects.filter(is_active=True, category='FEMALE')
    barbers = Barber.objects.filter(is_active=True, name='Prashant Borhade')

    return _ok({
        'male_services': [ser(s) for s in male],
        'female_services': [ser(s) for s in female],
        'barbers': [br(b) for b in barbers],
        'available_dates': [d.isoformat() for d in _available_dates(30)],
    })


# ──────────────────────────────────────────────────────────────
# Time Slots
# ──────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["GET"])
def customer_slots(request):
    """
    GET /api/customer/slots/?date=YYYY-MM-DD&service_id=&barber_id=
    Mirror of the website's AJAX slot picker.
    """
    date_str = request.GET.get('date')
    service_id = request.GET.get('service_id')
    barber_id = request.GET.get('barber_id')

    if not date_str:
        return _error('date is required')

    try:
        slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return _error('Invalid date format. Use YYYY-MM-DD.')

    duration = 30
    if service_id:
        try:
            service = Service.objects.get(pk=service_id, is_active=True)
            duration = service.duration
        except Service.DoesNotExist:
            pass

    today = timezone.localdate()
    if slot_date < today:
        return _error('Cannot book a past date.')

    try:
        bh = BusinessHour.objects.get(day=slot_date.weekday())
    except BusinessHour.DoesNotExist:
        return _ok({'slots': [], 'message': 'No business hours configured.'})

    if bh.is_closed:
        return _ok({'slots': [], 'message': 'Shop is closed on this day.'})

    all_slots = _generate_slots(bh.opening_time, bh.closing_time)
    booked = _booked_times(slot_date, barber_id=barber_id)

    now_local = timezone.localtime(timezone.now())
    buffer_time = (now_local + timedelta(minutes=30)).time() if slot_date == today else datetime.min.time()

    closing_dt = datetime.combine(slot_date, bh.closing_time)
    slots_data = []

    for s in all_slots:
        is_past = slot_date == today and s <= buffer_time

        is_booked = False
        current_check = datetime.combine(slot_date, s)
        end_check = current_check + timedelta(minutes=duration)

        if end_check > closing_dt:
            is_booked = True
        else:
            while current_check < end_check:
                if current_check.time() in booked:
                    is_booked = True
                    break
                current_check += timedelta(minutes=30)

        slots_data.append({
            'time': s.strftime('%H:%M'),
            'display': s.strftime('%I:%M %p').lstrip('0'),
            'booked': is_booked or is_past,
        })

    return _ok({'slots': slots_data, 'date': date_str})


# ──────────────────────────────────────────────────────────────
# Create Booking  (no payment — pay at shop)
# ──────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def customer_create_booking(request):
    """
    POST /api/customer/bookings/
    Body: {
        service_id, barber_id (optional),
        booking_date (YYYY-MM-DD), booking_time (HH:MM),
        full_name, phone, email, special_request
    }
    Auto-confirms since there is no payment in the app.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return _error('Invalid JSON payload.')

    service_id      = data.get('service_id')
    barber_id       = data.get('barber_id')
    date_str        = data.get('booking_date')
    time_str        = data.get('booking_time')
    full_name       = (data.get('full_name') or '').strip()
    phone           = (data.get('phone') or '').strip()
    email           = (data.get('email') or '').strip()
    special_request = (data.get('special_request') or '').strip()

    # ── Validate service ───────────────────────────────────────
    try:
        service = Service.objects.get(pk=service_id, is_active=True)
    except Service.DoesNotExist:
        return _error('Service not found or inactive.')

    # ── Validate barber if provided ───────────────────────────
    selected_barber = None
    if barber_id:
        try:
            selected_barber = Barber.objects.get(pk=barber_id, is_active=True)
        except Barber.DoesNotExist:
            return _error('Selected barber not found.')

    # ── Validate date ──────────────────────────────────────────
    try:
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return _error('Invalid date.')

    today = timezone.localdate()
    if booking_date < today:
        return _error('Cannot book a past date.')

    try:
        bh = BusinessHour.objects.get(day=booking_date.weekday())
    except BusinessHour.DoesNotExist:
        return _error('Shop is closed on this day.')

    if bh.is_closed:
        return _error('Shop is closed on this day.')

    # ── Validate time ──────────────────────────────────────────
    try:
        booking_time = datetime.strptime(time_str, '%H:%M').time()
    except (ValueError, TypeError):
        return _error('Invalid time format.')

    if not (bh.opening_time <= booking_time < bh.closing_time):
        return _error('Selected time is outside business hours.')

    if booking_date == today:
        now_local = timezone.localtime(timezone.now())
        if booking_time <= (now_local + timedelta(minutes=30)).time():
            return _error('Please select a future time slot.')

    # ── Double-booking check ───────────────────────────────────
    check_qs = Booking.objects.filter(
        booking_date=booking_date,
        booking_time=booking_time,
        status__in=[Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED]
    )
    if selected_barber:
        check_qs = check_qs.filter(barber=selected_barber)

    if check_qs.exists():
        return _error('This slot is already booked. Please choose another slot.', 409)

    # ── Validate customer details ──────────────────────────────
    if not full_name:
        return _error('Full name is required.')
    if not phone or len(''.join(filter(str.isdigit, phone))) < 10:
        return _error('Please enter a valid mobile number.')

    # ── Create Booking (confirmed immediately — pay at shop) ────
    booking = Booking.objects.create(
        user=None,
        service=service,
        barber=selected_barber,
        booking_date=booking_date,
        booking_time=booking_time,
        customer_name=full_name,
        customer_phone=phone,
        customer_email=email,
        special_request=special_request,
        amount=service.price,
        status=Booking.STATUS_CONFIRMED,
    )

    Payment.objects.create(
        booking=booking,
        amount=service.price,
        payment_method='CASH_AT_SHOP',
        status=Payment.STATUS_PENDING,
    )

    # ── Send confirmation SMS (best effort) ────────────────────
    try:
        from .sms import send_booking_confirmation, schedule_reminders
        send_booking_confirmation(booking)
        schedule_reminders(booking)
    except Exception as e:
        logger.exception(f'SMS error for {booking.booking_id}: {e}')

    return _ok({
        'message': 'Booking confirmed. Please pay at the shop.',
        'booking': _booking_dict(booking),
    })


# ──────────────────────────────────────────────────────────────
# My Bookings (lookup by phone — no login needed)
# ──────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["GET"])
def customer_my_bookings(request):
    """
    GET /api/customer/bookings/?phone=+919876543210
    Returns all bookings for the given phone number.
    """
    phone = (request.GET.get('phone') or '').strip()
    if not phone:
        return _error('phone is required')

    bookings = (
        Booking.objects
        .filter(customer_phone__icontains=phone[-10:])
        .select_related('service', 'barber')
        .order_by('-booking_date', '-booking_time')
    )
    return _ok({'bookings': [_booking_dict(b) for b in bookings]})


@csrf_exempt
@require_POST
def customer_cancel_booking(request, booking_id):
    """
    POST /api/customer/bookings/<booking_id>/cancel/
    Body: {"phone": "..."} — phone must match the booking.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = {}

    phone = (data.get('phone') or '').strip()

    try:
        booking = Booking.objects.select_related('service', 'barber').get(booking_id=booking_id)
    except Booking.DoesNotExist:
        return _error('Booking not found.', 404)

    if phone and booking.customer_phone and phone[-10:] != booking.customer_phone[-10:]:
        return _error('Phone number does not match this booking.', 403)

    if booking.status in (Booking.STATUS_COMPLETED, Booking.STATUS_CANCELLED):
        return _error(f'Cannot cancel a booking with status: {booking.status}')

    booking.status = Booking.STATUS_CANCELLED
    booking.save()

    try:
        from .sms import _send_sms
        dt = datetime.combine(booking.booking_date, booking.booking_time)
        msg = (
            f'❌ Booking Cancelled — 24K Barbershop\n'
            f'Your booking {booking.booking_id} on {booking.booking_date.strftime("%d %b")} '
            f'at {dt.strftime("%I:%M %p")} has been cancelled.\n'
            f'Please call us to rebook.'
        )
        _send_sms(booking.customer_phone, msg)
    except Exception as e:
        logger.exception(f'Cancel SMS error for {booking_id}: {e}')

    return _ok({'message': 'Booking cancelled.', 'booking': _booking_dict(booking)})
