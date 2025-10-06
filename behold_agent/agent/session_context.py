"""
Session context management for maintaining conversation history and state.
Implements a 5-turn context window for improved conversational experience.
Thread-safe for concurrent access by multiple clients.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
import json
import asyncio
from threading import Lock


@dataclass
class ContextEntry:
    """Single conversation turn with metadata."""
    role: str  # 'user' or 'assistant'
    message: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SessionContext:
    """Session context with 5-turn window and shopping state. Thread-safe."""
    user_id: str
    session_id: str
    conversation_history: List[ContextEntry] = field(default_factory=list)
    max_turns: int = 5  # 5 turns = 10 messages (5 user + 5 assistant)

    # Shopping state
    current_cart_id: Optional[str] = None
    recent_product_searches: List[Dict[str, Any]] = field(default_factory=list)
    recent_products_viewed: List[Dict[str, Any]] = field(default_factory=list)
    shipping_address: Optional[Dict[str, str]] = None
    user_preferences: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    last_activity: datetime = field(default_factory=datetime.utcnow)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    async def add_turn(self, user_message: str, assistant_response: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Add a complete conversation turn (user message + assistant response).
        Maintains 5-turn window by removing oldest when full.
        Thread-safe via async lock.
        """
        async with self._lock:
            now = datetime.utcnow().isoformat()
            meta = metadata or {}

            # Add user message
            self.conversation_history.append(
                ContextEntry(role="user", message=user_message, timestamp=now, metadata=meta.get("user", {}))
            )

            # Add assistant response
            self.conversation_history.append(
                ContextEntry(role="assistant", message=assistant_response, timestamp=now, metadata=meta.get("assistant", {}))
            )

            # Maintain 5-turn window (10 messages: 5 user + 5 assistant)
            max_messages = self.max_turns * 2
            if len(self.conversation_history) > max_messages:
                # Remove oldest turn (user + assistant pair)
                self.conversation_history = self.conversation_history[-max_messages:]

            # Update last activity
            self.last_activity = datetime.utcnow()

    def add_product_search(self, query: str, results: List[Dict[str, Any]], limit: int = 5):
        """Track recent product searches for context awareness."""
        search_entry = {
            "query": query,
            "results": results[:limit],  # Keep top 5 results
            "timestamp": datetime.utcnow().isoformat(),
            "result_count": len(results)
        }

        self.recent_product_searches.append(search_entry)

        # Keep only last 3 searches
        if len(self.recent_product_searches) > 3:
            self.recent_product_searches = self.recent_product_searches[-3:]

    def add_product_view(self, product: Dict[str, Any]):
        """Track products user has shown interest in."""
        view_entry = {
            "product_id": product.get("id"),
            "title": product.get("title"),
            "price": product.get("priceRange", {}).get("minVariantPrice", {}).get("amount"),
            "timestamp": datetime.utcnow().isoformat()
        }

        self.recent_products_viewed.append(view_entry)

        # Keep only last 10 views
        if len(self.recent_products_viewed) > 10:
            self.recent_products_viewed = self.recent_products_viewed[-10:]

    def update_cart(self, cart_id: str):
        """Update current cart ID."""
        self.current_cart_id = cart_id

    def update_shipping_address(self, address: Dict[str, str]):
        """Store shipping address for reuse."""
        self.shipping_address = address

    def update_preferences(self, preferences: Dict[str, Any]):
        """Update user preferences (size, color, price range, etc.)."""
        self.user_preferences.update(preferences)

    def get_context_summary(self) -> str:
        """
        Generate a concise summary of current context for the agent.
        This is injected into the agent's prompt to maintain continuity.
        """
        summary_parts = []

        # Recent conversation
        if self.conversation_history:
            recent_turns = []
            for i in range(0, len(self.conversation_history), 2):
                if i + 1 < len(self.conversation_history):
                    user_msg = self.conversation_history[i].message[:100]  # Truncate long messages
                    asst_msg = self.conversation_history[i + 1].message[:100]
                    recent_turns.append(f"User: {user_msg}\nAssistant: {asst_msg}")

            if recent_turns:
                summary_parts.append(f"**Recent Conversation:**\n" + "\n\n".join(recent_turns[-3:]))  # Last 3 turns

        # Cart context
        if self.current_cart_id:
            summary_parts.append(f"**Active Cart:** {self.current_cart_id}")

        # Recent searches
        if self.recent_product_searches:
            searches = [s["query"] for s in self.recent_product_searches[-3:]]
            summary_parts.append(f"**Recent Searches:** {', '.join(searches)}")

        # Recent products viewed
        if self.recent_products_viewed:
            products = [f"{p['title']} (${p['price']})" for p in self.recent_products_viewed[-3:]]
            summary_parts.append(f"**Products Viewed:** {', '.join(products)}")

        # Shipping address
        if self.shipping_address:
            addr = f"{self.shipping_address.get('city', '')}, {self.shipping_address.get('province', '')}, {self.shipping_address.get('country', '')}"
            summary_parts.append(f"**Shipping Address:** {addr}")

        # User preferences
        if self.user_preferences:
            prefs = ", ".join([f"{k}: {v}" for k, v in self.user_preferences.items()])
            summary_parts.append(f"**Preferences:** {prefs}")

        if not summary_parts:
            return ""

        return "\n\n".join(summary_parts)

    def get_full_history(self) -> List[Dict[str, Any]]:
        """Get complete conversation history as list of dicts."""
        return [entry.to_dict() for entry in self.conversation_history]

    def clear(self):
        """Clear all context (start fresh session)."""
        self.conversation_history.clear()
        self.recent_product_searches.clear()
        self.recent_products_viewed.clear()
        self.current_cart_id = None
        self.shipping_address = None
        self.user_preferences.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize context to dictionary for storage."""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "conversation_history": [entry.to_dict() for entry in self.conversation_history],
            "max_turns": self.max_turns,
            "current_cart_id": self.current_cart_id,
            "recent_product_searches": self.recent_product_searches,
            "recent_products_viewed": self.recent_products_viewed,
            "shipping_address": self.shipping_address,
            "user_preferences": self.user_preferences
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionContext":
        """Deserialize context from dictionary."""
        context = cls(
            user_id=data["user_id"],
            session_id=data["session_id"],
            max_turns=data.get("max_turns", 5)
        )

        # Restore conversation history
        for entry_data in data.get("conversation_history", []):
            context.conversation_history.append(ContextEntry(**entry_data))

        # Restore shopping state
        context.current_cart_id = data.get("current_cart_id")
        context.recent_product_searches = data.get("recent_product_searches", [])
        context.recent_products_viewed = data.get("recent_products_viewed", [])
        context.shipping_address = data.get("shipping_address")
        context.user_preferences = data.get("user_preferences", {})

        return context


class ContextManager:
    """
    Manages session contexts with in-memory storage.
    Thread-safe for concurrent access by multiple clients.

    Features:
    - Per-user context isolation
    - Thread-safe operations
    - Automatic cleanup of stale contexts (2 hour TTL)
    - Unlimited simultaneous users
    """

    def __init__(self, context_ttl_hours: int = 2):
        self._contexts: Dict[str, SessionContext] = {}
        self._lock = Lock()  # Thread-safe lock for dict operations
        self._context_ttl = timedelta(hours=context_ttl_hours)

    def get_or_create_context(self, user_id: str, session_id: str) -> SessionContext:
        """
        Get existing context or create new one.
        Thread-safe for concurrent access.
        """
        key = f"{user_id}:{session_id}"

        with self._lock:
            if key not in self._contexts:
                self._contexts[key] = SessionContext(user_id=user_id, session_id=session_id)

            return self._contexts[key]

    def get_context(self, user_id: str, session_id: str) -> Optional[SessionContext]:
        """Get existing context or None. Thread-safe."""
        key = f"{user_id}:{session_id}"
        with self._lock:
            return self._contexts.get(key)

    def delete_context(self, user_id: str, session_id: str) -> bool:
        """Delete a context. Returns True if deleted, False if not found."""
        key = f"{user_id}:{session_id}"
        with self._lock:
            if key in self._contexts:
                del self._contexts[key]
                return True
            return False

    def clear_all(self):
        """Clear all contexts. Thread-safe."""
        with self._lock:
            self._contexts.clear()

    def cleanup_stale_contexts(self) -> int:
        """
        Remove contexts that haven't been active within TTL.
        Returns number of contexts removed.
        """
        now = datetime.utcnow()
        stale_keys = []

        with self._lock:
            for key, context in self._contexts.items():
                if now - context.last_activity > self._context_ttl:
                    stale_keys.append(key)

            for key in stale_keys:
                del self._contexts[key]

        return len(stale_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        with self._lock:
            active_users = len(self._contexts)
            total_messages = sum(len(ctx.conversation_history) for ctx in self._contexts.values())
            active_carts = sum(1 for ctx in self._contexts.values() if ctx.current_cart_id)

            return {
                "active_sessions": active_users,
                "total_messages": total_messages,
                "active_carts": active_carts,
                "ttl_hours": self._context_ttl.total_seconds() / 3600
            }


# Global context manager instance
context_manager = ContextManager()
