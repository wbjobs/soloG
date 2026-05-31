import socket
import threading
from django.core.management.base import BaseCommand
from django.conf import settings
from logs.tasks import process_log


class SyslogServer:
    def __init__(self, host='0.0.0.0', port=None):
        self.host = host
        self.port = port or settings.SYSLOG_PORT
        self.running = False

    def handle_udp(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        print(f'Syslog UDP server listening on {self.host}:{self.port}')

        while self.running:
            try:
                data, addr = sock.recvfrom(8192)
                log_line = data.decode('utf-8', errors='ignore')
                if log_line.strip():
                    process_log.delay(log_line, 'syslog')
            except Exception as e:
                print(f'UDP error: {e}')

    def handle_tcp(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.listen(5)
        print(f'Syslog TCP server listening on {self.host}:{self.port}')

        while self.running:
            try:
                conn, addr = sock.accept()
                data = conn.recv(8192)
                conn.close()
                log_line = data.decode('utf-8', errors='ignore')
                if log_line.strip():
                    for line in log_line.strip().split('\n'):
                        if line.strip():
                            process_log.delay(line.strip(), 'syslog')
            except Exception as e:
                print(f'TCP error: {e}')

    def start(self):
        self.running = True
        udp_thread = threading.Thread(target=self.handle_udp, daemon=True)
        tcp_thread = threading.Thread(target=self.handle_tcp, daemon=True)
        udp_thread.start()
        tcp_thread.start()

        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            print('Syslog server stopped')


class Command(BaseCommand):
    help = 'Start Syslog server (UDP + TCP)'

    def add_arguments(self, parser):
        parser.add_argument('--port', type=int, help='Syslog server port')

    def handle(self, *args, **options):
        server = SyslogServer(port=options.get('port'))
        server.start()
