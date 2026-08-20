"""URL routes for the Customer REST API (/api/customer/...) — used by the Android Booking App."""

from django.urls import path
from . import customer_views

urlpatterns = [
    # Catalog + Slots
    path('home/',                customer_views.customer_home,     name='api_customer_home'),
    path('slots/',               customer_views.customer_slots,    name='api_customer_slots'),
    path('meta/',                customer_views.customer_meta,     name='api_customer_meta'),

    # Bookings
    path('bookings/',            customer_views.customer_create_booking, name='api_customer_create_booking'),
    path('bookings/list/',       customer_views.customer_my_bookings,   name='api_customer_my_bookings'),
    path('bookings/<str:booking_id>/cancel/', customer_views.customer_cancel_booking, name='api_customer_cancel_booking'),
]