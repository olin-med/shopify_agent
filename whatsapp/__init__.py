"""
WhatsApp Business API Integration Module

This module provides comprehensive WhatsApp Business API integration for the Behold Shopify agent.
It includes message handling, session management, and rich message formatting capabilities.
"""

from .client import WhatsAppClient
from .session_manager import SessionManager
from .message_handler import MessageHandler
from .formatters import WhatsAppFormatter

__all__ = [
    "WhatsAppClient",
    "SessionManager", 
    "MessageHandler",
    "WhatsAppFormatter"
]

__version__ = "1.0.0"

