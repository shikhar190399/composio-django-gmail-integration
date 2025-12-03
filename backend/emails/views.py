"""
Views for email API and Composio webhooks.
"""

import json
import logging
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response

from .models import Email, ComposioConnection
from .serializers import EmailListSerializer, EmailDetailSerializer, ComposioConnectionSerializer
from .services import ComposioService, parse_email_from_webhook

logger = logging.getLogger(__name__)


class EmailViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API viewset for listing and retrieving emails.
    
    list: GET /api/emails/
    retrieve: GET /api/emails/{id}/
    """
    queryset = Email.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return EmailListSerializer
        return EmailDetailSerializer
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark an email as read."""
        email = self.get_object()
        email.is_read = True
        email.save(update_fields=['is_read', 'updated_at'])
        return Response({'status': 'marked as read'})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get email statistics."""
        total = Email.objects.count()
        unread = Email.objects.filter(is_read=False).count()
        return Response({
            'total': total,
            'unread': unread,
            'read': total - unread,
        })


@csrf_exempt
@require_http_methods(["POST"])
def webhook_email(request):
    """
    Webhook endpoint to receive new email notifications from Composio.
    
    POST /api/webhook/email/
    """
    try:
        payload = json.loads(request.body)
        logger.info(f"Received webhook payload: {json.dumps(payload)[:500]}")
        
        # Parse email data from webhook
        email_data = parse_email_from_webhook(payload)
        
        if not email_data.get("message_id"):
            logger.warning("Webhook payload missing message_id")
            return JsonResponse({"status": "error", "message": "Missing message_id"}, status=400)
        
        # Create or update email record
        email, created = Email.objects.update_or_create(
            message_id=email_data["message_id"],
            defaults={
                "thread_id": email_data.get("thread_id", ""),
                "subject": email_data.get("subject", ""),
                "sender": email_data.get("sender", ""),
                "recipient": email_data.get("recipient", ""),
                "body_text": email_data.get("body_text", ""),
                "body_html": email_data.get("body_html", ""),
                "snippet": email_data.get("snippet", ""),
                "labels": email_data.get("labels", []),
                "received_at": email_data.get("received_at", timezone.now()),
                "is_read": email_data.get("is_read", False),
                "raw_payload": email_data.get("raw_payload", {}),
            }
        )
        
        action = "created" if created else "updated"
        logger.info(f"Email {action}: {email.message_id}")
        
        return JsonResponse({
            "status": "success",
            "action": action,
            "email_id": email.id,
        })
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.exception(f"Webhook processing error: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@api_view(['POST'])
def initiate_connection(request):
    """
    Start the Gmail OAuth connection flow.
    
    POST /api/connect/
    Body: {"user_id": "optional-user-id"}
    
    Returns: {"redirect_url": "...", "connection_id": "..."}
    """
    user_id = request.data.get("user_id", "default-user")
    
    try:
        service = ComposioService()
        result = service.generate_connect_link(user_id)
        
        # Store connection record
        ComposioConnection.objects.update_or_create(
            user_id=user_id,
            defaults={"is_active": False}
        )
        
        return Response(result)
    except Exception as e:
        logger.exception(f"Failed to initiate connection: {e}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def complete_connection(request):
    """
    Complete the connection and enable email trigger.
    
    POST /api/connect/complete/
    Body: {"user_id": "...", "connected_account_id": "..."}
    """
    user_id = request.data.get("user_id", "default-user")
    connected_account_id = request.data.get("connected_account_id")
    
    if not connected_account_id:
        return Response(
            {"error": "connected_account_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        service = ComposioService()
        
        # Build webhook URL
        webhook_url = f"{settings.WEBHOOK_BASE_URL}/api/webhook/email/"
        
        # Enable the email trigger (uses user_id/entity_id)
        trigger_result = service.enable_email_trigger(user_id, webhook_url)
        
        # Update connection record
        connection, _ = ComposioConnection.objects.update_or_create(
            user_id=user_id,
            defaults={
                "connected_account_id": connected_account_id,
                "trigger_id": trigger_result.get("trigger_id", ""),
                "is_active": True,
                "connected_at": timezone.now(),
            }
        )
        
        return Response({
            "status": "connected",
            "trigger_id": trigger_result.get("trigger_id"),
            "webhook_url": webhook_url,
        })
    except Exception as e:
        logger.exception(f"Failed to complete connection: {e}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def connection_status(request):
    """
    Get current connection status.
    
    GET /api/connect/status/
    """
    user_id = request.query_params.get("user_id", "default-user")
    
    try:
        connection = ComposioConnection.objects.filter(user_id=user_id).first()
        if connection:
            return Response(ComposioConnectionSerializer(connection).data)
        return Response({"status": "not_connected"})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def sync_emails(request):
    """
    Manually trigger email sync from Gmail.
    
    POST /api/sync/
    """
    user_id = request.data.get("user_id", "default-user")
    max_results = request.data.get("max_results", 50)
    
    try:
        connection = ComposioConnection.objects.filter(user_id=user_id, is_active=True).first()
        if not connection:
            return Response(
                {"error": "No active connection found"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = ComposioService()
        emails = service.fetch_emails(user_id, max_results)
        
        logger.info(f"Fetched {len(emails)} emails")
        
        created_count = 0
        for email_data in emails:
            parsed = parse_email_from_webhook(email_data)
            msg_id = parsed.get("message_id")
            logger.info(f"Parsed email - message_id: {msg_id}, subject: {parsed.get('subject', '')[:30]}")
            if msg_id:
                # Remove raw_payload from defaults to avoid issues
                defaults = {k: v for k, v in parsed.items() if k != "message_id"}
                try:
                    _, created = Email.objects.update_or_create(
                        message_id=msg_id,
                        defaults=defaults
                    )
                    if created:
                        created_count += 1
                except Exception as e:
                    logger.error(f"Failed to save email {msg_id}: {e}")
        
        return Response({
            "status": "synced",
            "emails_fetched": len(emails),
            "emails_created": created_count,
        })
    except Exception as e:
        logger.exception(f"Failed to sync emails: {e}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

