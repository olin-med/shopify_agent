"""
FastAPI routes for analytics and business intelligence dashboard.
Provides endpoints for merchant analytics and reporting.
"""

from datetime import datetime, timedelta
from typing import Optional
import logging
from fastapi import APIRouter, Query, HTTPException, Request

from .analytics_service import analytics_service
from .webhook_handler import setup_shopify_webhooks_guide

logger = logging.getLogger(__name__)

# Create router
analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])


@analytics_router.get("/overview")
async def get_overview(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    days: Optional[int] = Query(30, description="Number of days to look back (if dates not provided)")
):
    """
    Get high-level overview metrics.

    Returns total conversations, revenue, conversion rates, etc.
    """
    try:
        # Parse dates
        end = datetime.fromisoformat(end_date) if end_date else datetime.utcnow()
        start = datetime.fromisoformat(start_date) if start_date else end - timedelta(days=days)

        metrics = analytics_service.get_overview_metrics(start, end)
        return metrics

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error getting overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@analytics_router.get("/revenue/daily")
async def get_daily_revenue(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    days: Optional[int] = Query(30, description="Number of days to look back")
):
    """
    Get daily revenue breakdown.

    Returns revenue per day for charting/visualization.
    """
    try:
        end = datetime.fromisoformat(end_date) if end_date else datetime.utcnow()
        start = datetime.fromisoformat(start_date) if start_date else end - timedelta(days=days)

        revenue_data = analytics_service.get_revenue_by_day(start, end)
        return {
            "period": {
                "start_date": start.isoformat(),
                "end_date": end.isoformat()
            },
            "daily_revenue": revenue_data
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error getting daily revenue: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@analytics_router.get("/products/top")
async def get_top_products(
    limit: int = Query(10, description="Number of products to return", ge=1, le=100),
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    days: Optional[int] = Query(30, description="Number of days to look back")
):
    """
    Get top-performing products by sales.

    Returns products with view count, cart adds, purchases, and conversion rate.
    """
    try:
        end = datetime.fromisoformat(end_date) if end_date else datetime.utcnow()
        start = datetime.fromisoformat(start_date) if start_date else end - timedelta(days=days)

        products = analytics_service.get_top_products(limit, start, end)
        return {
            "period": {
                "start_date": start.isoformat(),
                "end_date": end.isoformat()
            },
            "top_products": products
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error getting top products: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@analytics_router.get("/funnel")
async def get_conversion_funnel(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    days: Optional[int] = Query(30, description="Number of days to look back")
):
    """
    Get conversion funnel metrics.

    Shows how many users progress through each stage:
    Conversation → Search → View → Cart → Checkout → Order
    """
    try:
        end = datetime.fromisoformat(end_date) if end_date else datetime.utcnow()
        start = datetime.fromisoformat(start_date) if start_date else end - timedelta(days=days)

        funnel = analytics_service.get_conversion_funnel(start, end)
        return {
            "period": {
                "start_date": start.isoformat(),
                "end_date": end.isoformat()
            },
            **funnel
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error getting conversion funnel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@analytics_router.get("/agent/performance")
async def get_agent_performance(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    days: Optional[int] = Query(30, description="Number of days to look back")
):
    """
    Get agent performance metrics.

    Shows action success rates, response times, and most common actions.
    """
    try:
        end = datetime.fromisoformat(end_date) if end_date else datetime.utcnow()
        start = datetime.fromisoformat(start_date) if start_date else end - timedelta(days=days)

        performance = analytics_service.get_agent_performance_metrics(start, end)
        return {
            "period": {
                "start_date": start.isoformat(),
                "end_date": end.isoformat()
            },
            **performance
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error getting agent performance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@analytics_router.get("/users/engagement")
async def get_user_engagement(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    days: Optional[int] = Query(30, description="Number of days to look back")
):
    """
    Get user engagement metrics.

    Shows active users, repeat users, and engagement patterns.
    """
    try:
        end = datetime.fromisoformat(end_date) if end_date else datetime.utcnow()
        start = datetime.fromisoformat(start_date) if start_date else end - timedelta(days=days)

        engagement = analytics_service.get_user_engagement_metrics(start, end)
        return {
            "period": {
                "start_date": start.isoformat(),
                "end_date": end.isoformat()
            },
            **engagement
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error getting user engagement: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@analytics_router.get("/setup/webhooks")
async def get_webhook_setup_guide():
    """
    Get instructions for setting up Shopify webhooks.

    Webhooks are required for order attribution and automatic revenue tracking.
    """
    return setup_shopify_webhooks_guide()


# Webhook endpoints router
webhooks_router = APIRouter(prefix="/webhooks/shopify", tags=["Webhooks"])


@webhooks_router.post("/orders/create")
async def shopify_order_webhook(request: Request):
    """
    Shopify webhook endpoint for order creation.

    This endpoint receives notifications when orders are completed
    and attributes them to agent conversations.
    """
    from .webhook_handler import handle_order_create_webhook
    return await handle_order_create_webhook(request)


@webhooks_router.post("/carts/create")
async def shopify_cart_webhook(request: Request):
    """
    Shopify webhook endpoint for cart creation (optional).

    This endpoint can track cart creation events if enabled.
    """
    from .webhook_handler import handle_cart_create_webhook
    return await handle_cart_create_webhook(request)
