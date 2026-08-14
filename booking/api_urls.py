"""URL routes for the Barber REST API (/api/barber/...)"""

from django.urls import path
from . import api_views

urlpatterns = [
    # Auth
    path('login/',          api_views.barber_login,         name='api_barber_login'),
    path('logout/',         api_views.barber_logout,        name='api_barber_logout'),

    # Dashboard
    path('stats/',          api_views.barber_stats,         name='api_barber_stats'),

    # Booking Lists
    path('bookings/today/', api_views.barber_bookings_today,    name='api_barber_bookings_today'),
    path('bookings/upcoming/', api_views.barber_bookings_upcoming, name='api_barber_bookings_upcoming'),
    path('bookings/',       api_views.barber_bookings_all,   name='api_barber_bookings_all'),

    # Booking Detail + Actions
    path('bookings/<str:booking_id>/',          api_views.barber_booking_detail,  name='api_barber_booking_detail'),
    path('bookings/<str:booking_id>/confirm/',  api_views.barber_confirm_booking, name='api_barber_confirm'),
    path('bookings/<str:booking_id>/complete/', api_views.barber_complete_booking,name='api_barber_complete'),
    path('bookings/<str:booking_id>/cancel/',   api_views.barber_cancel_booking,  name='api_barber_cancel'),

    # Push Notifications
    path('fcm-token/',      api_views.barber_register_fcm,  name='api_barber_fcm_token'),
]
