from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),

    # AJAX
    path('api/slots/', views.get_time_slots, name='get_time_slots'),

    # Booking flow
    path('book/', views.create_booking, name='create_booking'),
    path('payment/<str:booking_id>/', views.payment_page, name='payment_page'),
    path('payment/<str:booking_id>/process/', views.process_mock_payment, name='process_mock_payment'),
    path('booking/<str:booking_id>/confirm/', views.booking_confirm, name='booking_confirm'),

    # Barber Dashboard
    path('agenda/', views.barber_agenda, name='barber_agenda'),

    # My Bookings
    path('bookings/', views.booking_list, name='booking_list'),
    path('bookings/<str:booking_id>/', views.booking_detail, name='booking_detail'),
    path('bookings/<str:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
]
