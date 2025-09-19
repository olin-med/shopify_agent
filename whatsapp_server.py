"""
WhatsApp Business API Integration Server

This server handles incoming WhatsApp messages and integrates them with the Behold Shopify agent.
It provides a webhook endpoint for Meta's WhatsApp Cloud API and manages message routing.
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from whatsapp.client import WhatsAppClient
from whatsapp.session_manager import SessionManager
from whatsapp.message_handler import MessageHandler
from whatsapp.formatters import WhatsAppFormatter

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
whatsapp_client: Optional[WhatsAppClient] = None
session_manager: Optional[SessionManager] = None
message_handler: Optional[MessageHandler] = None
whatsapp_formatter: Optional[WhatsAppFormatter] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    global whatsapp_client, session_manager, message_handler, whatsapp_formatter
    
    # Startup
    logger.info("Initializing WhatsApp server components...")
    
    try:
        # Initialize WhatsApp client
        whatsapp_client = WhatsAppClient(
            access_token=os.getenv("WHATSAPP_ACCESS_TOKEN"),
            phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID"),
            verify_token=os.getenv("WHATSAPP_VERIFY_TOKEN")
        )
        
        # Initialize session manager
        session_manager = SessionManager()
        
        # Initialize message formatter
        whatsapp_formatter = WhatsAppFormatter()
        
        # Initialize message handler with dependencies
        message_handler = MessageHandler(
            whatsapp_client=whatsapp_client,
            session_manager=session_manager,
            formatter=whatsapp_formatter
        )
        
        logger.info("WhatsApp server initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize WhatsApp server: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down WhatsApp server...")
    if session_manager:
        await session_manager.cleanup()
    logger.info("WhatsApp server shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Behold WhatsApp Integration",
    description="WhatsApp Business API integration for Behold Shopify Agent",
    version="1.0.0",
    lifespan=lifespan
)


class WebhookVerification(BaseModel):
    """Model for webhook verification request."""
    hub_mode: str = Field(alias="hub.mode")
    hub_challenge: str = Field(alias="hub.challenge")
    hub_verify_token: str = Field(alias="hub.verify_token")


class WhatsAppMessage(BaseModel):
    """Model for incoming WhatsApp message."""
    object: str
    entry: List[Dict[str, Any]]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Behold WhatsApp Integration",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.get("/webhook")
async def verify_webhook(request: Request):
    """
    Webhook verification endpoint for WhatsApp Cloud API.
    
    Meta sends a GET request with verification parameters when setting up the webhook.
    """
    try:
        # Extract query parameters
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")
        
        # Verify the request
        verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
        
        if mode == "subscribe" and token == verify_token:
            logger.info("Webhook verified successfully")
            return PlainTextResponse(challenge)
        else:
            logger.warning(f"Webhook verification failed: mode={mode}, token_match={token == verify_token}")
            raise HTTPException(status_code=403, detail="Forbidden")
            
    except Exception as e:
        logger.error(f"Webhook verification error: {e}")
        raise HTTPException(status_code=400, detail="Bad Request")


@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Main webhook endpoint for receiving WhatsApp messages.
    
    Processes incoming messages and routes them to the agent.
    """
    try:
        # Parse the request body
        body = await request.json()
        logger.info(f"Received webhook: {json.dumps(body, indent=2)}")
        
        # Validate the webhook payload
        if body.get("object") != "whatsapp_business_account":
            logger.warning(f"Invalid webhook object: {body.get('object')}")
            return {"status": "ignored"}
        
        # Process messages in background
        background_tasks.add_task(process_whatsapp_webhook, body)
        
        # Return immediate response to WhatsApp
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=400, detail="Bad Request")


async def process_whatsapp_webhook(webhook_data: Dict[str, Any]):
    """
    Process WhatsApp webhook data in the background.
    
    Args:
        webhook_data: The webhook payload from WhatsApp
    """
    try:
        # Extract entries
        entries = webhook_data.get("entry", [])
        
        for entry in entries:
            # Process changes in each entry
            changes = entry.get("changes", [])
            
            for change in changes:
                # Handle message changes
                if change.get("field") == "messages":
                    await handle_message_change(change.get("value", {}))
                    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")


async def handle_message_change(message_data: Dict[str, Any]):
    """
    Handle individual message changes from webhook.
    
    Args:
        message_data: Message data from the webhook
    """
    try:
        # Extract messages
        messages = message_data.get("messages", [])
        
        for message in messages:
            # Get message details
            from_number = message.get("from")
            message_id = message.get("id")
            message_type = message.get("type")
            timestamp = message.get("timestamp")
            
            logger.info(f"Processing message: {message_id} from {from_number} type {message_type}")
            
            # Route to message handler
            if message_handler:
                await message_handler.handle_incoming_message(message, message_data)
            else:
                logger.error("Message handler not initialized")
                
    except Exception as e:
        logger.error(f"Error handling message change: {e}")


@app.post("/send-message")
async def send_message_endpoint(
    to: str,
    message: str,
    message_type: str = "text"
):
    """
    API endpoint for sending messages directly (useful for testing).
    
    Args:
        to: Phone number to send to
        message: Message content
        message_type: Type of message (text, image, etc.)
    """
    try:
        if not whatsapp_client:
            raise HTTPException(status_code=500, detail="WhatsApp client not initialized")
        
        result = await whatsapp_client.send_text_message(to, message)
        
        return {
            "status": "sent",
            "message_id": result.get("messages", [{}])[0].get("id"),
            "to": to
        }
        
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {e}")


@app.get("/sessions/{phone_number}")
async def get_session(phone_number: str):
    """
    Get session information for a phone number.
    
    Args:
        phone_number: The phone number to get session for
    """
    try:
        if not session_manager:
            raise HTTPException(status_code=500, detail="Session manager not initialized")
        
        session = await session_manager.get_session(phone_number)
        
        return {
            "phone_number": phone_number,
            "session": session.model_dump() if session else None
        }
        
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session: {e}")


@app.delete("/sessions/{phone_number}")
async def clear_session(phone_number: str):
    """
    Clear session for a phone number.
    
    Args:
        phone_number: The phone number to clear session for
    """
    try:
        if not session_manager:
            raise HTTPException(status_code=500, detail="Session manager not initialized")
        
        await session_manager.clear_session(phone_number)
        
        return {
            "status": "cleared",
            "phone_number": phone_number
        }
        
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear session: {e}")


@app.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint.
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "whatsapp_client": whatsapp_client is not None,
                "session_manager": session_manager is not None,
                "message_handler": message_handler is not None,
                "formatter": whatsapp_formatter is not None
            },
            "environment": {
                "whatsapp_token_configured": bool(os.getenv("WHATSAPP_ACCESS_TOKEN")),
                "phone_number_configured": bool(os.getenv("WHATSAPP_PHONE_NUMBER_ID")),
                "verify_token_configured": bool(os.getenv("WHATSAPP_VERIFY_TOKEN"))
            }
        }
        
        # Check if all components are healthy
        all_components_healthy = all(health_status["components"].values())
        all_env_configured = all(health_status["environment"].values())
        
        if not (all_components_healthy and all_env_configured):
            health_status["status"] = "unhealthy"
            
        return health_status
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


if __name__ == "__main__":
    # Run the server
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting WhatsApp server on {host}:{port}")
    
    uvicorn.run(
        "whatsapp_server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )

