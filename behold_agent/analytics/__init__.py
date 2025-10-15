"""
Analytics and Business Intelligence package for Behold Agent.

Provides:
- Database models for tracking conversations, orders, and metrics
- Cart attribution system for linking orders to agent conversations
- Event tracking service for logging agent actions
- Analytics service for generating BI insights
- Webhook handlers for Shopify order events
- API routes for merchant dashboard
"""

from .database import (
    db_manager,
    User,
    Conversation,
    Message,
    AgentAction,
    Cart,
    Order,
    ProductView,
)

from .tracking_service import tracking_service
from .analytics_service import analytics_service
from .cart_attribution import (
    add_attribution_to_cart_input,
    extract_attribution_from_order,
)
from .api_routes import analytics_router, webhooks_router

__all__ = [
    # Database
    "db_manager",
    "User",
    "Conversation",
    "Message",
    "AgentAction",
    "Cart",
    "Order",
    "ProductView",
    # Services
    "tracking_service",
    "analytics_service",
    # Attribution
    "add_attribution_to_cart_input",
    "extract_attribution_from_order",
    # API
    "analytics_router",
    "webhooks_router",
]
