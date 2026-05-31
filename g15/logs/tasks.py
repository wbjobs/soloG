from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .clickhouse_client import get_clickhouse_client
from .parsers import parse_log, get_severity_name
from .alert_engine import process_alert_rule, check_all_alert_rules


@shared_task
def process_log(log_line, source_type=None):
    try:
        parsed = parse_log(log_line, source_type)
        if not parsed:
            return None

        ch_client = get_clickhouse_client()
        ch_client.insert_log(parsed)

        broadcast_log.delay(parsed)
        return parsed
    except Exception as e:
        print(f"Error processing log: {e}")
        return None


@shared_task
def process_logs_batch(logs, source_type=None):
    try:
        parsed_logs = []
        for log_line in logs:
            parsed = parse_log(log_line, source_type)
            if parsed:
                parsed_logs.append(parsed)

        if parsed_logs:
            ch_client = get_clickhouse_client()
            ch_client.insert_logs_batch(parsed_logs)

            for log in parsed_logs:
                broadcast_log.delay(log)

        return len(parsed_logs)
    except Exception as e:
        print(f"Error processing logs batch: {e}")
        return 0


@shared_task
def broadcast_log(log_data):
    try:
        channel_layer = get_channel_layer()
        log_dict = {
            'timestamp': log_data['timestamp'].isoformat() if hasattr(log_data['timestamp'], 'isoformat') else str(log_data['timestamp']),
            'hostname': log_data.get('hostname', ''),
            'source': log_data.get('source', ''),
            'severity': log_data.get('severity', 6),
            'severity_name': get_severity_name(log_data.get('severity', 6)),
            'facility': log_data.get('facility', 1),
            'message': log_data.get('message', ''),
            'tags': log_data.get('tags', []),
            'fields': log_data.get('fields', {}),
            'raw': log_data.get('raw', ''),
        }
        async_to_sync(channel_layer.group_send)(
            'logs_group',
            {
                'type': 'log_message',
                'log': log_dict,
            }
        )
    except Exception as e:
        print(f"Error broadcasting log: {e}")


@shared_task
def run_alert_rule(rule_id):
    from .alert_engine import process_alert_rule
    return process_alert_rule(rule_id)


@shared_task
def run_all_alert_rules():
    from .alert_engine import check_all_alert_rules
    events = check_all_alert_rules()
    return f"Triggered {len(events)} alerts"
