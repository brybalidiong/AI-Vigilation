import threading
from django.apps import AppConfig

class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        # Warmup threads for AI models have been disabled to prevent 
        # C++ thread deadlocks with MediaPipe and TensorFlow on Windows.
        pass
