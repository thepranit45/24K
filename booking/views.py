import json
import uuid
import urllib.parse
from datetime import date, datetime, timedelta, time as dtime
from decimal import Decimal
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CustomerDetailsForm
from .models import (
    Barber, Booking, BusinessHour, Payment, Service, ShopSetting,
    slot_step_minutes, get_shop_upi_id, get_shop_upi_name, get_razorpay_keys
)


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _generate_slots(open_t: dtime, close_t: dtime, step_minutes: int = None):
    step = step_minutes or slot_step_minutes()
    slots = []
    current = datetime.combine(date.today(), open_t)
    end = datetime.combine(date.today(), close_t)
    while current < end:
        slots.append(current.time())
        current += timedelta(minutes=step)
    return slots


def _booked_times(booking_date: date, barber_id=None):
    qs = Booking.objects.filter(
        booking_date=booking_date,
        status__in=[Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED]
    )
    if barber_id:
        qs = qs.filter(barber_id=barber_id)
        
    bookings = qs.select_related('service')

    step = slot_step_minutes()
    booked_slots = set()
    for b in bookings:
        current_time = datetime.combine(booking_date, b.booking_time)
        end_time = current_time + timedelta(minutes=b.service.duration)
        
        while current_time < end_time:
            booked_slots.add(current_time.time())
            current_time += timedelta(minutes=step)
            
    return booked_slots


def _available_dates(days_ahead: int = 30):
    today = timezone.localdate()
    business_hours = {bh.day: bh for bh in BusinessHour.objects.all()}
    result = []
    for i in range(0, days_ahead):
        d = today + timedelta(days=i)
        bh = business_hours.get(d.weekday())
        if bh and not bh.is_closed:
            result.append(d)
    return result


def _session_booking_ids(request):
    """Return list of booking IDs stored in session (for guests)."""
    return request.session.get('booking_ids', [])


def _add_booking_to_session(request, booking_id):
    ids = _session_booking_ids(request)
    if booking_id not in ids:
        ids.append(booking_id)
    request.session['booking_ids'] = ids
    request.session.modified = True


def barber_staff_required(view_func):
    """Allow only signed-in staff members to operate shop-management controls."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped


def barber_required(view_func):
    """Allow only signed-in barbers (linked via Barber.user) to use their own dashboard."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not hasattr(request.user, 'barber_profile'):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped


# ──────────────────────────────────────────────────────────────
# Public pages
# ──────────────────────────────────────────────────────────────

def _barber_next_slot(barber, business_hours, now, days_ahead=14):
    """Earliest free slot for one barber across the upcoming business days."""
    step = slot_step_minutes()
    for i in range(0, days_ahead):
        d = now.date() + timedelta(days=i)
        bh = business_hours.get(d.weekday())
        if not bh or bh.is_closed:
            continue
        booked = _booked_times(d, barber_id=barber.id)
        for s in _generate_slots(bh.opening_time, bh.closing_time, step):
            slot_dt = datetime.combine(d, s)
            if d == now.date() and slot_dt <= now.replace(tzinfo=None):
                continue
            if s in booked:
                continue
            return slot_dt
    return None


def home(request):
    male_services = Service.objects.filter(is_active=True, category='MALE')
    female_services = Service.objects.filter(is_active=True, category='FEMALE')
    barbers = list(Barber.objects.filter(is_active=True))
    featured = next((b for b in barbers if b.name == 'Prashant Borhade'), None)
    barbers.sort(key=lambda b: (b is not featured, -float(b.rating)))
    business_hours = {bh.day: bh for bh in BusinessHour.objects.all()}
    now = timezone.localtime()
    for b in barbers:
        b.is_featured = b is featured
        next_slot = _barber_next_slot(b, business_hours, now)
        if next_slot:
            if next_slot.date() == now.date():
                b.next_slot_label = f"{next_slot.strftime('%I:%M %p')} today"
            elif next_slot.date() == now.date() + timedelta(days=1):
                b.next_slot_label = f"{next_slot.strftime('%I:%M %p')} tomorrow"
            else:
                b.next_slot_label = f"{next_slot.strftime('%a, %I:%M %p')}"
        else:
            b.next_slot_label = None
    available_dates = _available_dates(30)
    total_services_count = male_services.count() + female_services.count()
    context = {
        'male_services': male_services,
        'female_services': female_services,
        'total_services_count': total_services_count,
        'barbers': barbers,
        'available_dates': available_dates,
    }
    return render(request, 'home.html', context)


def about(request):
    business_hours = BusinessHour.objects.all()
    barbers = Barber.objects.filter(is_active=True)
    return render(request, 'about.html', {'business_hours': business_hours, 'barbers': barbers})


# ──────────────────────────────────────────────────────────────
# AJAX — Time Slots
# ──────────────────────────────────────────────────────────────

