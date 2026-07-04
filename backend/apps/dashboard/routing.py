from django.urls import re_path

from apps.dashboard import consumers

websocket_urlpatterns = [
    re_path(r"ws/dashboard/$", consumers.DashboardConsumer.as_asgi()),
    re_path(r"ws/processing/$", consumers.ProcessingConsumer.as_asgi()),
]
