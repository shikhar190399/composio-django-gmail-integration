"""
Admin configuration for email models.
"""

from django.contrib import admin
from .models import Email, ComposioConnection


@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ['sender', 'subject', 'received_at', 'is_read']
    list_filter = ['is_read', 'received_at']
    search_fields = ['subject', 'sender', 'body_text']
    readonly_fields = ['message_id', 'thread_id', 'created_at', 'updated_at', 'raw_payload']
    ordering = ['-received_at']


@admin.register(ComposioConnection)
class ComposioConnectionAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'is_active', 'connected_at']
    list_filter = ['is_active']
    readonly_fields = ['created_at', 'updated_at']