def get_time_slots(request):
    date_str = request.GET.get('date')
    service_id = request.GET.get('service_id')
    barber_id = request.GET.get('barber_id')
    
    if not date_str:
        return JsonResponse({'error': 'date is required'}, status=400)

    try:
        slot_date = date.fromisoformat(date_str)
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

    # The "Any Available" option is only bookable while the featured barber is
    # on duty. This makes the dashboard availability toggle affect the public
    # booking flow immediately.
    if not barber_id and not Barber.objects.filter(
        is_active=True,
        name='Prashant Borhade',
    ).exists():
        return JsonResponse({
            'slots': [],
            'message': 'No barber is available right now. Please check back soon.',
        })
        
    duration = 30
    if service_id:
        try:
            service = Service.objects.get(pk=service_id, is_active=True)
            duration = service.duration
        except Service.DoesNotExist:
            pass

    today = timezone.localdate()
    if slot_date < today:
        return JsonResponse({'error': 'Cannot book a past date.'}, status=400)

    try:
        bh = BusinessHour.objects.get(day=slot_date.weekday())
    except BusinessHour.DoesNotExist:
        return JsonResponse({'slots': [], 'message': 'No business hours configured.'})

    if bh.is_closed:
        return JsonResponse({'slots': [], 'message': 'Shop is closed on this day.'})

    all_slots = _generate_slots(bh.opening_time, bh.closing_time)
    booked = _booked_times(slot_date, barber_id=barber_id)

    now_local = timezone.localtime(timezone.now())
    buffer_time = (now_local + timedelta(minutes=30)).time() if slot_date == today else dtime.min

    slots_data = []
    closing_dt = datetime.combine(slot_date, bh.closing_time)
    
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

    return JsonResponse({'slots': slots_data})


# ──────────────────────────────────────────────────────────────
# Booking Creation  — NO login required (guests welcome)
# ──────────────────────────────────────────────────────────────

