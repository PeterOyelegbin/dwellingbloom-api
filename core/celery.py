import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# Load config from Django settings using a CELERY_ namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Automatically discover tasks in all registered apps
app.autodiscover_tasks()
