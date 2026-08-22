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
    path('payment/<str:booking_id>/razorpay-verify/', views.verify_razorpay_payment, name='verify_razorpay_payment'),
    path('booking/<str:booking_id>/confirm/', views.booking_confirm, name='booking_confirm'),

    # Barber Agenda (Public Timeline)
    path('agenda/', views.barber_agenda, name='barber_agenda'),

    # Barber management dashboard. Keep the legacy URL working for saved links.
    path('barber/dashboard/', views.barber_dashboard, name='barber_dashboard'),
    path('dashboard/', views.barber_dashboard, name='admin_dashboard'),
    path('dashboard/appointments/', views.admin_appointments, name='admin_appointments'),
    path('dashboard/barbers/', views.admin_barbers, name='admin_barbers'),
    path('dashboard/barbers/add/', views.admin_add_barber, name='admin_add_barber'),
    path('dashboard/barbers/<int:barber_id>/delete/', views.admin_delete_barber, name='admin_delete_barber'),
    path('dashboard/services/', views.admin_services, name='admin_services'),
    path('dashboard/hours/', views.admin_hours, name='admin_hours'),
    path('dashboard/settings/', views.admin_settings, name='admin_settings'),
    path('dashboard/status/<str:booking_id>/', views.admin_update_status, name='admin_update_status'),
    path('barber/dashboard/status/<str:booking_id>/', views.barber_update_status, name='barber_update_status'),
    path('dashboard/toggle-barber/<int:barber_id>/', views.admin_toggle_barber, name='admin_toggle_barber'),
    path('dashboard/notify/<str:booking_id>/', views.admin_send_notification, name='admin_send_notification'),

    # My Bookings
    path('bookings/', views.booking_list, name='booking_list'),
    path('bookings/<str:booking_id>/', views.booking_detail, name='booking_detail'),
    path('bookings/<str:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
]
