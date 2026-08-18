# 24K Barbershop — Full-Stack Booking Platform

A production-ready **Django** barbershop booking system with a premium dark-gold aesthetic, a barber staff Android app, and a customer Android app.

---

## Projects

| Project | Location | Status |
|---|---|---|
| 🌐 **Django Web App** | `d:\QC\barbershop\` | ✅ Done |
| 👨‍💼 **Barber Staff App** (Android) | `d:\QC\barber-staff-app\` | ✅ Done |
| 📱 **Customer App** (Android) | `d:\QC\BarberApp\` | ✅ Done |

---

## 🌐 Django Web App

### Quick Start

```bash
cd barbershop

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

pip install -r requirements.txt

copy .env.example .env         # Windows
# cp .env.example .env         # Linux/macOS

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit: http://127.0.0.1:8000  
Admin: http://127.0.0.1:8000/admin

### Seed Data (via Admin)

1. Login to `/admin/`
2. **Business Hours** → Add hours for all 7 days
3. **Services** → Add your barbershop services

### Payment

Currently running in `PAYMENT_MODE=MOCK` — no real charges. To swap in Razorpay:
1. Set `PAYMENT_MODE=RAZORPAY` in `.env`
2. Add `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in `.env`
3. Update `payment/pay.html` with the Razorpay checkout script

### Stack

- Django 4.2 · SQLite (dev) / PostgreSQL (prod)
- Vanilla HTML/CSS/JS · Playfair Display + Inter fonts
- Font Awesome 6 icons
- Django REST Framework + SimpleJWT (for mobile APIs)

---

## 📱 Customer Android App (`BarberApp`)

Kotlin + Jetpack Compose app for customers to browse services and book appointments.

### Features

- **Splash screen** — animated 24K branded launch screen
- **Home** — services (Male/Female) + barbers listing with ratings
  - Shop location & hours chips
  - "Book Now" + "Call Shop" buttons
- **Booking wizard** (5 steps):
  1. Choose Service
  2. Choose Barber (or "Fastest Available")
  3. Choose Date (next 30 days)
  4. Choose Time Slot (real-time availability)
  5. Enter Details → Confirmed!
  - Back button navigates between steps (not exit)
- **My Bookings** — search by phone number
  - Phone saved automatically — pre-filled on next visit
  - Tap any booking → full detail screen
- **Booking Detail** — booking ID (copyable), service/barber/date/time, cancel button
- **Offline mode** — works without a server using bundled catalog + on-device storage

### API Endpoints (Django)

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/customer/home/` | Services, barbers, available dates |
| `GET` | `/api/customer/slots/?date=&service_id=&barber_id=` | Available time slots |
| `POST` | `/api/customer/bookings/` | Create booking (pay at shop) |
| `GET` | `/api/customer/bookings/list/?phone=` | My bookings by phone |
| `POST` | `/api/customer/bookings/<id>/cancel/` | Cancel a booking |

### Switch to Live Server

In `d:\QC\BarberApp\app\src\main\java\com\thepranit\barberapp\data\`:

```kotlin
// Repository.kt
const val USE_REMOTE = true   // switch from offline to live API

// Api.kt — set your server IP / domain
const val BASE_URL = "http://192.168.x.x:8000/api/customer/"
```

---

## 👨‍💼 Barber Staff App (`barber-staff-app`)

Kotlin + Jetpack Compose app for staff to manage bookings (login required).

### Features

- JWT login / logout
- Dashboard with today's stats
- Today's schedule + upcoming bookings
- Confirm / Complete / Cancel bookings
- FCM push notification token registration

### API Endpoints (Django)

| Method | URL | Description |
|---|---|---|
| `POST` | `/api/barber/login/` | JWT login |
| `GET` | `/api/barber/stats/` | Dashboard stats |
| `GET` | `/api/barber/bookings/today/` | Today's bookings |
| `GET` | `/api/barber/bookings/upcoming/` | Upcoming bookings |
| `POST` | `/api/barber/bookings/<id>/confirm/` | Confirm booking |
| `POST` | `/api/barber/bookings/<id>/complete/` | Mark completed |
| `POST` | `/api/barber/bookings/<id>/cancel/` | Cancel booking |

---

## SMS Notifications

Booking confirmation + reminders via Twilio/Fast2SMS.  
Configure in `.env`:

```
SMS_PROVIDER=fast2sms   # or twilio
FAST2SMS_API_KEY=your_key
```
