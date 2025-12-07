"""
Composio integration service for Gmail.
"""

import logging
from datetime import datetime
from typing import Optional
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class ComposioService:
    """Service class for interacting with Composio API."""
    
    def __init__(self):
        self.api_key = settings.COMPOSIO_API_KEY
        self._client = None
        self._toolset = None
    
    @property
    def client(self):
        """Lazy load Composio client."""
        if self._client is None:
            try:
                from composio import Composio
                self._client = Composio(api_key=self.api_key)
            except ImportError:
                logger.error("composio-core not installed. Run: pip install composio-core")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize Composio client: {e}")
                raise
        return self._client
    
    def get_toolset(self, entity_id: str):
        """Get ComposioToolSet for executing actions."""
        from composio.tools import ComposioToolSet
        return ComposioToolSet(api_key=self.api_key, entity_id=entity_id)
    
    def get_entity(self, user_id: str):
        """Get or create an entity for the user."""
        return self.client.get_entity(id=user_id)
    
    def generate_connect_link(self, user_id: str, redirect_url: Optional[str] = None) -> dict:
        """
        Generate a Composio Connect Link for Gmail OAuth.
        
        Args:
            user_id: Unique identifier for the user
            redirect_url: URL to redirect after auth (optional)
            
        Returns:
            dict with redirect_url and connection_request info
        """
        try:
            entity = self.get_entity(user_id)
            
            # Initiate connection for Gmail
            connection_request = entity.initiate_connection(
                app_name="gmail",
                redirect_url=redirect_url,
                use_composio_auth=True,
            )
            
            return {
                "redirect_url": connection_request.redirectUrl,
                "connection_id": connection_request.connectedAccountId,
                "status": "initiated"
            }
        except Exception as e:
            logger.error(f"Failed to generate connect link: {e}")
            raise
    
    def get_connection(self, user_id: str, app_name: str = "gmail"):
        """Get existing connection for user."""
        try:
            entity = self.get_entity(user_id)
            return entity.get_connection(app=app_name)
        except Exception as e:
            logger.error(f"Failed to get connection: {e}")
            return None
    
    def enable_email_trigger(self, user_id: str, webhook_url: str) -> dict:
        """
        Enable the Gmail new email trigger.
        
        Args:
            user_id: The user ID (entity ID)
            webhook_url: URL to receive webhook notifications
            
        Returns:
            dict with trigger info
        """
        try:
            entity = self.get_entity(user_id)
            
            # Enable the Gmail new message trigger
            trigger_result = entity.enable_trigger(
                app="gmail",
                trigger_name="GMAIL_NEW_GMAIL_MESSAGE",
                config={"callback_url": webhook_url}
            )
            
            return {
                "trigger_id": trigger_result.get("triggerId", str(trigger_result)),
                "status": "enabled"
            }
        except Exception as e:
            logger.error(f"Failed to enable email trigger: {e}")
            raise
    
    def disable_trigger(self, user_id: str, trigger_id: str) -> bool:
        """Disable a trigger."""
        try:
            entity = self.get_entity(user_id)
            entity.disable_trigger(trigger_id)
            return True
        except Exception as e:
            logger.error(f"Failed to disable trigger: {e}")
            return False
    
    def fetch_emails(self, user_id: str, max_results: int = 50) -> list:
        """
        Fetch emails using Composio Gmail tools.
        
        Args:
            user_id: The user ID (entity ID)
            max_results: Maximum number of emails to fetch
            
        Returns:
            list of email data dicts
        """
        try:
            toolset = self.get_toolset(user_id)
            
            # Execute the Gmail fetch emails action
            result = toolset.execute_action(
                action="GMAIL_FETCH_EMAILS",
                params={"max_results": max_results},
                entity_id=user_id,
            )
            
            # Handle different response formats
            if isinstance(result, dict):
                data = result.get("data", result.get("response_data", {}))
                if isinstance(data, dict):
                    return data.get("messages", data.get("emails", []))
                return data if isinstance(data, list) else []
            return []
        except Exception as e:
            logger.error(f"Failed to fetch emails: {e}")
            raise


def parse_email_from_webhook(payload: dict) -> dict:
    """
    Parse email data from Composio webhook/fetch payload.
    
    Args:
        payload: Raw payload from Composio (webhook or fetch response)
        
    Returns:
        dict with normalized email fields
    """
    # For webhook payloads, data might be nested under "data" key
    # For fetch results, the email object is passed directly
    data = payload
    if "data" in payload and isinstance(payload.get("data"), dict):
        data = payload["data"]
    
    # Try to extract common fields (handle both webhook and fetch formats)
    # Get the message content - Composio puts it in messageText
    message_text = data.get("messageText") or data.get("body") or data.get("bodyText") or data.get("text", "")
    body_html = data.get("bodyHtml") or data.get("html", "")
    
    # Detect if messageText is actually HTML content
    if message_text and not body_html:
        text_lower = message_text.lower().strip()
        if text_lower.startswith('<!doctype') or text_lower.startswith('<html') or '<table' in text_lower[:500]:
            # It's HTML content, move it to body_html
            body_html = message_text
            message_text = ""  # Clear text since it's HTML
    
    email_data = {
        "message_id": data.get("messageId") or data.get("id") or data.get("message_id", ""),
        "thread_id": data.get("threadId") or data.get("thread_id", ""),
        "subject": data.get("subject", "(No Subject)"),
        "sender": data.get("sender") or data.get("from", ""),
        "recipient": data.get("to") or data.get("recipient", ""),
        "body_text": message_text,
        "body_html": body_html,
        "snippet": data.get("preview") or data.get("snippet", ""),
        "labels": data.get("labelIds") or data.get("labels", []),
        "is_read": "UNREAD" not in (data.get("labelIds") or []),
        "raw_payload": payload,
    }
    
    # Parse received date - check messageTimestamp first (from fetch), then other formats
    received_at = data.get("messageTimestamp") or data.get("date") or data.get("internalDate") or data.get("received_at")
    if received_at:
        if isinstance(received_at, (int, float)):
            # Unix timestamp (milliseconds or seconds)
            email_data["received_at"] = datetime.fromtimestamp(
                received_at / 1000 if received_at > 1e10 else received_at,
                tz=timezone.utc
            )
        elif isinstance(received_at, str):
            try:
                # Try ISO format first
                email_data["received_at"] = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
            except ValueError:
                try:
                    # Try parsing as timestamp string
                    ts = float(received_at)
                    email_data["received_at"] = datetime.fromtimestamp(
                        ts / 1000 if ts > 1e10 else ts,
                        tz=timezone.utc
                    )
                except (ValueError, TypeError):
                    email_data["received_at"] = timezone.now()
        else:
            email_data["received_at"] = timezone.now()
    else:
        email_data["received_at"] = timezone.now()
    
    return email_data
