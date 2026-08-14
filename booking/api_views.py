"""
Barber REST API — for the Android Barber Management App.
Provides authentication + booking management endpoints.

Endpoints:
  POST   /api/barber/login/
  POST   /api/barber/logout/
  GET    /api/barber/stats/
  GET    /api/barber/bookings/today/
  GET    /api/barber/bookings/upcoming/
  GET    /api/barber/bookings/
  GET    /api/barber/bookings/<booking_id>/
  POST   /api/barber/bookings/<booking_id>/confirm/
  POST   /api/barber/bookings/<booking_id>/complete/
  POST   /api/barber/bookings/<booking_id>/cancel/
  POST   /api/barber/fcm-token/
"""

import json
import logging
from datetime import datetime, timedelta

from django.contrib.auth import authenticate
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Barber, Booking, Service

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _booking_dict(booking) -> dict:
    """Serialize a Booking object to dict for JSON response."""
    return {
        'id': booking.pk,
        'booking_id': booking.booking_id,
        'customer_name': booking.customer_name,
        'customer_phone': booking.customer_phone,
        'customer_email': booking.customer_email,
        'service': {
            'id': booking.service.pk,
            'name': booking.service.name,
            'duration': booking.service.duration,
            'price': str(booking.amount),
        },
        'barber': {
            'id': booking.barber.pk,
            'name': booking.barber.name,
        } if booking.barber else None,
        'booking_date': booking.booking_date.isoformat(),
        'booking_time': booking.booking_time.strftime('%H:%M'),
        'status': booking.status,
        'special_request': booking.special_request,
        'amount': str(booking.amount),
        'created_at': booking.created_at.isoformat(),
    }


def _error(msg: str, status: int = 400) -> JsonResponse:
    return JsonResponse({'success': False, 'error': msg}, status=status)


def _ok(data: dict = None, **kwargs) -> JsonResponse:
    payload = {'success': True}
    if data:
        payload.update(data)
    payload.update(kwargs)
    return JsonResponse(payload)


def _get_token_user(request):
    """Extract user from JWT Bearer token. Returns user or None."""
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return None
    token_str = auth_header[7:]
    try:
        from rest_framework_simplejwt.tokens import AccessToken
        token = AccessToken(token_str)
        from django.contrib.auth.models import User
        return User.objects.get(pk=token['user_id'])
    except Exception:
        return None


def _require_auth(view_func):
    """Decorator: require valid JWT, inject request.barber_user."""
    def wrapper(request, *args, **kwargs):
        user = _get_token_user(request)
        if not user:
            return JsonResponse({'success': False, 'error': 'Authentication required.'}, status=401)
        if not (user.is_staff or user.is_superuser):
            return JsonResponse({'success': False, 'error': 'Staff access only.'}, status=403)
        request.barber_user = user
        return view_func(request, *args, **kwargs)
    return wrapper