@require_POST
def create_booking(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

    service_id      = data.get('service_id')
    barber_id       = data.get('barber_id')
    date_str        = data.get('booking_date')
    time_str        = data.get('booking_time')
    full_name       = data.get('full_name', '').strip()
    phone           = data.get('phone', '').strip()
    email           = data.get('email', '').strip()
    special_request = data.get('special_request', '').strip()

    # ── Validate service ───────────────────────────────────────
    try:
        service = Service.objects.get(pk=service_id, is_active=True)
    except Service.DoesNotExist:
        return JsonResponse({'error': 'Service not found or inactive.'}, status=400)

    # ── Validate barber if provided ───────────────────────────
    selected_barber = None
    if barber_id:
        try:
            selected_barber = Barber.objects.get(pk=barber_id, is_active=True)
        except Barber.DoesNotExist:
            return JsonResponse({'error': 'Selected barber is no longer available.'}, status=400)
    elif not Barber.objects.filter(is_active=True, name='Prashant Borhade').exists():
        return JsonResponse({'error': 'No barber is available right now. Please check back soon.'}, status=400)

    # ── Validate date ──────────────────────────────────────────
    try:
        booking_date = date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid date.'}, status=400)

    today = timezone.localdate()
    if booking_date < today:
        return JsonResponse({'error': 'Cannot book a past date.'}, status=400)

    try:
        bh = BusinessHour.objects.get(day=booking_date.weekday())
    except BusinessHour.DoesNotExist:
        return JsonResponse({'error': 'Shop is closed on this day.'}, status=400)

    if bh.is_closed:
        return JsonResponse({'error': 'Shop is closed on this day.'}, status=400)

    # ── Validate time ──────────────────────────────────────────
    try:
        booking_time = datetime.strptime(time_str, '%H:%M').time()
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid time format.'}, status=400)

    if not (bh.opening_time <= booking_time < bh.closing_time):
        return JsonResponse({'error': 'Selected time is outside business hours.'}, status=400)

    if booking_date == today:
        now_local = timezone.localtime(timezone.now())
        if booking_time <= (now_local + timedelta(minutes=30)).time():
            return JsonResponse({'error': 'Please select a future time slot.'}, status=400)

    # ── Double-booking check ───────────────────────────────────
    check_qs = Booking.objects.filter(
        booking_date=booking_date,
        booking_time=booking_time,
        status__in=[Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED]
    )
    if selected_barber:
        check_qs = check_qs.filter(barber=selected_barber)

    if check_qs.exists():
        return JsonResponse({'error': 'This slot is already booked. Please choose another slot.'}, status=409)

    # ── Validate customer details ──────────────────────────────
    if not full_name:
        return JsonResponse({'error': 'Full name is required.'}, status=400)
    if not phone or len(''.join(filter(str.isdigit, phone))) < 10:
        return JsonResponse({'error': 'Please enter a valid mobile number.'}, status=400)

    # ── Create Booking + Payment ───────────────────────────────
    booking = Booking.objects.create(
        user=request.user if request.user.is_authenticated else None,
        service=service,
        barber=selected_barber,
        booking_date=booking_date,
        booking_time=booking_time,
        customer_name=full_name,
        customer_phone=phone,
        customer_email=email,
        special_request=special_request,
        amount=service.price,
        status=Booking.STATUS_PENDING,
    )

    Payment.objects.create(
        booking=booking,
        amount=service.price,
        payment_method='MOCK' if settings.PAYMENT_MODE == 'MOCK' else 'ONLINE',
        status=Payment.STATUS_PENDING,
    )

    _add_booking_to_session(request, booking.booking_id)

    return JsonResponse({'success': True, 'redirect': f'/payment/{booking.booking_id}/'})


# ──────────────────────────────────────────────────────────────
# Payment & Confirmation
# ──────────────────────────────────────────────────────────────

def _can_access_booking(request, booking):
    if request.user.is_authenticated and booking.user == request.user:
        return True
    if booking.booking_id in _session_booking_ids(request):
        return True
    return False


def payment_page(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id)

    if not _can_access_booking(request, booking):
        messages.error(request, "You don't have access to this booking.")
        return redirect('home')

    if booking.status == Booking.STATUS_CONFIRMED:
        return redirect('booking_confirm', booking_id=booking.booking_id)
    if booking.status == Booking.STATUS_CANCELLED:
        messages.error(request, "This booking has been cancelled.")
        return redirect('home')

    payment, _ = Payment.objects.get_or_create(
        booking=booking,
        defaults={'amount': booking.amount, 'status': Payment.STATUS_PENDING}
    )

    shop_upi_id = "9921028084@okbizaxis"
    shop_upi_name = "24 K HAIR STUDIO"
    shop_phone = "+91 99210 28084"
    
    # Format amount cleanly
    amt_val = booking.amount
    amount_str = str(int(amt_val)) if amt_val == int(amt_val) else f"{amt_val:.2f}"

    # Clean Official NPCI Web Intent Query (No mode=01 / aid / tr which triggers security/risky fraud flags on web deep links)
    merchant_query = f"pa={shop_upi_id}&pn=24%20K%20HAIR%20STUDIO&mc=7230&am={amount_str}&cu=INR&tn=24K%20Salon"
    
    # Universal UPI link (for Any UPI App / QR Scanner)
    upi_link = f"upi://pay?{merchant_query}"
    
    # Dedicated Android Package Intents to open specific apps directly (prevents WhatsApp hijack)
    gpay_link = f"intent://pay?{merchant_query}#Intent;scheme=upi;package=com.google.android.apps.nbu.paisa.user;end"
    phonepe_link = f"intent://pay?{merchant_query}#Intent;scheme=upi;package=com.phonepe.app;end"
    paytm_link = f"intent://pay?{merchant_query}#Intent;scheme=upi;package=net.one97.paytm;end"

    # Generate crisp dynamic QR Code using local Python qrcode (offline, zero third-party dependency)
    qr_code_url = ""
    try:
        import io, base64, qrcode
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(upi_link)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_code_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as e:
        encoded_upi_link = urllib.parse.quote(upi_link, safe='')
        qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?data={encoded_upi_link}&size=340x340&margin=12&color=000000&bgcolor=ffffff"

    context = {
        'booking': booking,
        'payment': payment,
        'shop_upi_id': shop_upi_id,
        'shop_upi_name': shop_upi_name,
        'shop_phone': shop_phone,
        'gpay_standee_img': '/static/images/gpay_standee_qr.jpg',
        'merchant_query': merchant_query,
        'upi_link': upi_link,
        'gpay_link': gpay_link,
        'phonepe_link': phonepe_link,
        'paytm_link': paytm_link,
        'qr_code_url': qr_code_url,
    }
    return render(request, 'payment/pay.html', context)


@barber_required
@require_POST
def barber_verify_payment(request, booking_id):
    """Barber or Admin verifies the customer's UPI payment in salon when service is done."""
    booking = get_object_or_404(Booking, booking_id=booking_id)

    # If not staff, barber can only verify their own appointments
    if not request.user.is_staff:
        barber = getattr(request.user, 'barber_profile', None)
        if not barber or booking.barber != barber:
            messages.error(request, "You can only verify payments for your own appointments.")
            return redirect('barber_dashboard')

    payment, _ = Payment.objects.get_or_create(
        booking=booking,
        defaults={'amount': booking.amount}
    )
    payment.is_verified_by_barber = True
    payment.status = Payment.STATUS_PAID
    payment.verified_at = timezone.now()
    payment.verified_by = request.user
    payment.save()

    # If requested to also complete the service
    if request.POST.get('complete_service') == '1':
        booking.status = Booking.STATUS_COMPLETED
        booking.save()
        messages.success(request, f"Payment for {booking.booking_id} verified & service marked Completed!")
    else:
        messages.success(request, f"Payment for {booking.booking_id} verified in salon by {request.user.get_full_name() or request.user.username}!")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_verified': True,
            'booking_status': booking.status,
            'booking_id': booking.booking_id
        })

    return redirect(request.META.get('HTTP_REFERER', 'barber_dashboard'))


