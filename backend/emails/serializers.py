"""
Serializers for the emails API.
"""

from rest_framework import serializers
from .models import Email, ComposioConnection


class EmailListSerializer(serializers.ModelSerializer):
    """Serializer for email list view (minimal fields)."""
    
    class Meta:
        model = Email
        fields = [
            'id',
            'message_id',
            'subject',
            'sender',
            'snippet',
            'received_at',
            'is_read',
            'labels',
        ]


class EmailDetailSerializer(serializers.ModelSerializer):
    """Serializer for email detail view (all fields)."""
    
    class Meta:
        model = Email
        fields = [
            'id',
            'message_id',
            'thread_id',
            'subject',
            'sender',
            'recipient',
            'body_text',
            'body_html',
            'snippet',
            'labels',
            'received_at',
            'is_read',
            'created_at',
        ]


class ComposioConnectionSerializer(serializers.ModelSerializer):
    """Serializer for Composio connection status."""
    
    class Meta:
        model = ComposioConnection
        fields = [
            'user_id',
            'is_active',
            'connected_at',
        ]

