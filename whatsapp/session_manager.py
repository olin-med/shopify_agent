"""
Session Management for WhatsApp Conversations

Manages user sessions, conversation state, cart persistence, and conversation history
for WhatsApp users interacting with the Shopify agent.
"""

import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

import aiofiles
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):
    """Possible conversation states."""
    GREETING = "greeting"
    BROWSING = "browsing"
    PRODUCT_INQUIRY = "product_inquiry"
    CART_MANAGEMENT = "cart_management"
    CHECKOUT_PROCESS = "checkout_process"
    SHIPPING_INQUIRY = "shipping_inquiry"
    POLICY_INQUIRY = "policy_inquiry"
    SUPPORT = "support"
    IDLE = "idle"


class UserSession(BaseModel):
    """User session model with conversation state and data."""
    
    phone_number: str
    session_id: str
    created_at: datetime
    last_activity: datetime
    conversation_state: ConversationState = ConversationState.GREETING
    
    # User profile information
    user_name: Optional[str] = None
    preferred_language: str = "en"
    timezone: Optional[str] = None
    
    # Shopping context
    current_cart_id: Optional[str] = None
    last_search_query: Optional[str] = None
    last_product_viewed: Optional[str] = None
    shipping_address: Optional[Dict[str, str]] = None
    
    # Conversation history (last 20 messages)
    message_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Agent context
    agent_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Preferences and settings
    notifications_enabled: bool = True
    marketing_opt_in: bool = False
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def add_message(self, message: Dict[str, Any]):
        """
        Add a message to the conversation history.
        
        Args:
            message: Message data to add
        """
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()
        
        # Add to history
        self.message_history.append(message)
        
        # Keep only last 20 messages
        if len(self.message_history) > 20:
            self.message_history = self.message_history[-20:]
        
        # Update last activity
        self.last_activity = datetime.utcnow()
    
    def update_state(self, new_state: ConversationState, context: Optional[Dict[str, Any]] = None):
        """
        Update conversation state and context.
        
        Args:
            new_state: New conversation state
            context: Additional context to store
        """
        self.conversation_state = new_state
        self.last_activity = datetime.utcnow()
        
        if context:
            self.agent_context.update(context)
    
    def get_context_summary(self) -> str:
        """
        Get a summary of the conversation context for the agent.
        
        Returns:
            Context summary string
        """
        context_parts = []
        
        # Basic user info
        if self.user_name:
            context_parts.append(f"User: {self.user_name}")
        
        context_parts.append(f"State: {self.conversation_state.value}")
        
        # Shopping context
        if self.current_cart_id:
            context_parts.append(f"Has active cart: {self.current_cart_id}")
        
        if self.last_search_query:
            context_parts.append(f"Last searched: {self.last_search_query}")
        
        if self.last_product_viewed:
            context_parts.append(f"Last viewed product: {self.last_product_viewed}")
        
        # Recent message context
        if self.message_history:
            recent_messages = self.message_history[-3:]  # Last 3 messages
            context_parts.append("Recent conversation:")
            
            for msg in recent_messages:
                sender = "User" if msg.get("direction") == "incoming" else "Agent"
                content = msg.get("content", "")[:100]  # Truncate long messages
                context_parts.append(f"  {sender}: {content}")
        
        return "\n".join(context_parts)


