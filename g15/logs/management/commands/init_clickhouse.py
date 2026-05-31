from django.core.management.base import BaseCommand
from logs.clickhouse_client import get_clickhouse_client


class Command(BaseCommand):
    help = 'Initialize ClickHouse database and tables'

    def handle(self, *args, **options):
        try:
            ch_client = get_clickhouse_client()
            self.stdout.write('Creating database...')
            ch_client.create_database()
            self.stdout.write('Creating tables...')
            ch_client.create_table()
            self.stdout.write(self.style.SUCCESS('ClickHouse initialized successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to initialize ClickHouse: {e}'))
