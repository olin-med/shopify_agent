"""
Database models for agent analytics and business intelligence.
Tracks the complete customer journey from conversation to order completion.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import os

Base = declarative_base()


class User(Base):
    """Represents a WhatsApp user interacting with the agent."""
    __tablename__ = "users"

    id = Column(String(255), primary_key=True)  # WhatsApp user ID
    phone_number = Column(String(50), nullable=True)
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # User metadata (renamed to avoid SQLAlchemy reserved word)
    user_metadata = Column(JSON, default=dict)  # Store additional user info

    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_user_last_seen", "last_seen"),
    )


class Conversation(Base):
    """Represents a conversation session between user and agent."""
    __tablename__ = "conversations"

    id = Column(String(255), primary_key=True)  # session_id
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False)

    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Metrics
    message_count = Column(Integer, default=0, nullable=False)
    agent_response_count = Column(Integer, default=0, nullable=False)
    total_duration_seconds = Column(Integer, default=0, nullable=True)  # When ended

    # Shopping metrics
    products_searched = Column(Integer, default=0, nullable=False)
    products_viewed = Column(Integer, default=0, nullable=False)
    cart_created = Column(Boolean, default=False, nullable=False)
    checkout_initiated = Column(Boolean, default=False, nullable=False)
    order_completed = Column(Boolean, default=False, nullable=False)

    # Revenue attribution
    total_revenue = Column(Float, default=0.0, nullable=False)  # Sum of all orders from this conversation

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    agent_actions = relationship("AgentAction", back_populates="conversation", cascade="all, delete-orphan")
    carts = relationship("Cart", back_populates="conversation", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="conversation", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_conversation_user_id", "user_id"),
        Index("idx_conversation_started_at", "started_at"),
        Index("idx_conversation_order_completed", "order_completed"),
    )


class Message(Base):
    """Individual message in a conversation."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(255), ForeignKey("conversations.id"), nullable=False)

    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Message metadata (renamed to avoid SQLAlchemy reserved word)
    message_metadata = Column(JSON, default=dict)  # Store tool usage, response time, etc.

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    # Indexes
    __table_args__ = (
        Index("idx_message_conversation_id", "conversation_id"),
        Index("idx_message_timestamp", "timestamp"),
    )


class AgentAction(Base):
    """Tracks every tool/action the agent performs."""
    __tablename__ = "agent_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(255), ForeignKey("conversations.id"), nullable=False)

    action_type = Column(String(100), nullable=False)  # 'search_products', 'create_cart', 'calculate_shipping', etc.
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Action details
    parameters = Column(JSON, default=dict)  # Input parameters
    result = Column(JSON, default=dict)  # Action result/output
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)

    # Performance
    execution_time_ms = Column(Integer, nullable=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="agent_actions")

    # Indexes
    __table_args__ = (
        Index("idx_action_conversation_id", "conversation_id"),
        Index("idx_action_type", "action_type"),
        Index("idx_action_timestamp", "timestamp"),
    )


class Cart(Base):
    """Tracks carts created by the agent."""
    __tablename__ = "carts"

    id = Column(String(255), primary_key=True)  # Shopify cart ID
    conversation_id = Column(String(255), ForeignKey("conversations.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Cart details
    checkout_url = Column(Text, nullable=True)
    total_items = Column(Integer, default=0, nullable=False)
    subtotal_amount = Column(Float, default=0.0, nullable=False)
    currency = Column(String(10), default="BRL", nullable=False)

    # Cart content (denormalized for analytics)
    items = Column(JSON, default=list)  # List of product IDs and quantities

    # Conversion tracking
    checkout_clicked = Column(Boolean, default=False, nullable=False)
    converted_to_order = Column(Boolean, default=False, nullable=False)
    order_id = Column(String(255), nullable=True)  # Shopify order ID when converted

    # Relationships
    conversation = relationship("Conversation", back_populates="carts")

    # Indexes
    __table_args__ = (
        Index("idx_cart_conversation_id", "conversation_id"),
        Index("idx_cart_created_at", "created_at"),
        Index("idx_cart_converted", "converted_to_order"),
    )


class Order(Base):
    """Tracks completed orders attributed to agent conversations."""
    __tablename__ = "orders"

    id = Column(String(255), primary_key=True)  # Shopify order ID
    conversation_id = Column(String(255), ForeignKey("conversations.id"), nullable=False)
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False)
    cart_id = Column(String(255), nullable=True)  # Original cart ID

    # Order details
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    order_number = Column(String(100), nullable=True)  # Shopify order number (#1001, etc.)

    # Financial
    total_amount = Column(Float, nullable=False)
    subtotal_amount = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0.0, nullable=False)
    shipping_amount = Column(Float, default=0.0, nullable=False)
    discount_amount = Column(Float, default=0.0, nullable=False)
    currency = Column(String(10), default="BRL", nullable=False)

    # Order content (denormalized for analytics)
    items = Column(JSON, default=list)  # Product details, quantities, prices
    customer_email = Column(String(255), nullable=True)

    # Attribution metadata from Shopify tags/attributes
    attribution_data = Column(JSON, default=dict)

    # Relationships
    conversation = relationship("Conversation", back_populates="orders")
    user = relationship("User", back_populates="orders")

    # Indexes
    __table_args__ = (
        Index("idx_order_conversation_id", "conversation_id"),
        Index("idx_order_user_id", "user_id"),
        Index("idx_order_created_at", "created_at"),
        Index("idx_order_cart_id", "cart_id"),
    )


class ProductView(Base):
    """Tracks products viewed/recommended during conversations."""
    __tablename__ = "product_views"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(255), ForeignKey("conversations.id"), nullable=False)

    product_id = Column(String(255), nullable=False)  # Shopify product ID
    product_title = Column(String(500), nullable=True)
    product_price = Column(Float, nullable=True)
    product_type = Column(String(100), nullable=True)

    viewed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Tracking
    recommended_by_agent = Column(Boolean, default=False, nullable=False)
    added_to_cart = Column(Boolean, default=False, nullable=False)
    purchased = Column(Boolean, default=False, nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_product_view_conversation_id", "conversation_id"),
        Index("idx_product_view_product_id", "product_id"),
        Index("idx_product_view_purchased", "purchased"),
    )


# Database connection and session management
class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            database_url: SQLAlchemy database URL. If None, uses DATABASE_URL env var.
        """
        if database_url is None:
            database_url = os.getenv("DATABASE_URL")

        # Validate DATABASE_URL is provided and not empty
        if not database_url:
            raise ValueError(
                "DATABASE_URL environment variable is required. "
                "Add a PostgreSQL database to your Railway project to automatically set this variable."
            )

        # Handle postgres:// to postgresql:// for SQLAlchemy 1.4+
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

        self.engine = create_engine(
            database_url,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",  # Log SQL queries if enabled
            pool_pre_ping=True,  # Verify connections before using
        )

        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        """Drop all database tables (use with caution!)."""
        Base.metadata.drop_all(bind=self.engine)

    def get_session(self):
        """Get a new database session."""
        return self.SessionLocal()


# Global database manager instance
db_manager = DatabaseManager()
