"""
SMS Service for 24K Barbershop
Sends SMS automatically from the app's own SIM — using a free Android SMS
Gateway app on the barber's Android phone. No third-party/paid service:
the phone's own SIM sends the SMS, the Django app triggers it over WiFi.

Setup:
1. Install "SMS Gateway" app on the Android phone from Play Store
   https://play.google.com/store/apps/details?id=au.com.penguinlabs.smsgateway
2. Open the app, start the server, note the IP + port (e.g. http://192.168.1.5:8080)
3. Set SMS_GATEWAY_URL (and optional SMS_GATEWAY_TOKEN) in .env
4. Keep the phone on the same network as the PC running the app
"""

import logging
import threading
from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    """Normalize phone number to international format for India."""
    digits = ''.join(filter(str.isdigit, phone))
    if digits.startswith('91') and len(digits) == 12:
        return f'+{digits}'
    if len(digits) == 10:
        return f'+91{digits}'
    if digits.startswith('0') and len(digits) == 11:
        return f'+91{digits[1:]}'
    return f'+{digits}'


def _send_sms(phone: str, message: str) -> bool:
    """
    Send SMS via the Android SMS Gateway app (own SIM).
    Returns True on success, False on failure.
    """
    gateway_url = getattr(settings, 'SMS_GATEWAY_URL', 'mock')
    gateway_token = getattr(settings, 'SMS_GATEWAY_TOKEN', '')

    normalized = _normalize_phone(phone)

    # ── Mock mode ─────────────────────────────────────────────────────────
    if not gateway_url or gateway_url == 'mock':
        logger.info(f'[MOCK SMS] To: {normalized} | Message: {message}')
        print(f'\n[MOCK SMS → {normalized}]\n{message}\n')
        return True

    # ── Real Android SMS Gateway (own SIM) ─────────────────────────────────
    try:
        headers = {'Content-Type': 'application/json'}
        if gateway_token:
            headers['Authorization'] = f'Bearer {gateway_token}'

        payload = {
            'phone_number': normalized,
            'message': message,
        }

        resp = requests.post(
            f'{gateway_url.rstrip("/")}/send',
            json=payload,
            headers=headers,
            timeout=10,
        )

        if resp.status_code in (200, 201):
            logger.info(f'SMS sent to {normalized}')
            return True
        else:
            logger.error(f'SMS Gateway error {resp.status_code}: {resp.text}')
            return False

    except requests.exceptions.ConnectionError:
        logger.error(
            f'Cannot reach SMS Gateway at {gateway_url}. '
            'Make sure the Android phone is on the same network and the app is running.'
        )
        return False
    except Exception as exc:
        logger.exception(f'SMS send failed: {exc}')
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Public API — called from booking views
# ──────────────────────────────────────────────────────────────────────────────

def send_booking_confirmation(booking) -> None:
    """Send booking confirmation SMS immediately after payment."""
    dt = datetime.combine(booking.booking_date, booking.booking_time)
    time_str = dt.strftime('%I:%M %p')
    date_str = booking.booking_date.strftime('%d %b %Y')
    barber_str = f' with {booking.barber.name}' if booking.barber else ''

    message = (
        f'✅ Booking Confirmed!\n'
        f'ID: {booking.booking_id}\n'
        f'Service: {booking.service.name}{barber_str}\n'
        f'Date: {date_str} at {time_str}\n'
        f'Amount: ₹{int(booking.amount)}\n'
        f'Thank you! — 24K Barbershop'
    )
    _send_sms(booking.customer_phone, message)


def send_one_hour_reminder(booking) -> None:
    """Send 1-hour reminder SMS."""
    dt = datetime.combine(booking.booking_date, booking.booking_time)
    time_str = dt.strftime('%I:%M %p')

    message = (
        f'⏰ Reminder — 24K Barbershop\n'
        f'Your {booking.service.name} appointment is in 1 HOUR!\n'
        f'Time: {time_str}\n'
        f'Booking: {booking.booking_id}\n'
        f'See you soon! 💈'
    )
    _send_sms(booking.customer_phone, message)


def send_fifteen_min_reminder(booking) -> None:
    """Send 15-minute reminder SMS."""
    dt = datetime.combine(booking.booking_date, booking.booking_time)
    time_str = dt.strftime('%I:%M %p')

    message = (
        f'🚀 You\'re Up Next! — 24K Barbershop\n'
        f'Your appointment starts in 15 MINUTES at {time_str}.\n'
        f'Please head over now. See you! 💈'
    )
    _send_sms(booking.customer_phone, message)


# ──────────────────────────────────────────────────────────────────────────────
# Reminder Scheduler — runs in background thread after booking confirmed
# ──────────────────────────────────────────────────────────────────────────────

def schedule_reminders(booking) -> None:
    """
    Schedule 1-hour and 15-minute reminders in background threads.
    Called once after booking is confirmed.
    """
    now = timezone.now()
    booking_dt = timezone.make_aware(
        datetime.combine(booking.booking_date, booking.booking_time)
    )

    one_hour_before = booking_dt - timedelta(hours=1)
    fifteen_min_before = booking_dt - timedelta(minutes=15)

    def _remind_1h():
        delay = (one_hour_before - now).total_seconds()
        if delay > 0:
            import time
            time.sleep(delay)
            # Refresh booking from DB before sending
            try:
                from .models import Booking
                b = Booking.objects.get(pk=booking.pk)
                if b.status == Booking.STATUS_CONFIRMED:
                    send_one_hour_reminder(b)
            except Exception as e:
                logger.exception(f'1h reminder failed: {e}')
        else:
            logger.info(f'Skipping 1h reminder for {booking.booking_id} — time passed')

    def _remind_15m():
        delay = (fifteen_min_before - now).total_seconds()
        if delay > 0:
            import time
            time.sleep(delay)
            try:
                from .models import Booking
                b = Booking.objects.get(pk=booking.pk)
                if b.status == Booking.STATUS_CONFIRMED:
                    send_fifteen_min_reminder(b)
            except Exception as e:
                logger.exception(f'15m reminder failed: {e}')
        else:
            logger.info(f'Skipping 15m reminder for {booking.booking_id} — time passed')

    t1 = threading.Thread(target=_remind_1h, daemon=True, name=f'reminder-1h-{booking.booking_id}')
    t2 = threading.Thread(target=_remind_15m, daemon=True, name=f'reminder-15m-{booking.booking_id}')
    t1.start()
    t2.start()
    logger.info(f'Reminders scheduled for booking {booking.booking_id}')
