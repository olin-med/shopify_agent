"""
WhatsApp integration tools for Behold Shopify Agent.
"""

from .whatsapp_tool import (
    send_whatsapp_message,
    get_whatsapp_client_info,
    check_whatsapp_status,
    get_whatsapp_qr_info,
    start_whatsapp_bridge,
)
from .whatsapp_integration import (
    WhatsAppAPI,
    WhatsAppShopifyBot,
    create_whatsapp_bot,
)
from .webhook_handler import (
    WhatsAppWebhookHandler,
    create_webhook_handler,
)

__all__ = [
    # Core WhatsApp tools
    "send_whatsapp_message",
    "get_whatsapp_client_info",
    "check_whatsapp_status",
    "get_whatsapp_qr_info",
    "start_whatsapp_bridge",

    # Integration classes
    "WhatsAppAPI",
    "WhatsAppShopifyBot",
    "create_whatsapp_bot",

    # Webhook handling
    "WhatsAppWebhookHandler",
    "create_webhook_handler",
]
