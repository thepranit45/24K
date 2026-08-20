from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from booking.pwa_views import manifest, service_worker

urlpatterns = [
    path('manifest.webmanifest', manifest, name='pwa_manifest'),
    path('service-worker.js', service_worker, name='pwa_service_worker'),
    path('admin/', admin.site.urls),
    path('auth/', include('users.urls')),
    path('', include('booking.urls')),
    path('api/barber/', include('booking.api_urls')),
    path('api/customer/', include('booking.customer_urls')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]
