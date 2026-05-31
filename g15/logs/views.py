import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import render
from django.db import transaction
from django.utils import timezone
from .tasks import process_log, process_logs_batch, run_alert_rule, run_all_alert_rules
from .clickhouse_client import get_clickhouse_client
from .parsers import get_severity_name
from .models import AlertChannel, AlertRule, AlertEvent
from .alert_engine import get_top_n


@csrf_exempt
@require_POST
def receive_http_log(request):
    try:
        content_type = request.content_type
        source_type = request.GET.get('source', None)

        if content_type == 'application/json':
            try:
                data = json.loads(request.body)
                if isinstance(data, list):
                    log_lines = [json.dumps(item) if isinstance(item, dict) else str(item) for item in data]
                    count = process_logs_batch.delay(log_lines, source_type)
                    return JsonResponse({'status': 'success', 'count': len(log_lines)}, status=202)
                elif isinstance(data, dict):
                    log_line = json.dumps(data)
                    process_log.delay(log_line, source_type)
                    return JsonResponse({'status': 'success'}, status=202)
            except json.JSONDecodeError:
                pass

        log_line = request.body.decode('utf-8', errors='ignore')
        if log_line.strip():
            lines = log_line.strip().split('\n')
            if len(lines) > 1:
                process_logs_batch.delay(lines, source_type)
                return JsonResponse({'status': 'success', 'count': len(lines)}, status=202)
            else:
                process_log.delay(log_line, source_type)
                return JsonResponse({'status': 'success'}, status=202)

        return JsonResponse({'status': 'error', 'message': 'Empty log'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_POST
def receive_syslog(request):
    try:
        log_line = request.body.decode('utf-8', errors='ignore')
        if log_line.strip():
            process_log.delay(log_line, 'syslog')
            return JsonResponse({'status': 'success'}, status=202)
        return JsonResponse({'status': 'error', 'message': 'Empty log'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_GET
def search_logs(request):
    try:
        query = request.GET.get('q', '')
        limit = min(int(request.GET.get('limit', 100)), 500)
        last_timestamp = request.GET.get('last_timestamp')
        last_source = request.GET.get('last_source')
        last_severity = request.GET.get('last_severity')
        direction = request.GET.get('direction', 'backward')

        if last_severity:
            last_severity = int(last_severity)

        ch_client = get_clickhouse_client()
        if query:
            results = ch_client.search(
                query, 
                limit=limit,
                last_timestamp=last_timestamp,
                last_source=last_source,
                last_severity=last_severity,
                direction=direction
            )
        else:
            filters = {}
            for key in ['source', 'hostname', 'severity', 'start_time', 'end_time', 'message']:
                value = request.GET.get(key)
                if value:
                    filters[key] = value
            results = ch_client.filter_logs(
                filters, 
                limit=limit,
                last_timestamp=last_timestamp,
                last_source=last_source,
                last_severity=last_severity,
                direction=direction
            )

        logs = []
        for row in results:
            logs.append({
                'timestamp': row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                'hostname': row[1],
                'source': row[2],
                'severity': row[3],
                'severity_name': get_severity_name(row[3]),
                'facility': row[4],
                'message': row[5],
                'tags': row[6],
                'fields': row[7],
                'raw': row[8],
            })

        cursor = None
        if logs:
            last_log = logs[-1]
            cursor = {
                'last_timestamp': last_log['timestamp'],
                'last_source': last_log['source'],
                'last_severity': last_log['severity'],
            }

        return JsonResponse({
            'status': 'success', 
            'logs': logs, 
            'count': len(logs),
            'cursor': cursor,
            'has_more': len(logs) == limit
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_GET
def aggregate_logs(request):
    try:
        field = request.GET.get('field', 'severity')
        start_time = request.GET.get('start_time')
        end_time = request.GET.get('end_time')
        limit = int(request.GET.get('limit', 20))

        ch_client = get_clickhouse_client()
        results = ch_client.aggregate(field, start_time, end_time, limit)

        data = []
        for row in results:
            if field == 'time':
                data.append({
                    'time': row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                    'count': row[1],
                })
            elif field == 'severity':
                data.append({
                    'severity': row[0],
                    'severity_name': get_severity_name(row[0]),
                    'count': row[1],
                })
            else:
                data.append({
                    field: row[0],
                    'count': row[1],
                })

        return JsonResponse({'status': 'success', 'data': data, 'field': field})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_GET
def get_stats(request):
    try:
        ch_client = get_clickhouse_client()
        stats = {
            'total': ch_client.count_total(),
            'last_hour': ch_client.count_last_hour(),
            'by_severity': [
                {'severity': s, 'severity_name': get_severity_name(s), 'count': c}
                for s, c in ch_client.count_by_severity()
            ],
        }
        return JsonResponse({'status': 'success', 'stats': stats})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def dashboard(request):
    return render(request, 'dashboard.html')


def alerts_page(request):
    return render(request, 'alerts.html')


def aggregation_page(request):
    return render(request, 'aggregation.html')


@require_GET
def get_top_n(request):
    try:
        field = request.GET.get('field', 'source')
        limit = min(int(request.GET.get('limit', 10)), 100)
        start_time = request.GET.get('start_time')
        end_time = request.GET.get('end_time')

        data = get_top_n(field, limit, start_time, end_time)
        
        if field == 'severity':
            for item in data:
                item['severity_name'] = get_severity_name(item['value'])

        return JsonResponse({'status': 'success', 'data': data, 'field': field})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_POST
def test_alert_rule(request):
    try:
        data = json.loads(request.body)
        rule_id = data.get('rule_id')
        if not rule_id:
            return JsonResponse({'status': 'error', 'message': 'rule_id required'}, status=400)
        
        result = run_alert_rule.delay(rule_id)
        return JsonResponse({'status': 'success', 'task_id': str(result.id)})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_GET
def list_channels(request):
    try:
        channels = AlertChannel.objects.all().order_by('-created_at')
        data = []
        for ch in channels:
            data.append({
                'id': ch.id,
                'name': ch.name,
                'channel_type': ch.channel_type,
                'channel_type_name': ch.get_channel_type_display(),
                'webhook_url': ch.webhook_url,
                'email_to': ch.email_to,
                'email_subject_prefix': ch.email_subject_prefix,
                'is_enabled': ch.is_enabled,
                'created_at': ch.created_at.isoformat(),
            })
        return JsonResponse({'status': 'success', 'channels': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_POST
def create_channel(request):
    try:
        data = json.loads(request.body)
        channel = AlertChannel.objects.create(
            name=data.get('name', ''),
            channel_type=data.get('channel_type', 'webhook'),
            webhook_url=data.get('webhook_url', ''),
            secret=data.get('secret', ''),
            email_to=data.get('email_to', ''),
            email_subject_prefix=data.get('email_subject_prefix', '[日志告警]'),
            is_enabled=data.get('is_enabled', True),
        )
        return JsonResponse({'status': 'success', 'id': channel.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_POST
def update_channel(request, channel_id):
    try:
        data = json.loads(request.body)
        channel = AlertChannel.objects.get(id=channel_id)
        for field in ['name', 'channel_type', 'webhook_url', 'secret', 'email_to', 'email_subject_prefix', 'is_enabled']:
            if field in data:
                setattr(channel, field, data[field])
        channel.save()
        return JsonResponse({'status': 'success'})
    except AlertChannel.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Channel not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_POST
def delete_channel(request, channel_id):
    try:
        channel = AlertChannel.objects.get(id=channel_id)
        channel.delete()
        return JsonResponse({'status': 'success'})
    except AlertChannel.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Channel not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_GET
def list_rules(request):
    try:
        rules = AlertRule.objects.all().order_by('-created_at')
        data = []
        for rule in rules:
            data.append({
                'id': rule.id,
                'name': rule.name,
                'description': rule.description,
                'query': rule.query,
                'filter_severity': rule.filter_severity,
                'filter_source': rule.filter_source,
                'filter_hostname': rule.filter_hostname,
                'aggregation': rule.aggregation,
                'aggregation_name': rule.get_aggregation_display(),
                'operator': rule.operator,
                'operator_name': rule.get_operator_display(),
                'threshold': rule.threshold,
                'window_minutes': rule.window_minutes,
                'channel_ids': list(rule.channels.values_list('id', flat=True)),
                'is_enabled': rule.is_enabled,
                'cooldown_minutes': rule.cooldown_minutes,
                'last_triggered_at': rule.last_triggered_at.isoformat() if rule.last_triggered_at else None,
                'last_triggered_value': rule.last_triggered_value,
                'trigger_count': rule.trigger_count,
                'created_at': rule.created_at.isoformat(),
            })
        return JsonResponse({'status': 'success', 'rules': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_POST
def create_rule(request):
    try:
        data = json.loads(request.body)
        with transaction.atomic():
            rule = AlertRule.objects.create(
                name=data.get('name', ''),
                description=data.get('description', ''),
                query=data.get('query', ''),
                filter_severity=data.get('filter_severity'),
                filter_source=data.get('filter_source', ''),
                filter_hostname=data.get('filter_hostname', ''),
                aggregation=data.get('aggregation', 'count'),
                operator=data.get('operator', 'gt'),
                threshold=data.get('threshold', 0),
                window_minutes=data.get('window_minutes', 5),
                cooldown_minutes=data.get('cooldown_minutes', 10),
                is_enabled=data.get('is_enabled', True),
            )
            channel_ids = data.get('channel_ids', [])
            if channel_ids:
                rule.channels.set(channel_ids)
        return JsonResponse({'status': 'success', 'id': rule.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_POST
def update_rule(request, rule_id):
    try:
        data = json.loads(request.body)
        rule = AlertRule.objects.get(id=rule_id)
        with transaction.atomic():
            for field in ['name', 'description', 'query', 'filter_severity', 'filter_source', 
                         'filter_hostname', 'aggregation', 'operator', 'threshold', 
                         'window_minutes', 'cooldown_minutes', 'is_enabled']:
                if field in data:
                    setattr(rule, field, data[field])
            rule.save()
            if 'channel_ids' in data:
                rule.channels.set(data['channel_ids'])
        return JsonResponse({'status': 'success'})
    except AlertRule.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Rule not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_POST
def delete_rule(request, rule_id):
    try:
        rule = AlertRule.objects.get(id=rule_id)
        rule.delete()
        return JsonResponse({'status': 'success'})
    except AlertRule.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Rule not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_POST
def toggle_rule(request, rule_id):
    try:
        rule = AlertRule.objects.get(id=rule_id)
        rule.is_enabled = not rule.is_enabled
        rule.save()
        return JsonResponse({'status': 'success', 'is_enabled': rule.is_enabled})
    except AlertRule.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Rule not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_GET
def list_events(request):
    try:
        limit = min(int(request.GET.get('limit', 50)), 200)
        rule_id = request.GET.get('rule_id')
        
        events_qs = AlertEvent.objects.select_related('rule').order_by('-triggered_at')
        if rule_id:
            events_qs = events_qs.filter(rule_id=rule_id)
        
        events = events_qs[:limit]
        data = []
        for event in events:
            data.append({
                'id': event.id,
                'rule_id': event.rule_id,
                'rule_name': event.rule.name,
                'triggered_at': event.triggered_at.isoformat(),
                'trigger_value': event.trigger_value,
                'threshold': event.threshold,
                'operator': event.operator,
                'window_minutes': event.window_minutes,
                'message': event.message,
                'is_resolved': event.is_resolved,
                'resolved_at': event.resolved_at.isoformat() if event.resolved_at else None,
            })
        return JsonResponse({'status': 'success', 'events': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_POST
def silent_rule(request, rule_id):
    try:
        data = json.loads(request.body)
        minutes = int(data.get('minutes', 60))
        rule = AlertRule.objects.get(id=rule_id)
        rule.silent_until = timezone.now() + timezone.timedelta(minutes=minutes)
        rule.save()
        return JsonResponse({'status': 'success', 'silent_until': rule.silent_until.isoformat()})
    except AlertRule.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Rule not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