@require_POST
def process_mock_payment(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id)

    if not _can_access_booking(request, booking):
        messages.error(request, "You don't have access to this booking.")
        return redirect('home')

    if booking.status != Booking.STATUS_PENDING:
        messages.error(request, "This booking cannot be processed.")
        return redirect('home')

    payment, _ = Payment.objects.get_or_create(
        booking=booking,
        defaults={'amount': booking.amount}
    )

    utr_number = request.POST.get('utr_number', '').strip()
    if utr_number:
        txn_id = f"UPI-{utr_number}"
    else:
        txn_id = f"UPI-{booking.booking_id}-{uuid.uuid4().hex[:6].upper()}"

    payment.transaction_id = txn_id
    payment.status = Payment.STATUS_PAID
    payment.payment_method = 'UPI'
    payment.is_verified_by_barber = False
    payment.save()

    booking.status = Booking.STATUS_CONFIRMED
    booking.save()

    # ── Send confirmation SMS + schedule reminders ─────────────────────────
    try:
        from .sms import send_booking_confirmation, schedule_reminders
        send_booking_confirmation(booking)
        schedule_reminders(booking)
    except Exception as exc:
        # Never fail the booking flow because of SMS errors
        import logging
        logging.getLogger(__name__).exception(f'SMS error for {booking_id}: {exc}')

    return redirect('booking_confirm', booking_id=booking.booking_id)


def booking_confirm(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id)

    if not _can_access_booking(request, booking):
        messages.error(request, "You don't have access to this booking.")
        return redirect('home')

    return render(request, 'bookings/confirm.html', {'booking': booking})


# ──────────────────────────────────────────────────────────────
# Barber Agenda (Public Stack)
# ──────────────────────────────────────────────────────────────

def barber_agenda(request):
    today = timezone.localdate()
    now_time = timezone.localtime(timezone.now()).time()

    bookings = Booking.objects.filter(
        booking_date=today,
        status__in=[Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED]
    ).select_related('service', 'barber').order_by('booking_time')

    ongoing_bookings = []
    upcoming_bookings = []
    completed_count = 0
    active_bookings = []

    for b in bookings:
        start_dt = datetime.combine(today, b.booking_time)
        end_dt = start_dt + timedelta(minutes=b.service.duration)
        b.is_ongoing = start_dt.time() <= now_time < end_dt.time()
        b.is_past = end_dt.time() <= now_time
        b.end_time = end_dt.time()

        if b.is_ongoing:
            ongoing_bookings.append(b)
            active_bookings.append(b)
        elif b.is_past:
            completed_count += 1
        else:
            upcoming_bookings.append(b)
            active_bookings.append(b)

    return render(request, 'bookings/agenda.html', {
        'bookings': active_bookings,
        'ongoing_bookings': ongoing_bookings,
        'upcoming_bookings': upcoming_bookings,
        'completed_count': completed_count,
        'date': today,
        'now_time': now_time,
    })


# ──────────────────────────────────────────────────────────────
# Admin Dashboard Views
# ──────────────────────────────────────────────────────────────

def barber_dashboard(request):
    """Route each signed-in person to the right dashboard.

    Shop staff get the full management dashboard (even if they also hold a
    barber profile); everyone with a barber profile gets their personal desk.
    """
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())

    if request.user.is_staff:
        return _admin_dashboard(request)

    barber_profile = getattr(request.user, 'barber_profile', None)
    if barber_profile is not None:
        return _barber_dashboard(request, barber_profile)

    raise PermissionDenied


