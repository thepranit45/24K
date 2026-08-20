"""Small PWA endpoints served at the site root.

Keeping the service worker at ``/service-worker.js`` lets it control every
page in the booking site while deliberately avoiding cached booking data.
"""

from django.http import HttpResponse, JsonResponse
from django.views.decorators.cache import never_cache


@never_cache
def manifest(request):
    """Return the install metadata used by Safari and other mobile browsers."""
    return JsonResponse(
        {
            "name": "24K Barbershop",
            "short_name": "24K Salon",
            "description": "Book a premium grooming appointment with 24K Barbershop.",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "background_color": "#FFFBF0",
            "theme_color": "#D4AF37",
            "icons": [
                {"src": "/static/images/pwa/icon-192.png", "sizes": "192x192", "type": "image/png"},
                {"src": "/static/images/pwa/icon-512.png", "sizes": "512x512", "type": "image/png"},
            ],
        },
        content_type="application/manifest+json",
    )


@never_cache
def service_worker(request):
    """Serve a conservative worker: assets are cached, booking pages stay live."""
    script = """
const CACHE_NAME = '24k-static-v1';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;

  // Never cache pages or API responses: availability and bookings must be current.
  if (!url.pathname.startsWith('/static/')) return;

  event.respondWith(
    caches.open(CACHE_NAME).then(async cache => {
      const cached = await cache.match(request);
      if (cached) return cached;
      const response = await fetch(request);
      if (response.ok) cache.put(request, response.clone());
      return response;
    })
  );
});
""".strip()
    response = HttpResponse(script, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response