class SessionManager:
    """
    Manages WhatsApp user sessions and conversation state.
    
    Provides session persistence, state management, and conversation history
    for users interacting with the Shopify agent via WhatsApp.
    """
    
    def __init__(
        self,
        session_timeout_hours: int = 24,
        storage_path: str = "data/sessions",
        auto_save: bool = True
    ):
        """
        Initialize session manager.
        
        Args:
            session_timeout_hours: Hours after which inactive sessions expire
            storage_path: Directory to store session files
            auto_save: Whether to automatically save sessions
        """
        self.session_timeout = timedelta(hours=session_timeout_hours)
        self.storage_path = storage_path
        self.auto_save = auto_save
        
        # In-memory session cache
        self.sessions: Dict[str, UserSession] = {}
        
        # Background cleanup task
        self.cleanup_task: Optional[asyncio.Task] = None
        
        logger.info(f"Session manager initialized with {session_timeout_hours}h timeout")
    
    async def _ensure_storage_directory(self):
        """Ensure storage directory exists."""
        import os
        os.makedirs(self.storage_path, exist_ok=True)
    
    def _get_session_file_path(self, phone_number: str) -> str:
        """Get file path for session storage."""
        # Sanitize phone number for filename
        safe_number = phone_number.replace("+", "").replace(" ", "").replace("-", "")
        return f"{self.storage_path}/session_{safe_number}.json"
    
    async def _load_session_from_file(self, phone_number: str) -> Optional[UserSession]:
        """
        Load session from file.
        
        Args:
            phone_number: User's phone number
            
        Returns:
            UserSession if found, None otherwise
        """
        file_path = self._get_session_file_path(phone_number)
        
        try:
            async with aiofiles.open(file_path, "r") as f:
                data = await f.read()
                session_data = json.loads(data)
                
                # Convert datetime strings back to datetime objects
                session_data["created_at"] = datetime.fromisoformat(session_data["created_at"])
                session_data["last_activity"] = datetime.fromisoformat(session_data["last_activity"])
                
                return UserSession(**session_data)
                
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            logger.debug(f"Could not load session for {phone_number}: {e}")
            return None
    
    async def _save_session_to_file(self, session: UserSession):
        """
        Save session to file.
        
        Args:
            session: Session to save
        """
        if not self.auto_save:
            return
        
        await self._ensure_storage_directory()
        file_path = self._get_session_file_path(session.phone_number)
        
        try:
            async with aiofiles.open(file_path, "w") as f:
                session_data = session.model_dump()
                await f.write(json.dumps(session_data, indent=2, default=str))
                
            logger.debug(f"Session saved for {session.phone_number}")
            
        except Exception as e:
            logger.error(f"Failed to save session for {session.phone_number}: {e}")
    
    async def get_session(self, phone_number: str) -> UserSession:
        """
        Get or create user session.
        
        Args:
            phone_number: User's phone number
            
        Returns:
            UserSession object
        """
        # Check memory cache first
        if phone_number in self.sessions:
            session = self.sessions[phone_number]
            
            # Check if session is still valid
            if datetime.utcnow() - session.last_activity < self.session_timeout:
                return session
            else:
                # Session expired, remove from cache
                logger.info(f"Session expired for {phone_number}")
                del self.sessions[phone_number]
        
        # Try to load from file
        session = await self._load_session_from_file(phone_number)
        
        if session:
            # Check if file session is still valid
            if datetime.utcnow() - session.last_activity < self.session_timeout:
                # Add to cache and return
                self.sessions[phone_number] = session
                return session
            else:
                logger.info(f"File session expired for {phone_number}")
        
        # Create new session
        session = UserSession(
            phone_number=phone_number,
            session_id=f"whatsapp_{phone_number}_{int(datetime.utcnow().timestamp())}",
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        
        # Add to cache
        self.sessions[phone_number] = session
        
        # Save to file
        await self._save_session_to_file(session)
        
        logger.info(f"Created new session for {phone_number}")
        return session
    
    async def update_session(self, session: UserSession):
        """
        Update and save session.
        
        Args:
            session: Session to update
        """
        # Update in cache
        self.sessions[session.phone_number] = session
        
        # Save to file
        await self._save_session_to_file(session)
    
    async def clear_session(self, phone_number: str):
        """
        Clear session for a user.
        
        Args:
            phone_number: User's phone number
        """
        # Remove from cache
        if phone_number in self.sessions:
            del self.sessions[phone_number]
        
        # Remove file
        file_path = self._get_session_file_path(phone_number)
        try:
            import os
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Session file removed for {phone_number}")
        except Exception as e:
            logger.error(f"Failed to remove session file for {phone_number}: {e}")
    
    async def add_message_to_session(
        self,
        phone_number: str,
        message_content: str,
        direction: str,
        message_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add a message to user's session history.
        
        Args:
            phone_number: User's phone number
            message_content: Message content
            direction: 'incoming' or 'outgoing'
            message_type: Type of message (text, image, etc.)
            metadata: Additional message metadata
        """
        session = await self.get_session(phone_number)
        
        message = {
            "content": message_content,
            "direction": direction,
            "type": message_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if metadata:
            message["metadata"] = metadata
        
        session.add_message(message)
        await self.update_session(session)
    
    async def update_session_state(
        self,
        phone_number: str,
        new_state: ConversationState,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Update conversation state for a user.
        
        Args:
            phone_number: User's phone number
            new_state: New conversation state
            context: Additional context to store
        """
        session = await self.get_session(phone_number)
        session.update_state(new_state, context)
        await self.update_session(session)
        
        logger.info(f"Updated state for {phone_number}: {new_state.value}")
    
    async def set_user_cart(self, phone_number: str, cart_id: str):
        """
        Set active cart for user.
        
        Args:
            phone_number: User's phone number
            cart_id: Shopify cart ID
        """
        session = await self.get_session(phone_number)
        session.current_cart_id = cart_id
        session.last_activity = datetime.utcnow()
        await self.update_session(session)
        
        logger.info(f"Set cart {cart_id} for user {phone_number}")
    
    async def get_user_cart(self, phone_number: str) -> Optional[str]:
        """
        Get active cart ID for user.
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Cart ID if available, None otherwise
        """
        session = await self.get_session(phone_number)
        return session.current_cart_id
    
    async def set_user_profile(
        self,
        phone_number: str,
        name: Optional[str] = None,
        language: Optional[str] = None,
        timezone: Optional[str] = None
    ):
        """
        Update user profile information.
        
        Args:
            phone_number: User's phone number
            name: User's name
            language: Preferred language
            timezone: User's timezone
        """
        session = await self.get_session(phone_number)
        
        if name:
            session.user_name = name
        if language:
            session.preferred_language = language
        if timezone:
            session.timezone = timezone
        
        session.last_activity = datetime.utcnow()
        await self.update_session(session)
        
        logger.info(f"Updated profile for {phone_number}")
    
    async def get_active_sessions(self) -> List[UserSession]:
        """
        Get all active sessions.
        
        Returns:
            List of active sessions
        """
        now = datetime.utcnow()
        active_sessions = []
        
        for session in self.sessions.values():
            if now - session.last_activity < self.session_timeout:
                active_sessions.append(session)
        
        return active_sessions
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions from memory and disk."""
        now = datetime.utcnow()
        expired_numbers = []
        
        # Find expired sessions in memory
        for phone_number, session in self.sessions.items():
            if now - session.last_activity >= self.session_timeout:
                expired_numbers.append(phone_number)
        
        # Remove expired sessions
        for phone_number in expired_numbers:
            await self.clear_session(phone_number)
            logger.info(f"Cleaned up expired session for {phone_number}")
        
        # Clean up old session files
        try:
            import os
            import glob
            
            if os.path.exists(self.storage_path):
                session_files = glob.glob(f"{self.storage_path}/session_*.json")
                
                for file_path in session_files:
                    try:
                        stat = os.stat(file_path)
                        file_age = datetime.utcnow() - datetime.fromtimestamp(stat.st_mtime)
                        
                        if file_age >= self.session_timeout:
                            os.remove(file_path)
                            logger.debug(f"Removed old session file: {file_path}")
                            
                    except Exception as e:
                        logger.error(f"Error cleaning up session file {file_path}: {e}")
                        
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
    
    async def start_cleanup_task(self, cleanup_interval_minutes: int = 60):
        """
        Start background cleanup task.
        
        Args:
            cleanup_interval_minutes: How often to run cleanup (in minutes)
        """
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(cleanup_interval_minutes * 60)
                    await self.cleanup_expired_sessions()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")
        
        self.cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info(f"Started session cleanup task (every {cleanup_interval_minutes} minutes)")
    
    async def stop_cleanup_task(self):
        """Stop background cleanup task."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped session cleanup task")
    
    async def cleanup(self):
        """Clean up resources."""
        await self.stop_cleanup_task()
        
        # Save all active sessions
        for session in self.sessions.values():
            await self._save_session_to_file(session)
        
        logger.info("Session manager cleanup complete")