def _barber_dashboard(request, barber):
    today = timezone.localdate()
    now_time = timezone.localtime().time()

    bookings = Booking.objects.filter(barber=barber).select_related('service', 'payment')
    today_qs = bookings.filter(booking_date=today).exclude(status=Booking.STATUS_CANCELLED).order_by('booking_time')

    status_filter = request.GET.get('status', 'TODAY')
    qs = bookings.order_by('-booking_date', '-booking_time')
    if status_filter == 'TODAY':
        qs = qs.filter(booking_date=today)
    elif status_filter in [Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED, Booking.STATUS_COMPLETED, Booking.STATUS_CANCELLED]:
        qs = qs.filter(status=status_filter)

    next_appointment = bookings.filter(
        status__in=[Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED],
        booking_date__gte=today,
    ).order_by('booking_date', 'booking_time').first()

    revenue_paid = bookings.filter(payment__status=Payment.STATUS_PAID).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'barber': barber,
        'today': today,
        'today_bookings': today_qs.count(),
        'today_schedule': today_qs[:8],
        'next_appointment': next_appointment,
        'pending_count': bookings.filter(status=Booking.STATUS_PENDING).count(),
        'confirmed_count': bookings.filter(status=Booking.STATUS_CONFIRMED).count(),
        'completed_count': bookings.filter(status=Booking.STATUS_COMPLETED).count(),
        'cancelled_count': bookings.filter(status=Booking.STATUS_CANCELLED).count(),
        'revenue_paid': revenue_paid,
        'bookings': qs[:25],
        'status_filter': status_filter,
    }
    return render(request, 'barber_dashboard_me.html', context)


def _admin_dashboard(request):
    today = timezone.localdate()
    now_time = timezone.localtime().time()

    all_bookings = Booking.objects.select_related('service', 'barber', 'payment')
    all_payments = Payment.objects.all()

    # Metrics
    total_revenue = all_payments.filter(status=Payment.STATUS_PAID).aggregate(total=Sum('amount'))['total'] or 0
    today_revenue = all_payments.filter(
        booking__booking_date=today,
        status=Payment.STATUS_PAID
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_bookings_count = all_bookings.count()
    today_bookings_qs = all_bookings.filter(booking_date=today)
    today_bookings_count = today_bookings_qs.count()

    pending_count = all_bookings.filter(status=Booking.STATUS_PENDING).count()
    confirmed_count = all_bookings.filter(status=Booking.STATUS_CONFIRMED).count()
    completed_count = all_bookings.filter(status=Booking.STATUS_COMPLETED).count()
    cancelled_count = all_bookings.filter(status=Booking.STATUS_CANCELLED).count()

    # A compact, time-ordered view keeps the most important part of the
    # dashboard usable between appointments.
    today_schedule = today_bookings_qs.exclude(
        status=Booking.STATUS_CANCELLED
    ).order_by('booking_time')[:6]
    next_appointment = today_bookings_qs.filter(
        status__in=[Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED],
        booking_time__gte=now_time,
    ).order_by('booking_time').first()

    # Barber Stats
    barbers = Barber.objects.all()
    for b in barbers:
        b.total_appointments = b.bookings.count()
        b.completed_appointments = b.bookings.filter(status=Booking.STATUS_COMPLETED).count()
        b.revenue = b.bookings.filter(payment__status=Payment.STATUS_PAID).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'active_nav': 'dashboard',
        'total_revenue': total_revenue,
        'today_revenue': today_revenue,
        'total_bookings': total_bookings_count,
        'today_bookings': today_bookings_count,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'barbers': barbers,
        'today': today,
        'today_schedule': today_schedule,
        'next_appointment': next_appointment,
        'active_barbers_count': barbers.filter(is_active=True).count(),
    }
    return render(request, 'admin_dashboard.html', context)


@barber_staff_required
def admin_appointments(request):
    today = timezone.localdate()
    status_filter = request.GET.get('status', 'ALL')
    search_q = request.GET.get('q', '').strip()
    date_filter = request.GET.get('date', '').strip()

    qs = Booking.objects.select_related('service', 'barber', 'payment').order_by('-booking_date', '-booking_time')

    if status_filter == 'TODAY':
        qs = qs.filter(booking_date=today)
    elif status_filter in [Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED, Booking.STATUS_COMPLETED, Booking.STATUS_CANCELLED]:
        qs = qs.filter(status=status_filter)

    if date_filter:
        try:
            parsed_d = date.fromisoformat(date_filter)
            qs = qs.filter(booking_date=parsed_d)
        except ValueError:
            pass

    if search_q:
        qs = qs.filter(
            Q(booking_id__icontains=search_q) |
            Q(customer_name__icontains=search_q) |
            Q(customer_phone__icontains=search_q) |
            Q(customer_email__icontains=search_q)
        )

    context = {
        'active_nav': 'appointments',
        'bookings': qs[:100],
        'status_filter': status_filter,
        'search_q': search_q,
        'date_filter': date_filter,
        'today': today,
    }
    return render(request, 'admin_appointments.html', context)


