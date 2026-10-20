"""
ASGI config for exambackend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'exambackend.settings')

# Initialize Django ASGI application early to ensure AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

import accounts.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            accounts.routing.websocket_urlpatterns
        )
    ),
})

# Production workers load the CPU models in the background after ASGI is ready.
# This avoids making the first student's camera frame pay model initialization.
# Management commands and local development remain lazy by default.
if os.environ.get('PREWARM_PROCTORING_MODELS') == '1':
    from accounts.gadget_service import warm_gadget_detector
    from accounts.gaze_service import warm_gaze_tracker

    warm_gadget_detector()
    warm_gaze_tracker()
