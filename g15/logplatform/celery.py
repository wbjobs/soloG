import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'logplatform.settings')

app = Celery('logplatform')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'check-alert-rules-every-minute': {
        'task': 'logs.tasks.run_all_alert_rules',
        'schedule': 60.0,
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
