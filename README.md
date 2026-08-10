# The Gentleman's Cut — Premium Barbershop Booking

A production-ready Django barbershop booking application with a premium dark-gold aesthetic.

## Quick Start

```bash
# 1. Navigate to project
cd barbershop

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and configure environment
copy .env.example .env         # Windows
# cp .env.example .env         # Linux/macOS
# Edit .env if needed (defaults use SQLite)

# 5. Run migrations
python manage.py migrate

# 6. Create admin user
python manage.py createsuperuser

# 7. Run the dev server
python manage.py runserver
```

Visit: http://127.0.0.1:8000

Admin: http://127.0.0.1:8000/admin

## Seed Data (via Admin)

1. Login to `/admin/`
2. **Business Hours** → Add hours for all 7 days
3. **Services** → Add your barbershop services

## Payment

Currently running in `PAYMENT_MODE=MOCK` — no real charges. To swap in Razorpay:
1. Set `PAYMENT_MODE=RAZORPAY` in `.env`
2. Add `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in `.env`
3. Update `payment/pay.html` with the Razorpay checkout script

## Stack

- Django 4.2 · SQLite (dev) / PostgreSQL (prod)
- Vanilla HTML/CSS/JS · Playfair Display + Inter fonts
- Font Awesome 6 icons
# 24K
