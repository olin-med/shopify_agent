"""
WhatsApp Message Handler

Processes incoming WhatsApp messages, routes them to the Behold agent,
and formats responses for WhatsApp users.
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from .client import WhatsAppClient
from .session_manager import SessionManager, ConversationState
from .formatters import WhatsAppFormatter
from behold_agent.agent.agent import root_agent

logger = logging.getLogger(__name__)


class MessageHandler:
    """
    Handles WhatsApp message processing and agent integration.
    
    Processes incoming messages, maintains conversation context,
    routes messages to the Behold agent, and formats responses.
    """
    
    def __init__(
        self,
        whatsapp_client: WhatsAppClient,
        session_manager: SessionManager,
        formatter: WhatsAppFormatter
    ):
        """
        Initialize message handler.
        
        Args:
            whatsapp_client: WhatsApp client for sending messages
            session_manager: Session manager for conversation state
            formatter: Message formatter for WhatsApp
        """
        self.whatsapp_client = whatsapp_client
        self.session_manager = session_manager
        self.formatter = formatter
        self.agent = root_agent
        
        logger.info("Message handler initialized")
    
    async def handle_incoming_message(
        self,
        message: Dict[str, Any],
        webhook_data: Dict[str, Any]
    ):
        """
        Process an incoming WhatsApp message.
        
        Args:
            message: Message data from WhatsApp webhook
            webhook_data: Full webhook payload
        """
        try:
            # Extract message details
            from_number = message.get("from")
            message_id = message.get("id")
            message_type = message.get("type")
            timestamp = message.get("timestamp")
            
            if not from_number:
                logger.warning("Message missing 'from' field")
                return
            
            logger.info(f"Processing message {message_id} from {from_number}")
            
            # Mark message as read
            try:
                await self.whatsapp_client.mark_message_read(message_id)
            except Exception as e:
                logger.warning(f"Failed to mark message as read: {e}")
            
            # Get user session
            session = await self.session_manager.get_session(from_number)
            
            # Extract message content based on type
            message_content = await self._extract_message_content(message)
            
            if not message_content:
                logger.warning(f"Could not extract content from message type: {message_type}")
                await self._send_error_response(from_number, "Sorry, I couldn't understand that message type.")
                return
            
            # Add message to session history
            await self.session_manager.add_message_to_session(
                from_number,
                message_content,
                "incoming",
                message_type,
                {"message_id": message_id, "timestamp": timestamp}
            )
            
            # Process the message
            await self._process_message_content(from_number, message_content, session)
            
        except Exception as e:
            logger.error(f"Error handling incoming message: {e}")
            try:
                await self._send_error_response(
                    message.get("from", "unknown"),
                    "Sorry, I encountered an error processing your message."
                )
            except Exception as send_error:
                logger.error(f"Failed to send error response: {send_error}")
    
    async def _extract_message_content(self, message: Dict[str, Any]) -> Optional[str]:
        """
        Extract content from different message types.
        
        Args:
            message: Message data from WhatsApp
            
        Returns:
            Extracted message content or None
        """
        message_type = message.get("type")
        
        if message_type == "text":
            return message.get("text", {}).get("body", "")
        
        elif message_type == "interactive":
            # Handle button responses
            interactive = message.get("interactive", {})
            
            if interactive.get("type") == "button_reply":
                button_reply = interactive.get("button_reply", {})
                button_id = button_reply.get("id", "")
                button_title = button_reply.get("title", "")
                return f"[BUTTON:{button_id}] {button_title}"
            
            elif interactive.get("type") == "list_reply":
                list_reply = interactive.get("list_reply", {})
                list_id = list_reply.get("id", "")
                list_title = list_reply.get("title", "")
                return f"[LIST:{list_id}] {list_title}"
        
        elif message_type == "location":
            location = message.get("location", {})
            latitude = location.get("latitude", "")
            longitude = location.get("longitude", "")
            return f"[LOCATION] {latitude},{longitude}"
        
        elif message_type == "image":
            return "[IMAGE] User sent an image"
        
        elif message_type == "document":
            return "[DOCUMENT] User sent a document"
        
        elif message_type == "audio":
            return "[AUDIO] User sent an audio message"
        
        elif message_type == "video":
            return "[VIDEO] User sent a video"
        
        return None
    
    async def _process_message_content(
        self,
        from_number: str,
        content: str,
        session: Any
    ):
        """
        Process message content and generate response.
        
        Args:
            from_number: User's phone number
            content: Message content
            session: User session
        """
        try:
            # Handle button/interactive responses
            if content.startswith("[BUTTON:") or content.startswith("[LIST:"):
                await self._handle_interactive_response(from_number, content, session)
                return
            
            # Handle special commands
            if content.lower().strip() in ["hi", "hello", "hey", "start"]:
                await self._handle_greeting(from_number, session)
                return
            
            if content.lower().strip() in ["help", "menu", "options"]:
                await self._handle_help_menu(from_number, session)
                return
            
            # Prepare context for the agent
            agent_context = self._prepare_agent_context(session, content)
            
            # Send typing indicator (optional)
            # Note: WhatsApp Business API doesn't have typing indicators like regular WhatsApp
            
            # Call the Behold agent
            agent_response = await self._call_agent(agent_context)
            
            # Process agent response and send to user
            await self._process_agent_response(from_number, agent_response, session)
            
        except Exception as e:
            logger.error(f"Error processing message content: {e}")
            await self._send_error_response(from_number, "I'm having trouble processing your request right now.")
    
    def _prepare_agent_context(self, session: Any, user_message: str) -> str:
        """
        Prepare context for the agent.
        
        Args:
            session: User session
            user_message: User's message
            
        Returns:
            Formatted context for the agent
        """
        context_parts = [
            f"User Message: {user_message}",
            "",
            "CONVERSATION CONTEXT:",
            session.get_context_summary(),
            "",
            "IMPORTANT INSTRUCTIONS:",
            "- You are communicating via WhatsApp - be conversational and friendly",
            "- ALWAYS use the WhatsApp formatting tools for your responses",
            "- For products: use create_product_showcase()",
            "- For cart: use create_cart_summary()", 
            "- For greetings: use create_greeting_message()",
            "- For checkout: use format_checkout_message()",
            "- For interactive choices: use create_whatsapp_buttons()",
            "- Your response should be the output of one of these formatting tools",
            "- Be enthusiastic and helpful, like texting a friend who's a shopping expert"
        ]
        
        return "\n".join(context_parts)
    
    async def _call_agent(self, context: str) -> str:
        """
        Call the Behold agent with the prepared context.
        
        Args:
            context: Context string for the agent
            
        Returns:
            Agent response
        """
        try:
            # Note: The actual agent integration will depend on how Google ADK agents are called
            # This is a placeholder implementation
            
            # For now, we'll simulate the agent call
            # In a real implementation, you would call the agent's process method
            
            # Placeholder response
            response = f"Agent response to: {context[:100]}..."
            
            logger.info(f"Agent response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error calling agent: {e}")
            raise
    
    async def _process_agent_response(
        self,
        from_number: str,
        agent_response: str,
        session: Any
    ):
        """
        Process agent response and send to user.
        
        The agent now handles all formatting, so we just need to parse
        the structured response and send the appropriate WhatsApp message.
        
        Args:
            from_number: User's phone number
            agent_response: Structured response from the agent
            session: User session
        """
        try:
            # The agent should return structured JSON responses from the formatting tools
            # Try to parse as JSON first
            import json
            
            try:
                structured_response = json.loads(agent_response)
            except (json.JSONDecodeError, TypeError):
                # If not JSON, treat as plain text (fallback)
                await self.whatsapp_client.send_text_message(from_number, agent_response)
                await self.session_manager.add_message_to_session(
                    from_number, agent_response, "outgoing", "text"
                )
                return
            
            # Handle different response types from the agent's formatting tools
            response_type = structured_response.get("type", "text")
            
            if response_type == "interactive_buttons":
                await self._send_interactive_buttons(from_number, structured_response)
            
            elif response_type == "interactive_list":
                await self._send_interactive_list(from_number, structured_response)
            
            elif response_type == "text":
                message_text = structured_response.get("message_text", "")
                
                # Handle special case for checkout URLs
                if "checkout_url" in structured_response:
                    checkout_url = structured_response["checkout_url"]
                    message_with_url = f"{message_text}\n\n{checkout_url}"
                    await self.whatsapp_client.send_text_message(from_number, message_with_url)
                else:
                    await self.whatsapp_client.send_text_message(from_number, message_text)
            
            else:
                # Unknown type, send as text
                message_text = structured_response.get("message_text", str(structured_response))
                await self.whatsapp_client.send_text_message(from_number, message_text)
            
            # Add to session history
            await self.session_manager.add_message_to_session(
                from_number,
                str(structured_response),
                "outgoing",
                response_type
            )
            
        except Exception as e:
            logger.error(f"Error processing agent response: {e}")
            await self._send_error_response(from_number, "Sorry, I had trouble with my response.")
    
    async def _send_interactive_buttons(self, from_number: str, response_data: dict):
        """Send interactive button message."""
        await self.whatsapp_client.send_interactive_message(
            to=from_number,
            header_text=response_data.get("header_text", ""),
            body_text=response_data.get("message_text", ""),
            footer_text=response_data.get("footer_text", ""),
            buttons=response_data.get("buttons", [])
        )
    
    async def _send_interactive_list(self, from_number: str, response_data: dict):
        """Send interactive list message."""
        await self.whatsapp_client.send_interactive_message(
            to=from_number,
            header_text=response_data.get("header_text", ""),
            body_text=response_data.get("message_text", ""),
            footer_text=response_data.get("footer_text", ""),
            buttons=[{
                "id": "list_button",
                "title": response_data.get("button_text", "Choose option")
            }],
            action_type="list"
        )
    
    async def _handle_interactive_response(
        self,
        from_number: str,
        content: str,
        session: Any
    ):
        """
        Handle button or list responses.
        
        Args:
            from_number: User's phone number
            content: Interactive response content
            session: User session
        """
        try:
            # Extract button/list ID
            if content.startswith("[BUTTON:"):
                button_id = content.split("]")[0].replace("[BUTTON:", "")
            elif content.startswith("[LIST:"):
                button_id = content.split("]")[0].replace("[LIST:", "")
            else:
                return
            
            # Handle different button actions
            if button_id == "browse_products":
                await self._handle_browse_products(from_number, session)
            
            elif button_id == "view_cart":
                await self._handle_view_cart(from_number, session)
            
            elif button_id == "store_info":
                await self._handle_store_info(from_number, session)
            
            elif button_id == "checkout_cart":
                await self._handle_checkout(from_number, session)
            
            elif button_id.startswith("add_to_cart_"):
                product_id = button_id.replace("add_to_cart_", "")
                await self._handle_add_to_cart(from_number, product_id, session)
            
            elif button_id.startswith("view_product_"):
                product_id = button_id.replace("view_product_", "")
                await self._handle_view_product(from_number, product_id, session)
            
            else:
                # Unknown button, treat as regular message
                text_content = content.split("] ", 1)[1] if "] " in content else content
                await self._process_message_content(from_number, text_content, session)
            
        except Exception as e:
            logger.error(f"Error handling interactive response: {e}")
            await self._send_error_response(from_number, "Sorry, I couldn't process that action.")
    
    async def _handle_greeting(self, from_number: str, session: Any):
        """Handle greeting messages by calling the agent."""
        # Get user name if available
        user_name = session.user_name if hasattr(session, 'user_name') else None
        
        # Prepare context for greeting
        greeting_context = f"User said hello/hi. Create a greeting message"
        if user_name:
            greeting_context += f" for user named {user_name}"
        greeting_context += ". Use create_greeting_message() tool."
        
        # Call agent to generate greeting
        agent_response = await self._call_agent(greeting_context)
        await self._process_agent_response(from_number, agent_response, session)
        
        # Update session state
        await self.session_manager.update_session_state(
            from_number,
            ConversationState.BROWSING
        )
    
    async def _handle_help_menu(self, from_number: str, session: Any):
        """Handle help/menu requests."""
        help_text = (
            f"🛍️ Here's what I can help you with:\n\n"
            f"💬 *Just ask me naturally!*\n"
            f"• \"Show me your products\"\n"
            f"• \"I'm looking for shoes\"\n"
            f"• \"What's in my cart?\"\n"
            f"• \"How much is shipping to NYC?\"\n\n"
            f"Or use the quick options below:"
        )
        
        buttons = self.formatter.create_main_menu_buttons()
        
        await self.whatsapp_client.send_interactive_message(
            to=from_number,
            header_text="How can I help?",
            body_text=help_text,
            footer_text="I'm here to make shopping easy!",
            buttons=buttons
        )
    
    async def _handle_browse_products(self, from_number: str, session: Any):
        """Handle browse products action."""
        # This would call the agent to get popular/featured products
        placeholder_message = (
            f"🏪 *Featured Products*\n\n"
            f"Let me show you our most popular items!\n\n"
            f"What type of products are you interested in? "
            f"You can search for anything like \"shoes\", \"electronics\", \"clothing\", etc."
        )
        
        await self.whatsapp_client.send_text_message(from_number, placeholder_message)
        
        # Update session state
        await self.session_manager.update_session_state(
            from_number,
            ConversationState.BROWSING
        )
    
    async def _handle_view_cart(self, from_number: str, session: Any):
        """Handle view cart action."""
        cart_id = await self.session_manager.get_user_cart(from_number)
        
        if not cart_id:
            empty_cart_message = (
                f"🛒 Your cart is empty!\n\n"
                f"Would you like to browse our products?"
            )
            
            buttons = [
                {"id": "browse_products", "title": "Browse Products"},
                {"id": "search_products", "title": "Search Products"}
            ]
            
            await self.whatsapp_client.send_interactive_message(
                to=from_number,
                header_text="Empty Cart",
                body_text=empty_cart_message,
                footer_text="Let's find you something great!",
                buttons=buttons
            )
        else:
            # Call agent to get cart details
            # This is a placeholder - you'd implement the actual cart retrieval
            placeholder_message = f"🛒 Loading your cart details..."
            await self.whatsapp_client.send_text_message(from_number, placeholder_message)
        
        # Update session state
        await self.session_manager.update_session_state(
            from_number,
            ConversationState.CART_MANAGEMENT
        )
    
    async def _handle_store_info(self, from_number: str, session: Any):
        """Handle store info action."""
        # This would call the agent to get store policies
        placeholder_message = (
            f"🏪 *Store Information*\n\n"
            f"Loading our store policies and information...\n\n"
            f"You can also ask me specific questions like:\n"
            f"• \"What's your return policy?\"\n"
            f"• \"Do you offer free shipping?\"\n"
            f"• \"Where do you ship to?\""
        )
        
        await self.whatsapp_client.send_text_message(from_number, placeholder_message)
        
        # Update session state
        await self.session_manager.update_session_state(
            from_number,
            ConversationState.POLICY_INQUIRY
        )
    
    async def _handle_checkout(self, from_number: str, session: Any):
        """Handle checkout action."""
        cart_id = await self.session_manager.get_user_cart(from_number)
        
        if not cart_id:
            await self.whatsapp_client.send_text_message(
                from_number,
                "🛒 Your cart is empty. Add some products first!"
            )
            return
        
        # This would call the agent to create checkout
        placeholder_message = (
            f"🛒 Processing your checkout...\n\n"
            f"I'll create a secure checkout link for you in just a moment!"
        )
        
        await self.whatsapp_client.send_text_message(from_number, placeholder_message)
        
        # Update session state
        await self.session_manager.update_session_state(
            from_number,
            ConversationState.CHECKOUT_PROCESS
        )
    
    async def _handle_add_to_cart(self, from_number: str, product_id: str, session: Any):
        """Handle add to cart action."""
        # This would call the agent to add product to cart
        placeholder_message = f"🛒 Adding product to your cart..."
        await self.whatsapp_client.send_text_message(from_number, placeholder_message)
        
        # Update session state
        await self.session_manager.update_session_state(
            from_number,
            ConversationState.CART_MANAGEMENT,
            {"last_action": "add_to_cart", "product_id": product_id}
        )
    
    async def _handle_view_product(self, from_number: str, product_id: str, session: Any):
        """Handle view product action."""
        # This would call the agent to get product details
        placeholder_message = f"🏷️ Loading product details..."
        await self.whatsapp_client.send_text_message(from_number, placeholder_message)
        
        # Update session state
        await self.session_manager.update_session_state(
            from_number,
            ConversationState.PRODUCT_INQUIRY,
            {"last_product_viewed": product_id}
        )
    
    async def _handle_product_response(
        self,
        from_number: str,
        agent_response: str,
        session: Any
    ):
        """Handle agent response containing product data."""
        # Parse product data from agent response
        # This is a placeholder - implement based on your agent's response format
        
        # For now, send a formatted product list
        products_text = "🛍️ Here are the products I found:\n\n[Product data would be formatted here]"
        
        await self.whatsapp_client.send_text_message(from_number, products_text)
        
        # Update session state
        await self.session_manager.update_session_state(
            from_number,
            ConversationState.BROWSING
        )
    
    async def _handle_cart_response(
        self,
        from_number: str,
        agent_response: str,
        session: Any
    ):
        """Handle agent response containing cart data."""
        # Parse cart data from agent response
        # This is a placeholder - implement based on your agent's response format
        
        cart_text = "🛒 Your cart:\n\n[Cart data would be formatted here]"
        
        buttons = self.formatter.create_cart_buttons(has_items=True)
        
        await self.whatsapp_client.send_interactive_message(
            to=from_number,
            header_text="Your Cart",
            body_text=cart_text,
            footer_text="What would you like to do?",
            buttons=buttons
        )
        
        # Update session state
        await self.session_manager.update_session_state(
            from_number,
            ConversationState.CART_MANAGEMENT
        )
    
    async def _handle_shipping_response(
        self,
        from_number: str,
        agent_response: str,
        session: Any
    ):
        """Handle agent response containing shipping data."""
        # Parse shipping data from agent response
        # This is a placeholder - implement based on your agent's response format
        
        shipping_text = "🚚 Shipping estimate:\n\n[Shipping data would be formatted here]"
        
        await self.whatsapp_client.send_text_message(from_number, shipping_text)
        
        # Update session state
        await self.session_manager.update_session_state(
            from_number,
            ConversationState.SHIPPING_INQUIRY
        )
    
    async def _send_error_response(self, from_number: str, error_message: str):
        """Send error response to user."""
        try:
            formatted_error = self.formatter.format_error_message(error_message)
            await self.whatsapp_client.send_text_message(from_number, formatted_error)
        except Exception as e:
            logger.error(f"Failed to send error response: {e}")
