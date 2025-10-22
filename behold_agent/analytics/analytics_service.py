"""
Analytics service for generating business intelligence insights.
Provides high-level metrics and reports for merchant dashboards.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

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

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for generating business intelligence and analytics."""

    def __init__(self):
        """Initialize analytics service."""
        self.db_manager = db_manager

    def get_session(self) -> Session:
        """Get database session."""
        return self.db_manager.get_session()

    # =========================================================================
    # Overview Metrics
    # =========================================================================

    def get_overview_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get high-level overview metrics for the dashboard.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict with overview metrics
        """
        session = self.get_session()
        try:
            # Default to last 30 days if no dates provided
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            # Total conversations
            total_conversations = session.query(func.count(Conversation.id)).filter(
                Conversation.started_at >= start_date,
                Conversation.started_at <= end_date
            ).scalar() or 0

            # Total users
            total_users = session.query(func.count(func.distinct(User.id))).join(
                Conversation, User.id == Conversation.user_id
            ).filter(
                Conversation.started_at >= start_date,
                Conversation.started_at <= end_date
            ).scalar() or 0

            # Total messages
            total_messages = session.query(func.count(Message.id)).join(
                Conversation, Message.conversation_id == Conversation.id
            ).filter(
                Conversation.started_at >= start_date,
                Conversation.started_at <= end_date
            ).scalar() or 0

            # Carts created
            carts_created = session.query(func.count(Cart.id)).filter(
                Cart.created_at >= start_date,
                Cart.created_at <= end_date
            ).scalar() or 0

            # Orders completed
            orders_completed = session.query(func.count(Order.id)).filter(
                Order.created_at >= start_date,
                Order.created_at <= end_date
            ).scalar() or 0

            # Total revenue
            total_revenue = session.query(func.sum(Order.total_amount)).filter(
                Order.created_at >= start_date,
                Order.created_at <= end_date
            ).scalar() or 0.0

            # Conversion rates
            cart_conversion_rate = (orders_completed / carts_created * 100) if carts_created > 0 else 0
            conversation_conversion_rate = (orders_completed / total_conversations * 100) if total_conversations > 0 else 0

            # Average order value
            avg_order_value = (total_revenue / orders_completed) if orders_completed > 0 else 0

            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": (end_date - start_date).days
                },
                "conversations": {
                    "total": total_conversations,
                    "unique_users": total_users,
                    "total_messages": total_messages,
                    "avg_messages_per_conversation": total_messages / total_conversations if total_conversations > 0 else 0
                },
                "commerce": {
                    "carts_created": carts_created,
                    "orders_completed": orders_completed,
                    "total_revenue": round(total_revenue, 2),
                    "avg_order_value": round(avg_order_value, 2)
                },
                "conversion": {
                    "cart_to_order_rate": round(cart_conversion_rate, 2),
                    "conversation_to_order_rate": round(conversation_conversion_rate, 2)
                }
            }

        except Exception as e:
            logger.error(f"Error getting overview metrics: {e}", exc_info=True)
            return {"error": str(e)}
        finally:
            session.close()

    # =========================================================================
    # Revenue Analytics
    # =========================================================================

    def get_revenue_by_day(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get daily revenue breakdown.

        Args:
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            List of daily revenue data
        """
        session = self.get_session()
        try:
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            # Group by date
            results = session.query(
                func.date(Order.created_at).label('date'),
                func.count(Order.id).label('order_count'),
                func.sum(Order.total_amount).label('revenue')
            ).filter(
                Order.created_at >= start_date,
                Order.created_at <= end_date
            ).group_by(
                func.date(Order.created_at)
            ).order_by('date').all()

            return [
                {
                    "date": str(row.date),
                    "order_count": row.order_count,
                    "revenue": round(float(row.revenue), 2)
                }
                for row in results
            ]

        except Exception as e:
            logger.error(f"Error getting revenue by day: {e}", exc_info=True)
            return []
        finally:
            session.close()

    # =========================================================================
    # Product Analytics
    # =========================================================================

    def get_top_products(
        self,
        limit: int = 10,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top-selling products.

        Args:
            limit: Number of products to return
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            List of top products with metrics
        """
        session = self.get_session()
        try:
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            # Get top viewed products
            top_viewed = session.query(
                ProductView.product_id,
                ProductView.product_title,
                func.count(ProductView.id).label('view_count'),
                func.count(func.nullif(ProductView.added_to_cart, False)).label('cart_adds'),
                func.count(func.nullif(ProductView.purchased, False)).label('purchases')
            ).filter(
                ProductView.viewed_at >= start_date,
                ProductView.viewed_at <= end_date
            ).group_by(
                ProductView.product_id,
                ProductView.product_title
            ).order_by(
                desc('purchases')
            ).limit(limit).all()

            return [
                {
                    "product_id": row.product_id,
                    "product_title": row.product_title,
                    "views": row.view_count,
                    "cart_adds": row.cart_adds,
                    "purchases": row.purchases,
                    "conversion_rate": round((row.purchases / row.view_count * 100), 2) if row.view_count > 0 else 0
                }
                for row in top_viewed
            ]

        except Exception as e:
            logger.error(f"Error getting top products: {e}", exc_info=True)
            return []
        finally:
            session.close()

    # =========================================================================
    # Funnel Analytics
    # =========================================================================

    def get_conversion_funnel(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get conversion funnel metrics.

        Args:
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Funnel metrics at each stage
        """
        session = self.get_session()
        try:
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            # Count conversations at each stage
            total_conversations = session.query(func.count(Conversation.id)).filter(
                Conversation.started_at >= start_date,
                Conversation.started_at <= end_date
            ).scalar() or 0

            conversations_with_search = session.query(func.count(Conversation.id)).filter(
                Conversation.started_at >= start_date,
                Conversation.started_at <= end_date,
                Conversation.products_searched > 0
            ).scalar() or 0

            conversations_with_views = session.query(func.count(Conversation.id)).filter(
                Conversation.started_at >= start_date,
                Conversation.started_at <= end_date,
                Conversation.products_viewed > 0
            ).scalar() or 0

            conversations_with_cart = session.query(func.count(Conversation.id)).filter(
                Conversation.started_at >= start_date,
                Conversation.started_at <= end_date,
                Conversation.cart_created == True
            ).scalar() or 0

            conversations_with_checkout = session.query(func.count(Conversation.id)).filter(
                Conversation.started_at >= start_date,
                Conversation.started_at <= end_date,
                Conversation.checkout_initiated == True
            ).scalar() or 0

            conversations_with_order = session.query(func.count(Conversation.id)).filter(
                Conversation.started_at >= start_date,
                Conversation.started_at <= end_date,
                Conversation.order_completed == True
            ).scalar() or 0

            def calc_rate(count, total):
                return round((count / total * 100), 2) if total > 0 else 0

            return {
                "funnel_stages": [
                    {
                        "stage": "Conversation Started",
                        "count": total_conversations,
                        "percentage": 100.0,
                        "drop_off": 0
                    },
                    {
                        "stage": "Product Search",
                        "count": conversations_with_search,
                        "percentage": calc_rate(conversations_with_search, total_conversations),
                        "drop_off": total_conversations - conversations_with_search
                    },
                    {
                        "stage": "Product Viewed",
                        "count": conversations_with_views,
                        "percentage": calc_rate(conversations_with_views, total_conversations),
                        "drop_off": conversations_with_search - conversations_with_views
                    },
                    {
                        "stage": "Cart Created",
                        "count": conversations_with_cart,
                        "percentage": calc_rate(conversations_with_cart, total_conversations),
                        "drop_off": conversations_with_views - conversations_with_cart
                    },
                    {
                        "stage": "Checkout Initiated",
                        "count": conversations_with_checkout,
                        "percentage": calc_rate(conversations_with_checkout, total_conversations),
                        "drop_off": conversations_with_cart - conversations_with_checkout
                    },
                    {
                        "stage": "Order Completed",
                        "count": conversations_with_order,
                        "percentage": calc_rate(conversations_with_order, total_conversations),
                        "drop_off": conversations_with_checkout - conversations_with_order
                    }
                ],
                "overall_conversion_rate": calc_rate(conversations_with_order, total_conversations)
            }

        except Exception as e:
            logger.error(f"Error getting conversion funnel: {e}", exc_info=True)
            return {"error": str(e)}
        finally:
            session.close()

    # =========================================================================
    # Agent Performance
    # =========================================================================

    def get_agent_performance_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get agent performance metrics.

        Args:
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Agent performance metrics
        """
        session = self.get_session()
        try:
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            # Action success rate
            total_actions = session.query(func.count(AgentAction.id)).join(
                Conversation, AgentAction.conversation_id == Conversation.id
            ).filter(
                Conversation.started_at >= start_date,
                Conversation.started_at <= end_date
            ).scalar() or 0

            successful_actions = session.query(func.count(AgentAction.id)).join(
                Conversation, AgentAction.conversation_id == Conversation.id
            ).filter(
                Conversation.started_at >= start_date,
                Conversation.started_at <= end_date,
                AgentAction.success == True
            ).scalar() or 0

            # Average response time (from action execution times)
            avg_response_time = session.query(func.avg(AgentAction.execution_time_ms)).join(
                Conversation, AgentAction.conversation_id == Conversation.id
            ).filter(
                Conversation.started_at >= start_date,
                Conversation.started_at <= end_date,
                AgentAction.execution_time_ms.isnot(None)
            ).scalar() or 0

            # Most common actions
            top_actions = session.query(
                AgentAction.action_type,
                func.count(AgentAction.id).label('count')
            ).join(
                Conversation, AgentAction.conversation_id == Conversation.id
            ).filter(
                Conversation.started_at >= start_date,
                Conversation.started_at <= end_date
            ).group_by(
                AgentAction.action_type
            ).order_by(
                desc('count')
            ).limit(10).all()

            return {
                "actions": {
                    "total_actions": total_actions,
                    "successful_actions": successful_actions,
                    "success_rate": round((successful_actions / total_actions * 100), 2) if total_actions > 0 else 0,
                    "failed_actions": total_actions - successful_actions
                },
                "performance": {
                    "avg_response_time_ms": round(float(avg_response_time), 2) if avg_response_time else 0
                },
                "top_actions": [
                    {
                        "action_type": row.action_type,
                        "count": row.count
                    }
                    for row in top_actions
                ]
            }

        except Exception as e:
            logger.error(f"Error getting agent performance metrics: {e}", exc_info=True)
            return {"error": str(e)}
        finally:
            session.close()

    # =========================================================================
    # User Behavior
    # =========================================================================

    def get_user_engagement_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get user engagement and behavior metrics.

        Args:
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            User engagement metrics
        """
        session = self.get_session()
        try:
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            # Active users
            active_users = session.query(func.count(func.distinct(User.id))).join(
                Conversation, User.id == Conversation.user_id
            ).filter(
                Conversation.started_at >= start_date,
                Conversation.started_at <= end_date
            ).scalar() or 0

            # Average conversation duration
            avg_duration = session.query(func.avg(Conversation.total_duration_seconds)).filter(
                Conversation.started_at >= start_date,
                Conversation.started_at <= end_date,
                Conversation.total_duration_seconds.isnot(None)
            ).scalar() or 0

            # Repeat users (users with > 1 conversation)
            repeat_users = session.query(func.count(func.distinct(Conversation.user_id))).filter(
                Conversation.started_at >= start_date,
                Conversation.started_at <= end_date
            ).group_by(
                Conversation.user_id
            ).having(
                func.count(Conversation.id) > 1
            ).count()

            return {
                "users": {
                    "total_active": active_users,
                    "repeat_users": repeat_users,
                    "new_users": active_users - repeat_users,
                    "repeat_rate": round((repeat_users / active_users * 100), 2) if active_users > 0 else 0
                },
                "engagement": {
                    "avg_conversation_duration_seconds": round(float(avg_duration), 2) if avg_duration else 0
                }
            }

        except Exception as e:
            logger.error(f"Error getting user engagement metrics: {e}", exc_info=True)
            return {"error": str(e)}
        finally:
            session.close()


# Global analytics service instance
analytics_service = AnalyticsService()
