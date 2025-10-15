"""
Event tracking service for logging agent actions and user interactions.
Provides high-level API for recording all agent activities to the database.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func

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


class TrackingService:
    """Service for tracking agent interactions and business metrics."""

    def __init__(self):
        """Initialize tracking service."""
        self.db_manager = db_manager

    def get_session(self) -> Session:
        """Get database session."""
        return self.db_manager.get_session()

    # =========================================================================
    # User Management
    # =========================================================================

    def get_or_create_user(self, user_id: str, phone_number: Optional[str] = None) -> User:
        """
        Get existing user or create new one.

        Args:
            user_id: WhatsApp user ID
            phone_number: Optional phone number

        Returns:
            User object
        """
        session = self.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()

            if not user:
                user = User(
                    id=user_id,
                    phone_number=phone_number,
                    first_seen=datetime.now(),
                    last_seen=datetime.now()
                )
                session.add(user)
                session.commit()
                logger.info(f"Created new user: {user_id}")
            else:
                # Update last_seen
                user.last_seen = datetime.now()
                session.commit()

            return user
        except Exception as e:
            session.rollback()
            logger.error(f"Error getting/creating user {user_id}: {e}")
            raise
        finally:
            session.close()

    # =========================================================================
    # Conversation Management
    # =========================================================================

    def start_conversation(self, conversation_id: str, user_id: str) -> Conversation:
        """
        Start a new conversation session.

        Args:
            conversation_id: Unique conversation ID
            user_id: WhatsApp user ID

        Returns:
            Conversation object
        """
        session = self.get_session()
        try:
            # Ensure user exists
            self.get_or_create_user(user_id)

            # Check if conversation already exists
            conversation = session.query(Conversation).filter_by(id=conversation_id).first()

            if not conversation:
                conversation = Conversation(
                    id=conversation_id,
                    user_id=user_id,
                    started_at=datetime.now(),
                    last_activity=datetime.now()
                )
                session.add(conversation)
                session.commit()
                logger.info(f"Started conversation {conversation_id} for user {user_id}")

            return conversation
        except Exception as e:
            session.rollback()
            logger.error(f"Error starting conversation {conversation_id}: {e}")
            raise
        finally:
            session.close()

    def record_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record a message in the conversation.

        Args:
            conversation_id: Conversation ID
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional metadata
        """
        session = self.get_session()
        try:
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                timestamp=datetime.now(),
                message_metadata=metadata or {}
            )
            session.add(message)

            # Update conversation metrics
            conversation = session.query(Conversation).filter_by(id=conversation_id).first()
            if conversation:
                if role == "user":
                    conversation.message_count += 1
                elif role == "assistant":
                    conversation.agent_response_count += 1
                conversation.last_activity = datetime.now()

            session.commit()
            logger.debug(f"Recorded {role} message in conversation {conversation_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error recording message: {e}")
        finally:
            session.close()

    def end_conversation(self, conversation_id: str):
        """
        Mark conversation as ended and calculate duration.

        Args:
            conversation_id: Conversation ID
        """
        session = self.get_session()
        try:
            conversation = session.query(Conversation).filter_by(id=conversation_id).first()
            if conversation:
                conversation.ended_at = datetime.now()
                duration = (conversation.ended_at - conversation.started_at).total_seconds()
                conversation.total_duration_seconds = int(duration)
                session.commit()
                logger.info(f"Ended conversation {conversation_id}, duration: {duration}s")
        except Exception as e:
            session.rollback()
            logger.error(f"Error ending conversation {conversation_id}: {e}")
        finally:
            session.close()

    # =========================================================================
    # Agent Action Tracking
    # =========================================================================

    def record_agent_action(
        self,
        conversation_id: str,
        action_type: str,
        parameters: Dict[str, Any],
        result: Dict[str, Any],
        success: bool,
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ):
        """
        Record an agent tool/action execution.

        Args:
            conversation_id: Conversation ID
            action_type: Type of action (e.g., 'search_products', 'create_cart')
            parameters: Action input parameters
            result: Action result
            success: Whether action succeeded
            error_message: Optional error message
            execution_time_ms: Optional execution time in milliseconds
        """
        session = self.get_session()
        try:
            action = AgentAction(
                conversation_id=conversation_id,
                action_type=action_type,
                timestamp=datetime.now(),
                parameters=parameters,
                result=result,
                success=success,
                error_message=error_message,
                execution_time_ms=execution_time_ms
            )
            session.add(action)

            # Update conversation metrics based on action type
            conversation = session.query(Conversation).filter_by(id=conversation_id).first()
            if conversation:
                if "search" in action_type.lower() and "product" in action_type.lower():
                    conversation.products_searched += 1
                elif "cart" in action_type.lower() and "create" in action_type.lower():
                    conversation.cart_created = True
                elif "checkout" in action_type.lower():
                    conversation.checkout_initiated = True

            session.commit()
            logger.debug(f"Recorded agent action: {action_type} in conversation {conversation_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error recording agent action: {e}")
        finally:
            session.close()

    # =========================================================================
    # Cart & Order Tracking
    # =========================================================================

    def record_cart_creation(
        self,
        cart_id: str,
        conversation_id: str,
        checkout_url: Optional[str],
        items: List[Dict[str, Any]],
        subtotal_amount: float,
        currency: str = "BRL"
    ):
        """
        Record cart creation.

        Args:
            cart_id: Shopify cart ID
            conversation_id: Conversation ID
            checkout_url: Checkout URL
            items: Cart items
            subtotal_amount: Cart subtotal
            currency: Currency code
        """
        session = self.get_session()
        try:
            cart = Cart(
                id=cart_id,
                conversation_id=conversation_id,
                created_at=datetime.now(),
                checkout_url=checkout_url,
                total_items=len(items),
                subtotal_amount=subtotal_amount,
                currency=currency,
                items=items
            )
            session.add(cart)

            # Update conversation funnel flags
            conversation = session.query(Conversation).filter_by(id=conversation_id).first()
            if conversation:
                conversation.cart_created = True
                # If checkout URL exists, mark checkout as initiated
                if checkout_url:
                    conversation.checkout_initiated = True
                    logger.debug(f"Set checkout_initiated for conversation {conversation_id}")

            session.commit()
            logger.info(f"Recorded cart creation: {cart_id} for conversation {conversation_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error recording cart creation: {e}")
        finally:
            session.close()

    def record_cart_update(
        self,
        cart_id: str,
        items: List[Dict[str, Any]],
        subtotal_amount: float
    ):
        """
        Update existing cart.

        Args:
            cart_id: Shopify cart ID
            items: Updated cart items
            subtotal_amount: Updated subtotal
        """
        session = self.get_session()
        try:
            cart = session.query(Cart).filter_by(id=cart_id).first()
            if cart:
                cart.items = items
                cart.total_items = len(items)
                cart.subtotal_amount = subtotal_amount
                cart.updated_at = datetime.now()
                session.commit()
                logger.debug(f"Updated cart: {cart_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating cart {cart_id}: {e}")
        finally:
            session.close()

    def record_order_completion(
        self,
        order_id: str,
        conversation_id: str,
        user_id: str,
        cart_id: Optional[str],
        order_number: Optional[str],
        total_amount: float,
        subtotal_amount: float,
        tax_amount: float,
        shipping_amount: float,
        discount_amount: float,
        currency: str,
        items: List[Dict[str, Any]],
        customer_email: Optional[str] = None,
        attribution_data: Optional[Dict[str, Any]] = None
    ):
        """
        Record order completion (from Shopify webhook).

        Args:
            order_id: Shopify order ID
            conversation_id: Conversation ID from attribution
            user_id: User ID from attribution
            cart_id: Original cart ID
            order_number: Shopify order number
            total_amount: Total order amount
            subtotal_amount: Subtotal
            tax_amount: Tax
            shipping_amount: Shipping
            discount_amount: Discounts
            currency: Currency code
            items: Order items
            customer_email: Customer email
            attribution_data: Additional attribution metadata
        """
        session = self.get_session()
        try:
            order = Order(
                id=order_id,
                conversation_id=conversation_id,
                user_id=user_id,
                cart_id=cart_id,
                created_at=datetime.now(),
                order_number=order_number,
                total_amount=total_amount,
                subtotal_amount=subtotal_amount,
                tax_amount=tax_amount,
                shipping_amount=shipping_amount,
                discount_amount=discount_amount,
                currency=currency,
                items=items,
                customer_email=customer_email,
                attribution_data=attribution_data or {}
            )
            session.add(order)

            # Update conversation
            conversation = session.query(Conversation).filter_by(id=conversation_id).first()
            if conversation:
                conversation.order_completed = True
                conversation.total_revenue += total_amount

            # Update cart
            if cart_id:
                cart = session.query(Cart).filter_by(id=cart_id).first()
                if cart:
                    cart.converted_to_order = True
                    cart.order_id = order_id

            session.commit()
            logger.info(f"Recorded order completion: {order_id} for conversation {conversation_id}, revenue: {total_amount}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error recording order completion: {e}")
        finally:
            session.close()

    # =========================================================================
    # Product View Tracking
    # =========================================================================

    def record_product_view(
        self,
        conversation_id: str,
        product_id: str,
        product_title: Optional[str],
        product_price: Optional[float],
        product_type: Optional[str],
        recommended_by_agent: bool = True
    ):
        """
        Record product view/recommendation.

        Args:
            conversation_id: Conversation ID
            product_id: Shopify product ID
            product_title: Product title
            product_price: Product price
            product_type: Product type
            recommended_by_agent: Whether agent recommended this product
        """
        session = self.get_session()
        try:
            product_view = ProductView(
                conversation_id=conversation_id,
                product_id=product_id,
                product_title=product_title,
                product_price=product_price,
                product_type=product_type,
                viewed_at=datetime.now(),
                recommended_by_agent=recommended_by_agent
            )
            session.add(product_view)

            # Update conversation metrics
            conversation = session.query(Conversation).filter_by(id=conversation_id).first()
            if conversation:
                conversation.products_viewed += 1

            session.commit()
            logger.debug(f"Recorded product view: {product_id} in conversation {conversation_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error recording product view: {e}")
        finally:
            session.close()

    def mark_product_added_to_cart(self, conversation_id: str, product_id: str):
        """Mark that a viewed product was added to cart."""
        session = self.get_session()
        try:
            product_views = session.query(ProductView).filter_by(
                conversation_id=conversation_id,
                product_id=product_id
            ).all()

            for pv in product_views:
                pv.added_to_cart = True

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error marking product as added to cart: {e}")
        finally:
            session.close()

    def mark_product_purchased(self, conversation_id: str, product_id: str):
        """Mark that a viewed product was purchased."""
        session = self.get_session()
        try:
            product_views = session.query(ProductView).filter_by(
                conversation_id=conversation_id,
                product_id=product_id
            ).all()

            for pv in product_views:
                pv.purchased = True

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error marking product as purchased: {e}")
        finally:
            session.close()


# Global tracking service instance
tracking_service = TrackingService()