@barber_staff_required
def admin_barbers(request):
    """View and manage all barbers, duty status, and metrics."""
    barbers = list(Barber.objects.all().order_by('-is_active', 'name'))
    today = timezone.localdate()

    for b in barbers:
        b_bookings = Booking.objects.filter(barber=b)
        b.total_appointments = b_bookings.count()
        b.today_appointments = b_bookings.filter(booking_date=today).exclude(status=Booking.STATUS_CANCELLED).count()
        b.revenue = b_bookings.filter(payment__status=Payment.STATUS_PAID).aggregate(total=Sum('amount'))['total'] or 0

    active_count = sum(1 for b in barbers if b.is_active)
    context = {
        'active_nav': 'barbers',
        'barbers': barbers,
        'today': today,
        'total_barbers': len(barbers),
        'active_barbers_count': active_count,
        'inactive_barbers_count': len(barbers) - active_count,
    }
    return render(request, 'admin_barbers.html', context)


@barber_staff_required
@require_POST
def admin_add_barber(request):
    """Create a new barber profile, with optional staff login account."""
    name = request.POST.get('name', '').strip()
    title = request.POST.get('title', '').strip() or 'Master Barber'
    email = request.POST.get('email', '').strip()
    specialties = request.POST.get('specialties', '').strip() or 'Skin Fade, Beard Styling, Hair Design'
    avatar_icon = request.POST.get('avatar_icon', '').strip() or 'user-tie'

    try:
        experience_years = int(request.POST.get('experience_years', '5'))
    except (ValueError, TypeError):
        experience_years = 5

    try:
        rating = Decimal(request.POST.get('rating', '4.9'))
    except Exception:
        rating = Decimal('4.9')

    is_active = request.POST.get('is_active') == '1' or 'is_active' in request.POST
    photo = request.FILES.get('photo')

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'admin_dashboard'

    if not name:
        messages.error(request, "Barber name is required.")
        return redirect(next_url)

    linked_user = None
    if email:
        username = email
        user = User.objects.filter(username=username).first() or User.objects.filter(email=email).first()
        if not user:
            user = User.objects.create_user(
                username=username,
                email=email,
                password='admin',
                first_name=name.split()[0] if name else '',
                last_name=' '.join(name.split()[1:]) if len(name.split()) > 1 else ''
            )
        user.is_staff = True
        user.set_password('admin')
        user.save()
        linked_user = user

    barber = Barber.objects.create(
        name=name,
        title=title,
        specialties=specialties,
        avatar_icon=avatar_icon,
        experience_years=experience_years,
        rating=rating,
        is_active=is_active,
        user=linked_user,
        photo=photo if photo else None
    )

    login_msg = f" Login email: '{email}', password: 'admin'." if email else ""
    messages.success(request, f"Barber {barber.name} added successfully!{login_msg}")
    return redirect(next_url)


@barber_staff_required
@require_POST
def admin_edit_barber(request, barber_id):
    """Edit existing barber details, specialties, or upload a new photo."""
    barber = get_object_or_404(Barber, pk=barber_id)
    name = request.POST.get('name', '').strip()
    title = request.POST.get('title', '').strip()
    specialties = request.POST.get('specialties', '').strip()
    try:
        experience_years = int(request.POST.get('experience_years', barber.experience_years))
    except (ValueError, TypeError):
        experience_years = barber.experience_years

    if name:
        barber.name = name
    if title:
        barber.title = title
    if specialties:
        barber.specialties = specialties
    barber.experience_years = experience_years

    if 'photo' in request.FILES:
        barber.photo = request.FILES['photo']

    barber.save()

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'admin_barbers'
    messages.success(request, f"Barber {barber.name}'s profile and photo updated successfully!")
    return redirect(next_url)


@barber_staff_required
@require_POST
def admin_delete_barber(request, barber_id):
    """Safely delete a barber and their linked staff login account."""
    barber = get_object_or_404(Barber, pk=barber_id)
    name = barber.name
    linked_user = barber.user

    # Delete the barber record (associated Bookings will have barber set to NULL)
    barber.delete()

    # If linked user is not superuser and not main admin, remove login account
    if linked_user and not linked_user.is_superuser and linked_user.username != 'admin':
        try:
            linked_user.delete()
        except Exception:
            pass

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'admin_dashboard'
    messages.success(request, f"Barber {name} has been deleted.")
    return redirect(next_url)


@barber_staff_required
def admin_services(request):
    """Manage service rates, durations, ordering and availability."""
    if request.method == 'POST':
        updated = 0
        for pk in request.POST.getlist('service_pk'):
            svc = Service.objects.filter(pk=pk).first()
            if not svc:
                continue
            name = request.POST.get(f'name_{pk}', '').strip()
            try:
                price = Decimal(request.POST.get(f'price_{pk}', ''))
                duration = int(request.POST.get(f'dur_{pk}', ''))
                sort_order = int(request.POST.get(f'sort_{pk}', '0'))
            except (TypeError, ValueError):
                continue
            if price < 0 or duration < 5 or duration > 720:
                continue
            if name:
                svc.name = name
            svc.price = price
            svc.duration = duration
            svc.sort_order = sort_order
            svc.is_active = f'active_{pk}' in request.POST
            svc.save()
            updated += 1

        if updated:
            messages.success(request, f"{updated} service(s) updated.")
        else:
            messages.error(request, "No valid service rows to update.")
        return redirect('admin_services')

    services = Service.objects.all().order_by('sort_order', 'category', 'price')
    context = {
        'active_nav': 'services',
        'services': services,
    }
    return render(request, 'admin_services.html', context)


