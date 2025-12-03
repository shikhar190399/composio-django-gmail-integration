"""
Email model for storing Gmail messages.
"""

from django.db import models


class Email(models.Model):
    """Represents an email message fetched from Gmail."""
    
    message_id = models.CharField(
        max_length=255, 
        unique=True, 
        db_index=True,
        help_text="Gmail message ID"
    )
    thread_id = models.CharField(
        max_length=255, 
        blank=True, 
        db_index=True,
        help_text="Gmail thread ID"
    )
    subject = models.CharField(max_length=1000, blank=True)
    sender = models.CharField(max_length=500, help_text="From address")
    recipient = models.CharField(max_length=500, blank=True, help_text="To address")
    body_text = models.TextField(blank=True, help_text="Plain text body")
    body_html = models.TextField(blank=True, help_text="HTML body")
    snippet = models.TextField(blank=True, help_text="Email preview snippet")
    labels = models.JSONField(default=list, blank=True, help_text="Gmail labels")
    received_at = models.DateTimeField(db_index=True, help_text="When email was received")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Store raw payload for debugging
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-received_at']
        verbose_name = 'Email'
        verbose_name_plural = 'Emails'

    def __str__(self):
        return f"{self.sender}: {self.subject[:50]}"


class ComposioConnection(models.Model):
    """Stores Composio connection details for Gmail integration."""
    
    user_id = models.CharField(
        max_length=255, 
        unique=True,
        help_text="User identifier used with Composio"
    )
    connected_account_id = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Composio connected account ID"
    )
    trigger_id = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Composio trigger ID for email notifications"
    )
    is_active = models.BooleanField(default=False)
    connected_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Composio Connection'
        verbose_name_plural = 'Composio Connections'

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.user_id} ({status})"

