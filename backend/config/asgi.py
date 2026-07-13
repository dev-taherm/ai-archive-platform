import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")

import django  # noqa: E402

django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from config.asgi_middleware import TokenAuthMiddleware  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402

from apps.agents.routing import (  # noqa: E402
    websocket_urlpatterns as agent_ws_urlpatterns,
)
from apps.dashboard.routing import (  # noqa: E402
    websocket_urlpatterns as dashboard_ws_urlpatterns,
)

# Combine all WebSocket routes
all_ws_urlpatterns = dashboard_ws_urlpatterns + agent_ws_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": TokenAuthMiddleware(URLRouter(all_ws_urlpatterns)),
})
