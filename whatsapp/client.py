"""
WhatsApp Business Cloud API Client

Handles sending messages through Meta's WhatsApp Business Cloud API.
Supports text messages, media, interactive buttons, and rich formatting.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

import aiohttp
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class WhatsAppMessage(BaseModel):
    """Base model for WhatsApp messages."""
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    to: str
    type: str


class TextMessage(WhatsAppMessage):
    """Text message model."""
    type: str = "text"
    text: Dict[str, str]


class InteractiveMessage(WhatsAppMessage):
    """Interactive message with buttons or lists."""
    type: str = "interactive"
    interactive: Dict[str, Any]


class TemplateMessage(WhatsAppMessage):
    """Template message model."""
    type: str = "template"
    template: Dict[str, Any]


class MediaMessage(WhatsAppMessage):
    """Media message model (image, document, etc.)."""
    type: str  # image, document, audio, video
    image: Optional[Dict[str, str]] = None
    document: Optional[Dict[str, str]] = None
    audio: Optional[Dict[str, str]] = None
    video: Optional[Dict[str, str]] = None


class WhatsAppClient:
    """
    WhatsApp Business Cloud API client for sending messages.
    
    Handles authentication, message formatting, and API communication
    with Meta's WhatsApp Business platform.
    """
    
    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        verify_token: str,
        api_version: str = "v17.0"
    ):
        """
        Initialize WhatsApp client.
        
        Args:
            access_token: WhatsApp Business API access token
            phone_number_id: Phone number ID from WhatsApp Business account
            verify_token: Webhook verification token
            api_version: WhatsApp API version
        """
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.verify_token = verify_token
        self.api_version = api_version
        
        # Validate required parameters
        if not all([access_token, phone_number_id, verify_token]):
            raise ValueError("Missing required WhatsApp configuration parameters")
        
        # API base URL
        self.base_url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
        
        # HTTP session for connection pooling
        self.session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"WhatsApp client initialized for phone number ID: {phone_number_id}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def _make_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to WhatsApp API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            data: Request body data
            headers: Request headers
            
        Returns:
            API response data
            
        Raises:
            Exception: If request fails
        """
        session = await self._get_session()
        
        # Default headers
        default_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        if headers:
            default_headers.update(headers)
        
        try:
            async with session.request(
                method=method,
                url=url,
                json=data,
                headers=default_headers
            ) as response:
                response_data = await response.json()
                
                if response.status >= 400:
                    error_msg = f"WhatsApp API error: {response.status} - {response_data}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                logger.debug(f"WhatsApp API response: {response_data}")
                return response_data
                
        except aiohttp.ClientError as e:
            error_msg = f"HTTP client error: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    async def send_text_message(
        self,
        to: str,
        text: str,
        preview_url: bool = True
    ) -> Dict[str, Any]:
        """
        Send a text message.
        
        Args:
            to: Recipient phone number (with country code, no +)
            text: Message text content
            preview_url: Whether to show URL previews
            
        Returns:
            API response with message ID
        """
        message = TextMessage(
            to=to,
            text={
                "body": text,
                "preview_url": preview_url
            }
        )
        
        logger.info(f"Sending text message to {to}: {text[:100]}...")
        
        try:
            response = await self._make_request(
                method="POST",
                url=self.base_url,
                data=message.model_dump(exclude_none=True)
            )
            
            message_id = response.get("messages", [{}])[0].get("id")
            logger.info(f"Text message sent successfully: {message_id}")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to send text message: {e}")
            raise
    
    async def send_interactive_message(
        self,
        to: str,
        header_text: str,
        body_text: str,
        footer_text: str,
        buttons: List[Dict[str, str]],
        action_type: str = "buttons"
    ) -> Dict[str, Any]:
        """
        Send an interactive message with buttons.
        
        Args:
            to: Recipient phone number
            header_text: Header text (optional, can be empty)
            body_text: Main message body
            footer_text: Footer text (optional, can be empty)
            buttons: List of button dictionaries with 'id' and 'title'
            action_type: Type of interaction ('buttons' or 'list')
            
        Returns:
            API response with message ID
        """
        # Format buttons for WhatsApp API
        if action_type == "buttons":
            action_buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": btn["id"],
                        "title": btn["title"]
                    }
                }
                for btn in buttons[:3]  # WhatsApp allows max 3 buttons
            ]
            
            action = {
                "buttons": action_buttons
            }
        else:
            # List format (for more than 3 options)
            list_sections = [
                {
                    "title": "Options",
                    "rows": [
                        {
                            "id": btn["id"],
                            "title": btn["title"],
                            "description": btn.get("description", "")
                        }
                        for btn in buttons[:10]  # WhatsApp allows max 10 list items
                    ]
                }
            ]
            
            action = {
                "button": "Choose an option",
                "sections": list_sections
            }
        
        # Build interactive message
        interactive_content = {
            "type": action_type,
            "body": {"text": body_text}
        }
        
        if header_text:
            interactive_content["header"] = {"type": "text", "text": header_text}
        
        if footer_text:
            interactive_content["footer"] = {"text": footer_text}
        
        interactive_content["action"] = action
        
        message = InteractiveMessage(
            to=to,
            interactive=interactive_content
        )
        
        logger.info(f"Sending interactive message to {to} with {len(buttons)} options")
        
        try:
            response = await self._make_request(
                method="POST",
                url=self.base_url,
                data=message.model_dump(exclude_none=True)
            )
            
            message_id = response.get("messages", [{}])[0].get("id")
            logger.info(f"Interactive message sent successfully: {message_id}")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to send interactive message: {e}")
            raise
    
    async def send_product_message(
        self,
        to: str,
        header_text: str,
        body_text: str,
        products: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send a message with product information and quick action buttons.
        
        Args:
            to: Recipient phone number
            header_text: Header text
            body_text: Message body
            products: List of product dictionaries
            
        Returns:
            API response with message ID
        """
        # Create quick action buttons for products
        buttons = []
        
        for i, product in enumerate(products[:3]):  # Max 3 buttons
            buttons.append({
                "id": f"add_to_cart_{product.get('id', i)}",
                "title": f"Add {product.get('title', 'Product')}"[:20]  # WhatsApp button title limit
            })
        
        # Add view more button if there are more products
        if len(products) > 3:
            buttons.append({
                "id": "view_more_products",
                "title": "View More"
            })
        
        return await self.send_interactive_message(
            to=to,
            header_text=header_text,
            body_text=body_text,
            footer_text="Tap a button to add to cart",
            buttons=buttons
        )
    
    async def send_cart_summary(
        self,
        to: str,
        cart_data: Dict[str, Any],
        include_checkout: bool = True
    ) -> Dict[str, Any]:
        """
        Send cart summary with checkout options.
        
        Args:
            to: Recipient phone number
            cart_data: Cart information from Shopify
            include_checkout: Whether to include checkout button
            
        Returns:
            API response with message ID
        """
        # Format cart information
        lines = cart_data.get("lines", {}).get("edges", [])
        total = cart_data.get("cost", {}).get("totalAmount", {})
        
        cart_text = "🛒 *Your Cart*\n\n"
        
        for line in lines:
            node = line.get("node", {})
            merchandise = node.get("merchandise", {})
            product = merchandise.get("product", {})
            
            quantity = node.get("quantity", 1)
            title = product.get("title", "Product")
            price = merchandise.get("price", {}).get("amount", "0")
            currency = merchandise.get("price", {}).get("currencyCode", "USD")
            
            cart_text += f"• {quantity}x {title}\n"
            cart_text += f"  ${price} {currency} each\n\n"
        
        cart_text += f"*Total: ${total.get('amount', '0')} {total.get('currencyCode', 'USD')}*"
        
        # Create action buttons
        buttons = [
            {"id": "modify_cart", "title": "Modify Cart"},
            {"id": "continue_shopping", "title": "Keep Shopping"}
        ]
        
        if include_checkout:
            buttons.insert(0, {"id": "checkout_now", "title": "Checkout Now"})
        
        return await self.send_interactive_message(
            to=to,
            header_text="🛒 Cart Summary",
            body_text=cart_text,
            footer_text="What would you like to do?",
            buttons=buttons
        )
    
    async def send_image_message(
        self,
        to: str,
        image_url: str,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an image message.
        
        Args:
            to: Recipient phone number
            image_url: URL of the image
            caption: Optional caption text
            
        Returns:
            API response with message ID
        """
        image_data = {"link": image_url}
        
        if caption:
            image_data["caption"] = caption
        
        message = MediaMessage(
            to=to,
            type="image",
            image=image_data
        )
        
        logger.info(f"Sending image message to {to}: {image_url}")
        
        try:
            response = await self._make_request(
                method="POST",
                url=self.base_url,
                data=message.model_dump(exclude_none=True)
            )
            
            message_id = response.get("messages", [{}])[0].get("id")
            logger.info(f"Image message sent successfully: {message_id}")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to send image message: {e}")
            raise
    
    async def mark_message_read(self, message_id: str) -> Dict[str, Any]:
        """
        Mark a message as read.
        
        Args:
            message_id: ID of the message to mark as read
            
        Returns:
            API response
        """
        data = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        try:
            response = await self._make_request(
                method="POST",
                url=self.base_url,
                data=data
            )
            
            logger.debug(f"Marked message {message_id} as read")
            return response
            
        except Exception as e:
            logger.error(f"Failed to mark message as read: {e}")
            raise
    
    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("WhatsApp client session closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

