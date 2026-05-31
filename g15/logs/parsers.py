import re
import json
import datetime
from typing import Dict, Any, Optional


SYSLOG_PATTERN = re.compile(
    r'^<(?P<priority>\d+)>(?P<version>\d+)?\s*'
    r'(?P<timestamp>\S+)\s+'
    r'(?P<hostname>\S+)\s+'
    r'(?P<appname>\S+)\s+'
    r'(?P<procid>\S+)\s+'
    r'(?P<msgid>\S+)\s+'
    r'(?P<structured>-|\[.*\])\s*'
    r'(?P<message>.*)$'
)

SYSLOG_RFC3164_PATTERN = re.compile(
    r'^<(?P<priority>\d+)>'
    r'(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
    r'(?P<hostname>\S+)\s+'
    r'(?P<message>.*)$'
)

NGINX_PATTERN = re.compile(
    r'^(?P<remote_addr>\S+)\s+-\s+(?P<remote_user>\S+)\s+'
    r'\[(?P<timestamp>[^\]]+)\]\s+'
    r'"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<protocol>[^"]+)"\s+'
    r'(?P<status>\d+)\s+(?P<body_bytes>\d+)\s+'
    r'"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)"\s*'
    r'(?P<request_time>[0-9.]+)?'
)

SEVERITY_MAP = {
    'emerg': 0, 'emergency': 0,
    'alert': 1,
    'crit': 2, 'critical': 2,
    'err': 3, 'error': 3,
    'warning': 4, 'warn': 4,
    'notice': 5,
    'info': 6, 'information': 6,
    'debug': 7,
}

SEVERITY_NAMES = {
    0: 'Emergency',
    1: 'Alert',
    2: 'Critical',
    3: 'Error',
    4: 'Warning',
    5: 'Notice',
    6: 'Info',
    7: 'Debug',
}


def parse_priority(priority: int) -> tuple:
    facility = priority >> 3
    severity = priority & 7
    return facility, severity


def parse_syslog(log_line: str) -> Optional[Dict[str, Any]]:
    match = SYSLOG_PATTERN.match(log_line.strip())
    if match:
        data = match.groupdict()
        priority = int(data.get('priority', 0))
        facility, severity = parse_priority(priority)
        timestamp = parse_timestamp(data.get('timestamp', ''))
        return {
            'timestamp': timestamp,
            'hostname': data.get('hostname', ''),
            'source': data.get('appname', 'syslog'),
            'severity': severity,
            'facility': facility,
            'message': data.get('message', ''),
            'tags': ['syslog'],
            'fields': {
                'procid': data.get('procid', ''),
                'msgid': data.get('msgid', ''),
                'structured': data.get('structured', ''),
            },
            'raw': log_line,
        }

    match = SYSLOG_RFC3164_PATTERN.match(log_line.strip())
    if match:
        data = match.groupdict()
        priority = int(data.get('priority', 0))
        facility, severity = parse_priority(priority)
        timestamp = parse_timestamp(data.get('timestamp', ''), format='%b %d %H:%M:%S')
        return {
            'timestamp': timestamp,
            'hostname': data.get('hostname', ''),
            'source': 'syslog',
            'severity': severity,
            'facility': facility,
            'message': data.get('message', ''),
            'tags': ['syslog', 'rfc3164'],
            'fields': {},
            'raw': log_line,
        }

    return None


def parse_nginx(log_line: str) -> Optional[Dict[str, Any]]:
    match = NGINX_PATTERN.match(log_line.strip())
    if match:
        data = match.groupdict()
        status = int(data.get('status', 0))
        if status >= 500:
            severity = 3
        elif status >= 400:
            severity = 4
        elif status >= 300:
            severity = 6
        else:
            severity = 6
        timestamp = parse_timestamp(data.get('timestamp', ''), format='%d/%b/%Y:%H:%M:%S %z')
        return {
            'timestamp': timestamp,
            'hostname': data.get('remote_addr', ''),
            'source': 'nginx',
            'severity': severity,
            'facility': 16,
            'message': f"{data.get('method', '')} {data.get('path', '')} {status}",
            'tags': ['nginx', 'access'],
            'fields': {
                'remote_addr': data.get('remote_addr', ''),
                'remote_user': data.get('remote_user', ''),
                'method': data.get('method', ''),
                'path': data.get('path', ''),
                'protocol': data.get('protocol', ''),
                'status': str(status),
                'body_bytes': data.get('body_bytes', ''),
                'referer': data.get('referer', ''),
                'user_agent': data.get('user_agent', ''),
                'request_time': data.get('request_time', ''),
            },
            'raw': log_line,
        }
    return None


def parse_json(log_line: str) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(log_line.strip())
        if isinstance(data, dict):
            timestamp = data.get('timestamp') or data.get('time') or data.get('@timestamp')
            timestamp = parse_timestamp(timestamp) if timestamp else datetime.datetime.now()
            severity = data.get('level') or data.get('severity') or 'info'
            if isinstance(severity, str):
                severity = SEVERITY_MAP.get(severity.lower(), 6)
            return {
                'timestamp': timestamp,
                'hostname': data.get('hostname') or data.get('host') or '',
                'source': data.get('source') or data.get('service') or 'json',
                'severity': int(severity),
                'facility': int(data.get('facility', 1)),
                'message': data.get('message') or data.get('msg') or '',
                'tags': data.get('tags', []) + ['json'],
                'fields': {k: str(v) for k, v in data.items() if k not in ['timestamp', 'time', '@timestamp', 'hostname', 'host', 'source', 'service', 'level', 'severity', 'facility', 'message', 'msg', 'tags']},
                'raw': log_line,
            }
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def parse_timestamp(timestamp_str: str, format: str = None) -> datetime.datetime:
    if not timestamp_str:
        return datetime.datetime.now()
    if isinstance(timestamp_str, datetime.datetime):
        return timestamp_str
    try:
        if format:
            return datetime.datetime.strptime(timestamp_str, format)
        for fmt in [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%d/%b/%Y:%H:%M:%S %z',
            '%b %d %H:%M:%S',
            '%b %d %H:%M:%S %Y',
        ]:
            try:
                dt = datetime.datetime.strptime(timestamp_str, fmt)
                if dt.year == 1900:
                    dt = dt.replace(year=datetime.datetime.now().year)
                return dt
            except ValueError:
                continue
        return datetime.datetime.fromisoformat(timestamp_str)
    except (ValueError, TypeError):
        return datetime.datetime.now()


def parse_log(log_line: str, source_type: str = None) -> Dict[str, Any]:
    if not log_line or not log_line.strip():
        return None

    parsers = []
    if source_type == 'syslog':
        parsers = [parse_syslog]
    elif source_type == 'nginx':
        parsers = [parse_nginx]
    elif source_type == 'json':
        parsers = [parse_json]
    else:
        parsers = [parse_json, parse_syslog, parse_nginx]

    for parser in parsers:
        result = parser(log_line)
        if result:
            return result

    return {
        'timestamp': datetime.datetime.now(),
        'hostname': '',
        'source': source_type or 'unknown',
        'severity': 6,
        'facility': 1,
        'message': log_line.strip(),
        'tags': ['raw'],
        'fields': {},
        'raw': log_line,
    }


def get_severity_name(severity: int) -> str:
    return SEVERITY_NAMES.get(severity, 'Unknown')
