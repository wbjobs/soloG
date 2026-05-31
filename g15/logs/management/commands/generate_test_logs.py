import random
import time
import json
from datetime import datetime
from django.core.management.base import BaseCommand
from logs.tasks import process_log


LOG_SOURCES = ['nginx', 'app', 'database', 'auth', 'api', 'cache', 'queue']
SEVERITIES = ['debug', 'info', 'notice', 'warning', 'error', 'critical']
HOSTNAMES = ['web-01', 'web-02', 'app-01', 'app-02', 'db-01', 'cache-01', 'api-01']
MESSAGES = [
    'User login successful',
    'User login failed',
    'Database connection established',
    'Database connection timeout',
    'Cache hit for key: user:123',
    'Cache miss for key: user:456',
    'Request processed in 245ms',
    'Rate limit exceeded for IP 192.168.1.100',
    'Configuration reloaded',
    'Service started',
    'Service stopped',
    'Memory usage at 85%',
    'Disk space low on /var/log',
    'API request to /api/users returned 200',
    'API request to /api/data returned 500',
    'Background job completed',
    'Background job failed',
    'New user registered',
    'Password reset requested',
    'File upload completed',
]


class Command(BaseCommand):
    help = 'Generate test log entries'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=100, help='Number of logs to generate')
        parser.add_argument('--interval', type=float, default=0.1, help='Interval between logs in seconds')
        parser.add_argument('--format', type=str, default='json', choices=['json', 'syslog', 'nginx', 'raw'], help='Log format')

    def handle(self, *args, **options):
        count = options['count']
        interval = options['interval']
        fmt = options['format']

        self.stdout.write(f'Generating {count} test logs in {fmt} format...')

        for i in range(count):
            source = random.choice(LOG_SOURCES)
            severity = random.choice(SEVERITIES)
            hostname = random.choice(HOSTNAMES)
            message = random.choice(MESSAGES)
            timestamp = datetime.now().isoformat()

            if fmt == 'json':
                log_line = json.dumps({
                    'timestamp': timestamp,
                    'hostname': hostname,
                    'source': source,
                    'level': severity,
                    'message': message,
                    'request_id': f'req-{random.randint(10000, 99999)}',
                    'duration_ms': random.randint(10, 500),
                })
            elif fmt == 'syslog':
                priority = random.randint(0, 191)
                log_line = f'<{priority}>1 {timestamp} {hostname} {source} - - - {message}'
            elif fmt == 'nginx':
                status_codes = [200, 200, 200, 201, 301, 302, 400, 401, 403, 404, 500, 502, 503]
                methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
                paths = ['/', '/api/users', '/api/data', '/login', '/dashboard', '/static/style.css']
                ip = f'{random.randint(10, 250)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}'
                status = random.choice(status_codes)
                method = random.choice(methods)
                path = random.choice(paths)
                bytes_sent = random.randint(100, 100000)
                log_line = f'{ip} - - [{datetime.now().strftime("%d/%b/%Y:%H:%M:%S +0000")}] "{method} {path} HTTP/1.1" {status} {bytes_sent} "-" "Mozilla/5.0"'
            else:
                log_line = f'{timestamp} [{severity.upper()}] {source}: {message}'

            process_log.delay(log_line, fmt if fmt != 'raw' else None)

            if interval > 0:
                time.sleep(interval)

            if (i + 1) % 10 == 0:
                self.stdout.write(f'Generated {i + 1}/{count} logs')

        self.stdout.write(self.style.SUCCESS(f'Successfully generated {count} test logs'))
