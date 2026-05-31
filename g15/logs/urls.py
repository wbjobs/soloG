from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('alerts', views.alerts_page, name='alerts_page'),
    path('aggregation', views.aggregation_page, name='aggregation_page'),
    path('api/v1/logs/http', views.receive_http_log, name='receive_http_log'),
    path('api/v1/logs/syslog', views.receive_syslog, name='receive_syslog'),
    path('api/v1/logs/search', views.search_logs, name='search_logs'),
    path('api/v1/logs/aggregate', views.aggregate_logs, name='aggregate_logs'),
    path('api/v1/logs/topn', views.get_top_n, name='get_top_n'),
    path('api/v1/stats', views.get_stats, name='get_stats'),
    
    path('api/v1/alerts/channels', views.list_channels, name='list_channels'),
    path('api/v1/alerts/channels/create', views.create_channel, name='create_channel'),
    path('api/v1/alerts/channels/<int:channel_id>/update', views.update_channel, name='update_channel'),
    path('api/v1/alerts/channels/<int:channel_id>/delete', views.delete_channel, name='delete_channel'),
    
    path('api/v1/alerts/rules', views.list_rules, name='list_rules'),
    path('api/v1/alerts/rules/create', views.create_rule, name='create_rule'),
    path('api/v1/alerts/rules/<int:rule_id>/update', views.update_rule, name='update_rule'),
    path('api/v1/alerts/rules/<int:rule_id>/delete', views.delete_rule, name='delete_rule'),
    path('api/v1/alerts/rules/<int:rule_id>/toggle', views.toggle_rule, name='toggle_rule'),
    path('api/v1/alerts/rules/<int:rule_id>/silent', views.silent_rule, name='silent_rule'),
    path('api/v1/alerts/rules/test', views.test_alert_rule, name='test_alert_rule'),
    
    path('api/v1/alerts/events', views.list_events, name='list_events'),
]