@barber_staff_required
def admin_hours(request):
    """Set opening/closing time and closed days for the whole week."""
    if request.method == 'POST':
        updated = 0
        for day in range(7):
            bh, _ = BusinessHour.objects.get_or_create(day=day)
            if f'closed_{day}' in request.POST:
                bh.is_closed = True
                bh.save()
                updated += 1
                continue
            try:
                open_t = datetime.strptime(request.POST.get(f'opening_{day}', ''), '%H:%M').time()
                close_t = datetime.strptime(request.POST.get(f'closing_{day}', ''), '%H:%M').time()
            except (ValueError, TypeError):
                continue
            if close_t <= open_t:
                continue
            bh.opening_time = open_t
            bh.closing_time = close_t
            bh.is_closed = False
            bh.save()
            updated += 1

        if updated:
            messages.success(request, f"Business hours updated for {updated} day(s).")
        else:
            messages.error(request, "No valid hours rows to update.")
        return redirect('admin_hours')

    business_hours = [BusinessHour.objects.get_or_create(day=d)[0] for d in range(7)]
    hour_options = []
    start_dt = datetime.combine(datetime.today(), datetime.strptime('09:00', '%H:%M').time())
    end_dt = datetime.combine(datetime.today(), datetime.strptime('23:45', '%H:%M').time())
    cur = start_dt
    while cur <= end_dt:
        hour_options.append(cur.strftime('%H:%M'))
        cur += timedelta(minutes=15)
    context = {
        'active_nav': 'hours',
        'business_hours': business_hours,
        'hour_options': hour_options,
    }
    return render(request, 'admin_hours.html', context)


@barber_staff_required
def admin_settings(request):
    """Shop-wide knobs: slot duration and Salon Direct UPI Payment settings."""
    if request.method == 'POST':
        # Slot duration step
        try:
            step = int(request.POST.get('slot_step', '30'))
        except (TypeError, ValueError):
            step = 30
        step = max(5, min(step, 120))
        ShopSetting.objects.update_or_create(key='slot_step', defaults={'value': str(step)})

        # Shop UPI ID & Name
        shop_upi_id = request.POST.get('shop_upi_id', '').strip()
        shop_upi_name = request.POST.get('shop_upi_name', '').strip()

        if shop_upi_id:
            ShopSetting.objects.update_or_create(key='shop_upi_id', defaults={'value': shop_upi_id})
        if shop_upi_name:
            ShopSetting.objects.update_or_create(key='shop_upi_name', defaults={'value': shop_upi_name})

        messages.success(request, "Shop settings and Salon UPI payment details updated successfully.")
        return redirect('admin_settings')

    context = {
        'active_nav': 'settings',
        'slot_step': slot_step_minutes(),
        'slot_choices': [15, 20, 30, 45, 60, 90, 120],
        'shop_upi_id': get_shop_upi_id(),
        'shop_upi_name': get_shop_upi_name(),
    }
    return render(request, 'admin_settings.html', context)


@barber_required
@require_POST
def barber_update_status(request, booking_id):
    """A barber can update the status of their own bookings only."""
    barber = request.user.barber_profile
    booking = get_object_or_404(Booking, booking_id=booking_id, barber=barber)
    new_status = request.POST.get('status')

    if new_status in [Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED, Booking.STATUS_COMPLETED, Booking.STATUS_CANCELLED]:
        booking.status = new_status
        booking.save()

        try:
            payment = booking.payment
            if new_status in [Booking.STATUS_CONFIRMED, Booking.STATUS_COMPLETED] and payment.status == Payment.STATUS_PENDING:
                payment.status = Payment.STATUS_PAID
                payment.save()
            elif new_status == Booking.STATUS_CANCELLED and payment.status == Payment.STATUS_PAID:
                payment.status = Payment.STATUS_REFUNDED
                payment.save()
        except Payment.DoesNotExist:
            pass

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'status': booking.status, 'status_display': booking.get_status_display()})

        messages.success(request, f"Booking {booking.booking_id} status updated to {booking.get_status_display()}.")
    else:
        messages.error(request, "Invalid status choice.")

    return redirect('barber_dashboard')


