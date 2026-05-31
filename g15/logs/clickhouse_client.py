from clickhouse_driver import Client
from django.conf import settings


class ClickHouseClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.client = Client(
                host=settings.CLICKHOUSE_CONFIG['host'],
                port=settings.CLICKHOUSE_CONFIG['port'],
                user=settings.CLICKHOUSE_CONFIG['user'],
                password=settings.CLICKHOUSE_CONFIG['password'],
                database=settings.CLICKHOUSE_CONFIG['database'],
            )
        return cls._instance

    def execute(self, query, params=None):
        return self.client.execute(query, params or {})

    def create_database(self):
        db = settings.CLICKHOUSE_CONFIG['database']
        self.client.execute(f'CREATE DATABASE IF NOT EXISTS {db}')

    def create_table(self):
        self.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                timestamp DateTime64(3, 'Asia/Shanghai'),
                hostname String,
                source String,
                severity UInt8,
                facility UInt8,
                message String,
                tags Array(String),
                fields Map(String, String),
                raw String
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMM(timestamp)
            ORDER BY (timestamp, source, severity)
            SETTINGS index_granularity = 8192
        ''')

    def insert_log(self, log_data):
        self.execute('''
            INSERT INTO logs (timestamp, hostname, source, severity, facility, message, tags, fields, raw)
            VALUES
        ''', [log_data])

    def insert_logs_batch(self, logs_batch):
        self.execute('''
            INSERT INTO logs (timestamp, hostname, source, severity, facility, message, tags, fields, raw)
            VALUES
        ''', logs_batch)

    def search(self, query, limit=100, last_timestamp=None, last_source=None, last_severity=None, direction='backward'):
        where_clauses = [f"(message LIKE '%{query}%' OR raw LIKE '%{query}%')"]
        
        if last_timestamp is not None:
            if direction == 'backward':
                where_clauses.append(f"timestamp < '{last_timestamp}'")
            elif direction == 'forward':
                where_clauses.append(f"timestamp > '{last_timestamp}'")
        
        where_sql = ' AND '.join(where_clauses)
        order_direction = 'DESC' if direction == 'backward' else 'ASC'
        
        results = self.execute(f'''
            SELECT timestamp, hostname, source, severity, facility, message, tags, fields, raw
            FROM logs
            WHERE {where_sql}
            ORDER BY timestamp {order_direction}, source {order_direction}, severity {order_direction}
            LIMIT {limit}
        ''')
        
        if direction == 'forward':
            results = list(reversed(results))
        
        return results

    def filter_logs(self, filters, limit=100, last_timestamp=None, last_source=None, last_severity=None, direction='backward'):
        where_clauses = []
        for key, value in filters.items():
            if key == 'message':
                where_clauses.append(f"message LIKE '%{value}%'")
            elif key == 'source':
                where_clauses.append(f"source = '{value}'")
            elif key == 'hostname':
                where_clauses.append(f"hostname = '{value}'")
            elif key == 'severity':
                where_clauses.append(f"severity = {int(value)}")
            elif key == 'start_time':
                where_clauses.append(f"timestamp >= '{value}'")
            elif key == 'end_time':
                where_clauses.append(f"timestamp <= '{value}'")
        
        if last_timestamp is not None:
            if direction == 'backward':
                where_clauses.append(f"timestamp < '{last_timestamp}'")
            elif direction == 'forward':
                where_clauses.append(f"timestamp > '{last_timestamp}'")
        
        where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'
        order_direction = 'DESC' if direction == 'backward' else 'ASC'
        
        results = self.execute(f'''
            SELECT timestamp, hostname, source, severity, facility, message, tags, fields, raw
            FROM logs
            WHERE {where_sql}
            ORDER BY timestamp {order_direction}, source {order_direction}, severity {order_direction}
            LIMIT {limit}
        ''')
        
        if direction == 'forward':
            results = list(reversed(results))
        
        return results

    def aggregate(self, field, start_time=None, end_time=None, limit=20):
        where_clauses = []
        if start_time:
            where_clauses.append(f"timestamp >= '{start_time}'")
        if end_time:
            where_clauses.append(f"timestamp <= '{end_time}'")
        where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'
        if field == 'severity':
            return self.execute(f'''
                SELECT severity, count() as count
                FROM logs
                WHERE {where_sql}
                GROUP BY severity
                ORDER BY count DESC
                LIMIT {limit}
            ''')
        elif field == 'source':
            return self.execute(f'''
                SELECT source, count() as count
                FROM logs
                WHERE {where_sql}
                GROUP BY source
                ORDER BY count DESC
                LIMIT {limit}
            ''')
        elif field == 'hostname':
            return self.execute(f'''
                SELECT hostname, count() as count
                FROM logs
                WHERE {where_sql}
                GROUP BY hostname
                ORDER BY count DESC
                LIMIT {limit}
            ''')
        elif field == 'time':
            return self.execute(f'''
                SELECT toStartOfMinute(timestamp) as time, count() as count
                FROM logs
                WHERE {where_sql}
                GROUP BY time
                ORDER BY time DESC
                LIMIT {limit}
            ''')
        return []

    def count_total(self):
        result = self.execute('SELECT count() FROM logs')
        return result[0][0] if result else 0

    def count_by_severity(self):
        return self.execute('''
            SELECT severity, count() as count
            FROM logs
            GROUP BY severity
            ORDER BY severity
        ''')

    def count_last_hour(self):
        result = self.execute('''
            SELECT count()
            FROM logs
            WHERE timestamp >= now() - INTERVAL 1 HOUR
        ''')
        return result[0][0] if result else 0


def get_clickhouse_client():
    return ClickHouseClient()
