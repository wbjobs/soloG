#!/usr/bin/env python
import requests
import json
import time
import random
from datetime import datetime

BASE_URL = 'http://localhost:8000'

LOG_SOURCES = ['nginx', 'app', 'database', 'auth', 'api']
SEVERITIES = ['debug', 'info', 'notice', 'warning', 'error', 'critical']
HOSTNAMES = ['web-01', 'app-01', 'db-01', 'cache-01']
MESSAGES = [
    'User login successful',
    'User login failed',
    'Database query executed',
    'Cache invalidated',
    'API request completed',
    'Rate limit exceeded',
    'Configuration reloaded',
    'Memory usage high',
    'Disk space warning',
    'Background job failed',
]


def send_http_json_log():
    log = {
        'timestamp': datetime.now().isoformat(),
        'hostname': random.choice(HOSTNAMES),
        'source': random.choice(LOG_SOURCES),
        'level': random.choice(SEVERITIES),
        'message': random.choice(MESSAGES),
        'request_id': f'req-{random.randint(10000, 99999)}',
        'duration': random.randint(10, 500),
    }
    try:
        response = requests.post(f'{BASE_URL}/api/v1/logs/http', json=log)
        print(f'HTTP JSON: {response.status_code}')
    except Exception as e:
        print(f'HTTP JSON Error: {e}')


def send_http_text_log():
    log_line = f'{datetime.now().isoformat()} [{random.choice(SEVERITIES).upper()}] {random.choice(LOG_SOURCES)}: {random.choice(MESSAGES)}'
    try:
        response = requests.post(f'{BASE_URL}/api/v1/logs/http', data=log_line, headers={'Content-Type': 'text/plain'})
        print(f'HTTP Text: {response.status_code}')
    except Exception as e:
        print(f'HTTP Text Error: {e}')


def send_syslog_log():
    priority = random.randint(0, 191)
    timestamp = datetime.now().isoformat()
    hostname = random.choice(HOSTNAMES)
    source = random.choice(LOG_SOURCES)
    message = random.choice(MESSAGES)
    log_line = f'<{priority}>1 {timestamp} {hostname} {source} - - - {message}'
    try:
        response = requests.post(f'{BASE_URL}/api/v1/logs/syslog', data=log_line)
        print(f'Syslog HTTP: {response.status_code}')
    except Exception as e:
        print(f'Syslog HTTP Error: {e}')


def send_batch_logs():
    logs = []
    for _ in range(10):
        logs.append({
            'timestamp': datetime.now().isoformat(),
            'hostname': random.choice(HOSTNAMES),
            'source': random.choice(LOG_SOURCES),
            'level': random.choice(SEVERITIES),
            'message': random.choice(MESSAGES),
        })
    try:
        response = requests.post(f'{BASE_URL}/api/v1/logs/http', json=logs)
        print(f'Batch: {response.status_code}, count={response.json().get("count", 0)}')
    except Exception as e:
        print(f'Batch Error: {e}')


def main():
    print('Starting log sender... Press Ctrl+C to stop')
    try:
        while True:
            choice = random.randint(0, 3)
            if choice == 0:
                send_http_json_log()
            elif choice == 1:
                send_http_text_log()
            elif choice == 2:
                send_syslog_log()
            else:
                send_batch_logs()
            time.sleep(random.uniform(0.5, 2))
    except KeyboardInterrupt:
        print('\nStopped')


if __name__ == '__main__':
    main()
