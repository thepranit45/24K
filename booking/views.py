import json
import uuid
from datetime import date, datetime, timedelta, time as dtime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CustomerDetailsForm
from .models import Barber, Booking, BusinessHour, Payment, Service


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _generate_slots(open_t: dtime, close_t: dtime, step_minutes: int = 30):
    slots = []
    current = datetime.combine(date.today(), open_t)
    end = datetime.combine(date.today(), close_t)
    while current < end:
        slots.append(current.time())
        current += timedelta(minutes=step_minutes)
    return slots


def _booked_times(booking_date: date, barber_id=None):
    qs = Booking.objects.filter(
        booking_date=booking_date,
        status__in=[Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED]
    )
    if barber_id:
        qs = qs.filter(barber_id=barber_id)
        
    bookings = qs.select_related('service')
    
    booked_slots = set()
    for b in bookings:
        current_time = datetime.combine(booking_date, b.booking_time)
        end_time = current_time + timedelta(minutes=b.service.duration)
        
        while current_time < end_time:
            booked_slots.add(current_time.time())
            current_time += timedelta(minutes=30)
            
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


# ──────────────────────────────────────────────────────────────
# Public pages
# ──────────────────────────────────────────────────────────────

def home(request):
    male_services = Service.objects.filter(is_active=True, category='MALE')
    female_services = Service.objects.filter(is_active=True, category='FEMALE')
    barbers = Barber.objects.filter(is_active=True)
    available_dates = _available_dates(30)
    context = {
        'male_services': male_services,
        'female_services': female_services,
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
            pass

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

    context = {
        'booking': booking,
        'payment_mode': settings.PAYMENT_MODE,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
    }
    return render(request, 'payment/pay.html', context)


@require_POST
def process_mock_payment(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id)

    if not _can_access_booking(request, booking):
        messages.error(request, "You don't have access to this booking.")
        return redirect('home')

    if booking.status != Booking.STATUS_PENDING:
        messages.error(request, "This booking cannot be processed.")
        return redirect('home')

    payment = get_object_or_404(Payment, booking=booking)

    if payment.status == Payment.STATUS_PAID:
        return redirect('booking_confirm', booking_id=booking.booking_id)

    txn_id = f"MOCK-TXN-{uuid.uuid4().hex[:12].upper()}"
    payment.transaction_id = txn_id
    payment.status = Payment.STATUS_PAID
    payment.payment_method = 'MOCK'
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

def admin_dashboard(request):
    today = timezone.localdate()
    status_filter = request.GET.get('status', 'ALL')
    search_q = request.GET.get('q', '').strip()
    date_filter = request.GET.get('date', '').strip()

    all_bookings = Booking.objects.select_related('service', 'barber', 'payment')
    all_payments = Payment.objects.all()

    # Metrics
    total_revenue = all_payments.filter(status=Payment.STATUS_PAID).aggregate(total=Sum('amount'))['total'] or 0
    today_revenue = all_payments.filter(
        booking__booking_date=today,
        status=Payment.STATUS_PAID
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_bookings_count = all_bookings.count()
    today_bookings_count = all_bookings.filter(booking_date=today).count()

    pending_count = all_bookings.filter(status=Booking.STATUS_PENDING).count()
    confirmed_count = all_bookings.filter(status=Booking.STATUS_CONFIRMED).count()
    completed_count = all_bookings.filter(status=Booking.STATUS_COMPLETED).count()
    cancelled_count = all_bookings.filter(status=Booking.STATUS_CANCELLED).count()

    # Query table
    qs = all_bookings.order_by('-booking_date', '-booking_time')

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

    # Barber Stats
    barbers = Barber.objects.all()
    for b in barbers:
        b.total_appointments = b.bookings.count()
        b.completed_appointments = b.bookings.filter(status=Booking.STATUS_COMPLETED).count()
        b.revenue = b.bookings.filter(payment__status=Payment.STATUS_PAID).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'total_revenue': total_revenue,
        'today_revenue': today_revenue,
        'total_bookings': total_bookings_count,
        'today_bookings': today_bookings_count,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'bookings': qs[:50],
        'barbers': barbers,
        'status_filter': status_filter,
        'search_q': search_q,
        'date_filter': date_filter,
        'today': today,
    }
    return render(request, 'admin_dashboard.html', context)


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

    return redirect('admin_dashboard')


@require_POST
def admin_toggle_barber(request, barber_id):
    barber = get_object_or_404(Barber, pk=barber_id)
    barber.is_active = not barber.is_active
    barber.save()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'is_active': barber.is_active})

    messages.success(request, f"Barber {barber.name} status updated.")
    return redirect('admin_dashboard')


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
    return redirect('admin_dashboard')


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
