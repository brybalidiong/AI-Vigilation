from django.urls import re_path
from accounts import consumers

websocket_urlpatterns = [
    re_path(r'ws/student/exams/(?P<exam_id>\d+)/proctoring/gaze/$', consumers.GazeConsumer.as_asgi()),
]
