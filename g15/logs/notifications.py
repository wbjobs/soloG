import json
import hmac
import base64
import hashlib
import time
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from urllib.request import Request, urlopen
from urllib.parse import quote_plus
from django.conf import settings


class BaseNotifier:
    def send(self, channel, alert_rule, event, trigger_value):
        raise NotImplementedError


class WebhookNotifier(BaseNotifier):
    def send(self, channel, alert_rule, event, trigger_value):
        if not channel.webhook_url:
            return False
        
        payload = {
            'rule_id': alert_rule.id,
            'rule_name': alert_rule.name,
            'triggered_at': event.triggered_at.isoformat(),
            'trigger_value': trigger_value,
            'threshold': alert_rule.threshold,
            'operator': alert_rule.operator,
            'window_minutes': alert_rule.window_minutes,
            'message': event.message,
            'severity': alert_rule.filter_severity,
            'source': alert_rule.filter_source,
        }
        
        try:
            req = Request(
                channel.webhook_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            print(f'Webhook notification failed: {e}')
            return False


class DingTalkNotifier(BaseNotifier):
    def send(self, channel, alert_rule, event, trigger_value):
        if not channel.webhook_url:
            return False
        
        timestamp = str(round(time.time() * 1000))
        sign = ''
        if channel.secret:
            secret_enc = channel.secret.encode('utf-8')
            string_to_sign = f'{timestamp}\n{channel.secret}'
            string_to_sign_enc = string_to_sign.encode('utf-8')
            hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
            sign = quote_plus(base64.b64encode(hmac_code))
        
        webhook_url = channel.webhook_url
        if sign:
            webhook_url = f'{webhook_url}&timestamp={timestamp}&sign={sign}'
        
        text = f"""### 日志告警: {alert_rule.name}

**触发时间**: {event.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}
**规则描述**: {alert_rule.description or '无'}
**触发条件**: {alert_rule.get_aggregation_display()} {alert_rule.get_operator_display()} {alert_rule.threshold} (最近 {alert_rule.window_minutes} 分钟)
**当前值**: {trigger_value}
**过滤条件**: 
- 关键词: {alert_rule.query or '无'}
- 级别: {alert_rule.filter_severity or '无'}
- 来源: {alert_rule.filter_source or '无'}
- 主机: {alert_rule.filter_hostname or '无'}

**告警消息**: {event.message}
"""
        
        payload = {
            'msgtype': 'markdown',
            'markdown': {
                'title': f'日志告警: {alert_rule.name}',
                'text': text
            },
            'at': {
                'isAtAll': False
            }
        }
        
        try:
            req = Request(
                webhook_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result.get('errcode') == 0
        except Exception as e:
            print(f'DingTalk notification failed: {e}')
            return False


class EmailNotifier(BaseNotifier):
    def send(self, channel, alert_rule, event, trigger_value):
        if not channel.email_to:
            return False
        
        email_config = getattr(settings, 'EMAIL_CONFIG', {})
        if not email_config:
            return False
        
        recipients = [e.strip() for e in channel.email_to.split(',') if e.strip()]
        if not recipients:
            return False
        
        subject = f'{channel.email_subject_prefix} {alert_rule.name}'
        body = f"""
告警规则: {alert_rule.name}
规则描述: {alert_rule.description or '无'}
触发时间: {event.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}

触发条件:
  聚合方式: {alert_rule.get_aggregation_display()}
  比较符: {alert_rule.get_operator_display()}
  阈值: {alert_rule.threshold}
  时间窗口: 最近 {alert_rule.window_minutes} 分钟

当前值: {trigger_value}

过滤条件:
  关键词: {alert_rule.query or '无'}
  日志级别: {alert_rule.filter_severity or '无'}
  日志来源: {alert_rule.filter_source or '无'}
  主机名: {alert_rule.filter_hostname or '无'}

告警消息: {event.message}

--
日志分析平台自动发送
"""
        
        try:
            msg = MIMEText(body, 'plain', 'utf-8')
            msg['From'] = Header(email_config.get('from', 'logplatform@example.com'), 'utf-8')
            msg['To'] = Header(','.join(recipients), 'utf-8')
            msg['Subject'] = Header(subject, 'utf-8')
            
            smtp = smtplib.SMTP_SSL(email_config.get('host', 'smtp.example.com'), email_config.get('port', 465))
            smtp.login(email_config.get('user', ''), email_config.get('password', ''))
            smtp.sendmail(email_config.get('from', ''), recipients, msg.as_string())
            smtp.quit()
            return True
        except Exception as e:
            print(f'Email notification failed: {e}')
            return False


class FeiShuNotifier(BaseNotifier):
    def send(self, channel, alert_rule, event, trigger_value):
        if not channel.webhook_url:
            return False
        
        timestamp = str(int(time.time()))
        sign = ''
        if channel.secret:
            string_to_sign = f'{timestamp}\n{channel.secret}'
            hmac_code = hmac.new(
                channel.secret.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()
            sign = base64.b64encode(hmac_code).decode('utf-8')
        
        text = f"""**日志告警: {alert_rule.name}**

**触发时间**: {event.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}
**规则描述**: {alert_rule.description or '无'}
**触发条件**: {alert_rule.get_aggregation_display()} {alert_rule.get_operator_display()} {alert_rule.threshold} (最近 {alert_rule.window_minutes} 分钟)
**当前值**: {trigger_value}
**过滤条件**: 
- 关键词: {alert_rule.query or '无'}
- 级别: {alert_rule.filter_severity or '无'}
- 来源: {alert_rule.filter_source or '无'}
- 主机: {alert_rule.filter_hostname or '无'}

**告警消息**: {event.message}
"""
        
        payload = {
            'timestamp': timestamp,
            'sign': sign,
            'msg_type': 'interactive',
            'card': {
                'config': {'wide_screen_mode': True},
                'header': {
                    'title': {'tag': 'plain_text', 'content': f'日志告警: {alert_rule.name}'},
                    'template': 'red'
                },
                'elements': [
                    {'tag': 'markdown', 'content': text}
                ]
            }
        }
        
        try:
            req = Request(
                channel.webhook_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result.get('code') == 0
        except Exception as e:
            print(f'FeiShu notification failed: {e}')
            return False


NOTIFIERS = {
    'webhook': WebhookNotifier(),
    'dingtalk': DingTalkNotifier(),
    'email': EmailNotifier(),
    'feishu': FeiShuNotifier(),
}


def send_notification(channel, alert_rule, event, trigger_value):
    notifier = NOTIFIERS.get(channel.channel_type)
    if not notifier:
        return False
    if not channel.is_enabled:
        return False
    return notifier.send(channel, alert_rule, event, trigger_value)