@barber_staff_required
@require_POST
def admin_update_status(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id)
    new_status = request.POST.get('status')

    if new_status in [Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED, Booking.STATUS_COMPLETED, Booking.STATUS_CANCELLED]:
        booking.status = new_status
        booking.save()

        try:
            payment = booking.payment
            if new_status in [Booking.STATUS_CONFIRMED, Booking.STATUS_COMPLETED] and payment.status == Payment.STATUS_PENDING:
                payment.status = Payment.STATUS_PAID
                payment.save()
            elif new_status == Booking.STATUS_CANCELLED and payment.status == Payment.STATUS_PAID:
                payment.status = Payment.STATUS_REFUNDED
                payment.save()
        except Payment.DoesNotExist:
            pass

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'status': booking.status, 'status_display': booking.get_status_display()})

        messages.success(request, f"Booking {booking.booking_id} status updated to {booking.get_status_display()}.")
    else:
        messages.error(request, "Invalid status choice.")

    return redirect('barber_dashboard')


@barber_staff_required
@require_POST
def admin_toggle_barber(request, barber_id):
    barber = get_object_or_404(Barber, pk=barber_id)
    barber.is_active = not barber.is_active
    barber.save()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'is_active': barber.is_active})

    messages.success(request, f"Barber {barber.name} status updated.")
    return redirect('barber_dashboard')


@barber_staff_required
@require_POST
def admin_send_notification(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id)
    message_text = request.POST.get('message', '').strip()
    
    if not message_text:
        message_text = f"Hello {booking.customer_name}, reminder for your {booking.service.name} appointment on {booking.booking_date.strftime('%d %b %Y')} at {booking.booking_time.strftime('%I:%M %p')} with 24 K Barbershop."

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'booking_id': booking.booking_id,
            'customer_name': booking.customer_name,
            'customer_phone': booking.customer_phone,
            'message': message_text
        })

    messages.success(request, f"Notification message logged for {booking.customer_name} ({booking.customer_phone}).")
    return redirect('barber_dashboard')


# ──────────────────────────────────────────────────────────────
# My Bookings
# ──────────────────────────────────────────────────────────────

def booking_list(request):
    status_filter = request.GET.get('status', 'ALL')
    today = timezone.localdate()

    if request.user.is_authenticated:
        qs = Booking.objects.filter(user=request.user).select_related('service', 'barber', 'payment')
    else:
        session_ids = _session_booking_ids(request)
        qs = Booking.objects.filter(booking_id__in=session_ids).select_related('service', 'barber', 'payment')

    if status_filter == 'UPCOMING':
        qs = qs.filter(
            booking_date__gte=today,
            status__in=[Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED]
        )
    elif status_filter == 'COMPLETED':
        qs = qs.filter(status=Booking.STATUS_COMPLETED)
    elif status_filter == 'CANCELLED':
        qs = qs.filter(status=Booking.STATUS_CANCELLED)
    elif status_filter == 'CONFIRMED':
        qs = qs.filter(status=Booking.STATUS_CONFIRMED)

    next_booking = None
    if status_filter == 'ALL':
        if request.user.is_authenticated:
            next_qs = Booking.objects.filter(
                user=request.user,
                booking_date__gte=today,
                status__in=[Booking.STATUS_CONFIRMED, Booking.STATUS_PENDING]
            )
        else:
            session_ids = _session_booking_ids(request)
            next_qs = Booking.objects.filter(
                booking_id__in=session_ids,
                booking_date__gte=today,
                status__in=[Booking.STATUS_CONFIRMED, Booking.STATUS_PENDING]
            )
        next_booking = next_qs.select_related('service', 'barber').order_by('booking_date', 'booking_time').first()

    context = {
        'bookings': qs,
        'status_filter': status_filter,
        'next_booking': next_booking,
        'today': today,
    }
    return render(request, 'bookings/list.html', context)


def booking_detail(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related('service', 'barber', 'payment'),
        booking_id=booking_id,
    )

    if not _can_access_booking(request, booking):
        messages.error(request, "You don't have access to this booking.")
        return redirect('home')

    business_hours = BusinessHour.objects.all()
    return render(request, 'bookings/detail.html', {'booking': booking, 'business_hours': business_hours})


@require_POST
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id)

    if not _can_access_booking(request, booking):
        messages.error(request, "You don't have access to this booking.")
        return redirect('home')

    if not booking.can_be_cancelled:
        messages.error(request, "This booking cannot be cancelled.")
        return redirect('booking_detail', booking_id=booking.booking_id)

    booking.status = Booking.STATUS_CANCELLED
    booking.save()

    try:
        payment = booking.payment
        if payment.status == Payment.STATUS_PAID:
            payment.status = Payment.STATUS_REFUNDED
            payment.save()
    except Payment.DoesNotExist:
        pass

    messages.success(request, f"Booking {booking.booking_id} has been cancelled.")
    return redirect('booking_list')
