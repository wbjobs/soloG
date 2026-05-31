from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .clickhouse_client import get_clickhouse_client


@receiver(post_migrate)
def init_clickhouse(sender, **kwargs):
    try:
        ch_client = get_clickhouse_client()
        ch_client.create_database()
        ch_client.create_table()
        print("ClickHouse database and table initialized successfully")
    except Exception as e:
        print(f"Warning: Could not initialize ClickHouse: {e}")
