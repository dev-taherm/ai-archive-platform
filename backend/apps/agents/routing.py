from django.urls import re_path

from apps.agents import consumers

websocket_urlpatterns = [
    re_path(r"ws/agent/$", consumers.AgentConsumer.as_asgi()),
]