# ──────────────────────────────────────────────────────────────
# Authentication
# ──────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def barber_login(request):
    """
    POST /api/barber/login/
    Body: {"username": "...", "password": "..."}
    Returns: {access_token, refresh_token, user: {id, username, name}}
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return _error('Invalid JSON body.')

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return _error('Username and password are required.')

    user = authenticate(request, username=username, password=password)
    if not user:
        return _error('Invalid username or password.', 401)

    if not (user.is_staff or user.is_superuser):
        return _error('This account does not have barber/staff access.', 403)

    refresh = RefreshToken.for_user(user)
    return _ok({
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh),
        'user': {
            'id': user.pk,
            'username': user.username,
            'name': user.get_full_name() or user.username,
            'email': user.email,
        }
    })


@csrf_exempt
@require_POST
def barber_logout(request):
    """
    POST /api/barber/logout/
    Body: {"refresh_token": "..."}
    Blacklists the refresh token.
    """
    try:
        data = json.loads(request.body)
        token = RefreshToken(data.get('refresh_token', ''))
        token.blacklist()
    except Exception:
        pass
    return _ok(message='Logged out.')


# ──────────────────────────────────────────────────────────────
# Dashboard Stats
# ──────────────────────────────────────────────────────────────

@csrf_exempt
@_require_auth
def barber_stats(request):
    """
    GET /api/barber/stats/
    Returns today's and overall booking counts + revenue.
    """
    today = timezone.localdate()
    today_qs = Booking.objects.filter(booking_date=today)
    all_qs = Booking.objects

    stats = {
        'today': {
            'total': today_qs.count(),
            'pending': today_qs.filter(status=Booking.STATUS_PENDING).count(),
            'confirmed': today_qs.filter(status=Booking.STATUS_CONFIRMED).count(),
            'completed': today_qs.filter(status=Booking.STATUS_COMPLETED).count(),
            'cancelled': today_qs.filter(status=Booking.STATUS_CANCELLED).count(),
            'revenue': str(
                today_qs.filter(status=Booking.STATUS_COMPLETED)
                .aggregate(t=Sum('amount'))['t'] or 0
            ),
        },
        'all_time': {
            'total': all_qs.count(),
            'completed': all_qs.filter(status=Booking.STATUS_COMPLETED).count(),
            'revenue': str(
                all_qs.filter(status=Booking.STATUS_COMPLETED)
                .aggregate(t=Sum('amount'))['t'] or 0
            ),
        },
        'upcoming_count': Booking.objects.filter(
            booking_date__gte=today,
            status__in=[Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED]
        ).count(),
    }
    return _ok({'stats': stats})


# ──────────────────────────────────────────────────────────────
# Booking Lists
# ──────────────────────────────────────────────────────────────

@csrf_exempt
@_require_auth
def barber_bookings_today(request):
    """
    GET /api/barber/bookings/today/
    Returns all bookings for today, ordered by time.
    """
    today = timezone.localdate()
    bookings = (
        Booking.objects
        .filter(booking_date=today)
        .select_related('service', 'barber')
        .order_by('booking_time')
    )
    return _ok({'bookings': [_booking_dict(b) for b in bookings], 'date': today.isoformat()})


@csrf_exempt
@_require_auth
def barber_bookings_upcoming(request):
    """
    GET /api/barber/bookings/upcoming/
    Returns all future pending/confirmed bookings.
    """
    today = timezone.localdate()
    bookings = (
        Booking.objects
        .filter(
            booking_date__gte=today,
            status__in=[Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED]
        )
        .select_related('service', 'barber')
        .order_by('booking_date', 'booking_time')
    )
    return _ok({'bookings': [_booking_dict(b) for b in bookings]})


@csrf_exempt
@_require_auth
def barber_bookings_all(request):
    """
    GET /api/barber/bookings/?status=&search=&page=&page_size=
    Paginated list of all bookings with optional filters.
    """
    qs = Booking.objects.select_related('service', 'barber').order_by('-booking_date', '-booking_time')

    status = request.GET.get('status', '').upper()
    if status in (Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED, Booking.STATUS_COMPLETED, Booking.STATUS_CANCELLED):
        qs = qs.filter(status=status)

    search = request.GET.get('search', '').strip()
    if search:
        qs = qs.filter(
            Q(customer_name__icontains=search) |
            Q(booking_id__icontains=search) |
            Q(customer_phone__icontains=search)
        )

    page = max(1, int(request.GET.get('page', 1)))
    page_size = min(50, int(request.GET.get('page_size', 20)))
    total = qs.count()
    start = (page - 1) * page_size
    bookings = qs[start: start + page_size]

    return _ok({
        'bookings': [_booking_dict(b) for b in bookings],
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size,
    })


@csrf_exempt
@_require_auth
def barber_booking_detail(request, booking_id):
    """
    GET /api/barber/bookings/<booking_id>/
    """
    try:
        booking = Booking.objects.select_related('service', 'barber').get(booking_id=booking_id)
    except Booking.DoesNotExist:
        return _error('Booking not found.', 404)
    return _ok({'booking': _booking_dict(booking)})


# ──────────────────────────────────────────────────────────────
# Booking Actions
# ──────────────────────────────────────────────────────────────

@csrf_exempt
@_require_auth
def barber_confirm_booking(request, booking_id):
    """
    POST /api/barber/bookings/<booking_id>/confirm/
    Confirms a PENDING booking and sends confirmation SMS.
    """
    if request.method != 'POST':
        return _error('Method not allowed.', 405)
    try:
        booking = Booking.objects.select_related('service', 'barber').get(booking_id=booking_id)
    except Booking.DoesNotExist:
        return _error('Booking not found.', 404)

    if booking.status != Booking.STATUS_PENDING:
        return _error(f'Cannot confirm a booking with status: {booking.status}')

    booking.status = Booking.STATUS_CONFIRMED
    booking.save()

    # Send confirmation SMS + schedule reminders
    try:
        from .sms import send_booking_confirmation, schedule_reminders
        send_booking_confirmation(booking)
        schedule_reminders(booking)
    except Exception as e:
        logger.exception(f'SMS error for {booking_id}: {e}')

    return _ok(message='Booking confirmed.', booking=_booking_dict(booking))


@csrf_exempt
@_require_auth
def barber_complete_booking(request, booking_id):
    """
    POST /api/barber/bookings/<booking_id>/complete/
    Marks a confirmed booking as completed.
    """
    if request.method != 'POST':
        return _error('Method not allowed.', 405)
    try:
        booking = Booking.objects.select_related('service', 'barber').get(booking_id=booking_id)
    except Booking.DoesNotExist:
        return _error('Booking not found.', 404)

    if booking.status != Booking.STATUS_CONFIRMED:
        return _error(f'Cannot complete a booking with status: {booking.status}')

    booking.status = Booking.STATUS_COMPLETED
    booking.save()
    return _ok(message='Booking marked as completed.', booking=_booking_dict(booking))


@csrf_exempt
@_require_auth
def barber_cancel_booking(request, booking_id):
    """
    POST /api/barber/bookings/<booking_id>/cancel/
    Cancels a pending or confirmed booking.
    """
    if request.method != 'POST':
        return _error('Method not allowed.', 405)
    try:
        booking = Booking.objects.select_related('service', 'barber').get(booking_id=booking_id)
    except Booking.DoesNotExist:
        return _error('Booking not found.', 404)

    if booking.status in (Booking.STATUS_COMPLETED, Booking.STATUS_CANCELLED):
        return _error(f'Cannot cancel a booking with status: {booking.status}')

    booking.status = Booking.STATUS_CANCELLED
    booking.save()

    # Notify customer of cancellation via SMS
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

    return _ok(message='Booking cancelled.', booking=_booking_dict(booking))


# ──────────────────────────────────────────────────────────────
# FCM Push Token
# ──────────────────────────────────────────────────────────────

@csrf_exempt
@_require_auth
def barber_register_fcm(request):
    """
    POST /api/barber/fcm-token/
    Body: {"token": "fcm_device_token"}
    Stores FCM token for push notifications on new bookings.
    """
    if request.method != 'POST':
        return _error('Method not allowed.', 405)
    try:
        data = json.loads(request.body)
        token = data.get('token', '').strip()
    except Exception:
        return _error('Invalid JSON.')

    if not token:
        return _error('FCM token is required.')

    # Store in user profile (or simple file/cache for now)
    request.barber_user.profile_token = token  # noqa — stored in cache below
    _save_fcm_token(request.barber_user.pk, token)
    return _ok(message='FCM token registered.')


def _save_fcm_token(user_id: int, token: str):
    """Save FCM token to a simple JSON file (no extra dependencies)."""
    import json, os
    from django.conf import settings
    token_file = os.path.join(settings.BASE_DIR, '.fcm_tokens.json')
    try:
        if os.path.exists(token_file):
            with open(token_file) as f:
                tokens = json.load(f)
        else:
            tokens = {}
        tokens[str(user_id)] = token
        with open(token_file, 'w') as f:
            json.dump(tokens, f, indent=2)
    except Exception as e:
        logger.exception(f'Failed to save FCM token: {e}')
