from django.db import models
from django.utils import timezone


class AlertChannel(models.Model):
    CHANNEL_TYPES = [
        ('webhook', 'Webhook'),
        ('dingtalk', '钉钉'),
        ('email', '邮件'),
        ('feishu', '飞书'),
    ]

    name = models.CharField(max_length=100, verbose_name='通道名称')
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPES, verbose_name='通道类型')
    webhook_url = models.URLField(blank=True, null=True, verbose_name='Webhook URL')
    secret = models.CharField(max_length=200, blank=True, null=True, verbose_name='签名密钥')
    email_to = models.TextField(blank=True, null=True, verbose_name='收件人邮箱(逗号分隔)')
    email_subject_prefix = models.CharField(max_length=100, blank=True, default='[日志告警]', verbose_name='邮件主题前缀')
    is_enabled = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '告警通道'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.name} ({self.get_channel_type_display()})'


class AlertRule(models.Model):
    OPERATORS = [
        ('gt', '大于'),
        ('gte', '大于等于'),
        ('lt', '小于'),
        ('lte', '小于等于'),
        ('eq', '等于'),
        ('neq', '不等于'),
    ]

    AGGREGATIONS = [
        ('count', '计数'),
        ('avg', '平均值'),
        ('sum', '求和'),
    ]

    name = models.CharField(max_length=100, verbose_name='规则名称')
    description = models.TextField(blank=True, verbose_name='规则描述')
    
    query = models.CharField(max_length=500, blank=True, verbose_name='搜索关键词')
    filter_severity = models.IntegerField(blank=True, null=True, verbose_name='日志级别')
    filter_source = models.CharField(max_length=100, blank=True, verbose_name='日志来源')
    filter_hostname = models.CharField(max_length=100, blank=True, verbose_name='主机名')
    
    aggregation = models.CharField(max_length=20, default='count', choices=AGGREGATIONS, verbose_name='聚合方式')
    aggregation_field = models.CharField(max_length=100, blank=True, verbose_name='聚合字段')
    operator = models.CharField(max_length=10, choices=OPERATORS, default='gt', verbose_name='比较符')
    threshold = models.FloatField(verbose_name='阈值')
    window_minutes = models.IntegerField(default=5, verbose_name='时间窗口(分钟)')
    
    channels = models.ManyToManyField(AlertChannel, related_name='rules', verbose_name='通知通道')
    
    is_enabled = models.BooleanField(default=True, verbose_name='是否启用')
    silent_until = models.DateTimeField(blank=True, null=True, verbose_name='静默到')
    cooldown_minutes = models.IntegerField(default=10, verbose_name='冷却时间(分钟)')
    
    last_triggered_at = models.DateTimeField(blank=True, null=True, verbose_name='上次触发时间')
    last_triggered_value = models.FloatField(blank=True, null=True, verbose_name='上次触发值')
    trigger_count = models.IntegerField(default=0, verbose_name='触发次数')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '告警规则'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def is_in_cooldown(self):
        if not self.last_triggered_at or self.cooldown_minutes == 0:
            return False
        cooldown_until = self.last_triggered_at + timezone.timedelta(minutes=self.cooldown_minutes)
        return timezone.now() < cooldown_until

    def is_silenced(self):
        if not self.silent_until:
            return False
        return timezone.now() < self.silent_until


class AlertEvent(models.Model):
    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name='events', verbose_name='告警规则')
    triggered_at = models.DateTimeField(auto_now_add=True, verbose_name='触发时间')
    trigger_value = models.FloatField(verbose_name='触发值')
    threshold = models.FloatField(verbose_name='阈值')
    operator = models.CharField(max_length=10, verbose_name='比较符')
    window_minutes = models.IntegerField(verbose_name='时间窗口(分钟)')
    message = models.TextField(verbose_name='告警消息')
    is_resolved = models.BooleanField(default=False, verbose_name='是否已恢复')
    resolved_at = models.DateTimeField(blank=True, null=True, verbose_name='恢复时间')

    class Meta:
        verbose_name = '告警事件'
        verbose_name_plural = verbose_name
        ordering = ['-triggered_at']

    def __str__(self):
        return f'{self.rule.name} - {self.triggered_at}'
