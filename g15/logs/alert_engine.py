from datetime import timedelta
from django.utils import timezone
from .models import AlertRule, AlertEvent
from .clickhouse_client import get_clickhouse_client
from .notifications import send_notification
from .parsers import get_severity_name


OPERATOR_MAP = {
    'gt': lambda a, b: a > b,
    'gte': lambda a, b: a >= b,
    'lt': lambda a, b: a < b,
    'lte': lambda a, b: a <= b,
    'eq': lambda a, b: a == b,
    'neq': lambda a, b: a != b,
}


def evaluate_rule(rule):
    ch_client = get_clickhouse_client()
    
    where_clauses = [
        f"timestamp >= now() - INTERVAL {rule.window_minutes} MINUTE"
    ]
    
    if rule.query:
        where_clauses.append(f"(message LIKE '%{rule.query}%' OR raw LIKE '%{rule.query}%')")
    if rule.filter_severity is not None:
        where_clauses.append(f"severity = {rule.filter_severity}")
    if rule.filter_source:
        where_clauses.append(f"source = '{rule.filter_source}'")
    if rule.filter_hostname:
        where_clauses.append(f"hostname = '{rule.filter_hostname}'")
    
    where_sql = ' AND '.join(where_clauses)
    
    if rule.aggregation == 'count':
        result = ch_client.execute(f'''
            SELECT count() as cnt
            FROM logs
            WHERE {where_sql}
        ''')
        current_value = result[0][0] if result else 0
    else:
        current_value = 0
    
    operator_func = OPERATOR_MAP.get(rule.operator)
    is_triggered = operator_func(current_value, rule.threshold) if operator_func else False
    
    return {
        'triggered': is_triggered,
        'current_value': current_value,
    }


def build_alert_message(rule, current_value):
    parts = []
    parts.append(f"规则 '{rule.name}' 触发告警")
    parts.append(f"条件: {rule.get_aggregation_display()} {rule.get_operator_display()} {rule.threshold}")
    parts.append(f"当前值: {current_value}")
    parts.append(f"时间窗口: 最近 {rule.window_minutes} 分钟")
    
    filters = []
    if rule.query:
        filters.append(f"关键词='{rule.query}'")
    if rule.filter_severity is not None:
        filters.append(f"级别={get_severity_name(rule.filter_severity)}")
    if rule.filter_source:
        filters.append(f"来源={rule.filter_source}")
    if rule.filter_hostname:
        filters.append(f"主机={rule.filter_hostname}")
    
    if filters:
        parts.append(f"过滤条件: {', '.join(filters)}")
    
    return ' | '.join(parts)


def process_alert_rule(rule_id):
    try:
        rule = AlertRule.objects.get(id=rule_id)
    except AlertRule.DoesNotExist:
        return
    
    if not rule.is_enabled:
        return
    
    if rule.is_silenced():
        return
    
    result = evaluate_rule(rule)
    
    if result['triggered'] and not rule.is_in_cooldown():
        event = AlertEvent.objects.create(
            rule=rule,
            trigger_value=result['current_value'],
            threshold=rule.threshold,
            operator=rule.operator,
            window_minutes=rule.window_minutes,
            message=build_alert_message(rule, result['current_value'])
        )
        
        rule.last_triggered_at = timezone.now()
        rule.last_triggered_value = result['current_value']
        rule.trigger_count += 1
        rule.save()
        
        for channel in rule.channels.filter(is_enabled=True):
            send_notification(channel, rule, event, result['current_value'])
        
        return event
    return None


def check_all_alert_rules():
    rules = AlertRule.objects.filter(is_enabled=True)
    triggered = []
    for rule in rules:
        event = process_alert_rule(rule.id)
        if event:
            triggered.append(event)
    return triggered


def get_top_n(field, limit=10, start_time=None, end_time=None):
    ch_client = get_clickhouse_client()
    
    where_clauses = []
    if start_time:
        where_clauses.append(f"timestamp >= '{start_time}'")
    if end_time:
        where_clauses.append(f"timestamp <= '{end_time}'")
    where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'
    
    if field == 'hostname':
        results = ch_client.execute(f'''
            SELECT hostname, count() as cnt
            FROM logs
            WHERE {where_sql} AND hostname != ''
            GROUP BY hostname
            ORDER BY cnt DESC
            LIMIT {limit}
        ''')
    elif field == 'source':
        results = ch_client.execute(f'''
            SELECT source, count() as cnt
            FROM logs
            WHERE {where_sql} AND source != ''
            GROUP BY source
            ORDER BY cnt DESC
            LIMIT {limit}
        ''')
    elif field == 'severity':
        results = ch_client.execute(f'''
            SELECT severity, count() as cnt
            FROM logs
            WHERE {where_sql}
            GROUP BY severity
            ORDER BY cnt DESC
            LIMIT {limit}
        ''')
    elif field == 'fields_key':
        results = ch_client.execute(f'''
            SELECT arrayJoin(mapKeys(fields)) as key, count() as cnt
            FROM logs
            WHERE {where_sql}
            GROUP BY key
            ORDER BY cnt DESC
            LIMIT {limit}
        ''')
    elif field == 'tag':
        results = ch_client.execute(f'''
            SELECT arrayJoin(tags) as tag, count() as cnt
            FROM logs
            WHERE {where_sql}
            GROUP BY tag
            ORDER BY cnt DESC
            LIMIT {limit}
        ''')
    else:
        return []
    
    return [{'value': r[0], 'count': r[1]} for r in results]
