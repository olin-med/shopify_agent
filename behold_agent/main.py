"""
Main application entry point for Behold WhatsApp Shopify Agent.
"""

import os
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Reduce verbosity of ADK model registry logs
logging.getLogger('google_adk.google.adk.models.registry').setLevel(logging.WARNING)

# Import analytics system
try:
    from analytics import analytics_router, webhooks_router, db_manager, tracking_service
    analytics_available = True
    logger.info("✅ Analytics system loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Analytics system not available: {e}")
    analytics_router = None
    webhooks_router = None
    db_manager = None
    tracking_service = None
    analytics_available = False

# Import agent conditionally - use when available, fallback when not
try:
    from agent.agent import root_agent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.messages import Content, Part
    from agent.session_context import context_manager

    agent_available = True
    logger.info("✅ Behold agent loaded successfully")

    # Initialize session service and runner
    APP_NAME = "behold_whatsapp_agent"
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,  # Use the ADK agent directly (now with callbacks)
        app_name=APP_NAME,
        session_service=session_service
    )

    logger.info("✅ Context manager initialized")
    logger.info("✅ ADK callbacks are automatically registered with the agent")
    # Validate Shopify environment at startup
    def validate_shopify_config():
        """Validate Shopify configuration and test connectivity."""
        required_vars = {
            "SHOPIFY_STORE": os.getenv("SHOPIFY_STORE"),
            "SHOPIFY_STOREFRONT_TOKEN": os.getenv("SHOPIFY_STOREFRONT_TOKEN"),
            "SHOPIFY_ADMIN_TOKEN": os.getenv("SHOPIFY_ADMIN_TOKEN")
        }

        missing = [k for k, v in required_vars.items() if not v]

        if missing:
            return False

        # Test a simple GraphQL query to verify connectivity
        try:
            from agent.tools.shopify_tool import get_store_info

            result = get_store_info()

            if result.get("status") == "success":
                return True
            else:
                return False

        except Exception as e:
            return False

    # Run validation
    shopify_configured = validate_shopify_config()

except ImportError as e:
    logger.warning(f"⚠️ Failed to import root_agent: {e}")
    root_agent = None
    agent_available = False
    session_service = None
    runner = None
    context_manager = None
    shopify_configured = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Behold WhatsApp Shopify Agent")

    # Initialize database if analytics available
    if analytics_available and db_manager:
        try:
            logger.info("Creating database tables...")
            db_manager.create_tables()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    yield
    logger.info("Shutting down Behold WhatsApp Shopify Agent")


def create_application() -> FastAPI:
    """Create FastAPI application with all components."""
    app = FastAPI(
        title="Behold WhatsApp Shopify Agent",
        description="WhatsApp integration for Shopify store assistance using Google ADK with Business Intelligence",
        version="0.2.0",
        lifespan=lifespan
    )

    # Add CORS middleware for dashboard access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include analytics and webhook routers if available
    if analytics_available:
        if analytics_router:
            app.include_router(analytics_router)
            logger.info("✅ Analytics routes enabled")
        if webhooks_router:
            app.include_router(webhooks_router)
            logger.info("✅ Webhook routes enabled")

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "message": "Behold WhatsApp Shopify Agent is running",
            "version": "0.2.0",
            "features": [
                "WhatsApp Sales Agent",
                "Business Intelligence & Analytics" if analytics_available else "Business Intelligence (Not Available)",
                "Order Attribution & Tracking" if analytics_available else "Order Attribution (Not Available)",
                "Shopify Integration"
            ],
            "endpoints": {
                "health": "/health",
                "process_message": "/process-whatsapp-message",
                "analytics": "/analytics/overview" if analytics_available else None,
                "webhooks": "/webhooks/shopify/orders/create" if analytics_available else None,
                "docs": "/docs"
            }
        }
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "Behold WhatsApp Shopify Agent"}
    
    @app.post("/clear-context/{user_id}")
    async def clear_context(user_id: str):
        """Clear conversation context for a specific user."""
        if context_manager:
            session_id = f"whatsapp_{user_id}"
            context = context_manager.get_context(user_id=user_id, session_id=session_id)
            if context:
                context.clear()
                logger.info(f"Cleared context for user {user_id}")
                return {"status": "success", "message": f"Context cleared for user {user_id}"}
            else:
                return {"status": "not_found", "message": f"No context found for user {user_id}"}
        else:
            raise HTTPException(status_code=500, detail="Context manager not available")

    @app.get("/context/{user_id}")
    async def get_context(user_id: str):
        """Get conversation context for a specific user."""
        if context_manager:
            session_id = f"whatsapp_{user_id}"
            context = context_manager.get_context(user_id=user_id, session_id=session_id)
            if context:
                return {
                    "status": "success",
                    "user_id": user_id,
                    "session_id": session_id,
                    "message_count": len(context.conversation_history),
                    "current_cart_id": context.current_cart_id,
                    "recent_searches": [s["query"] for s in context.recent_product_searches],
                    "context_summary": context.get_context_summary()
                }
            else:
                return {"status": "not_found", "message": f"No context found for user {user_id}"}
        else:
            raise HTTPException(status_code=500, detail="Context manager not available")

    @app.get("/stats")
    async def get_stats():
        """Get system statistics including active sessions."""
        if context_manager:
            stats = context_manager.get_stats()
            return {
                "status": "success",
                "agent_available": agent_available,
                "shopify_configured": shopify_configured,
                **stats
            }
        else:
            return {
                "status": "success",
                "agent_available": agent_available,
                "shopify_configured": shopify_configured,
                "active_sessions": 0
            }

    @app.post("/cleanup-contexts")
    async def cleanup_contexts():
        """Manually trigger cleanup of stale contexts."""
        if context_manager:
            removed = context_manager.cleanup_stale_contexts()
            logger.info(f"Cleaned up {removed} stale contexts")
            return {
                "status": "success",
                "removed_contexts": removed,
                "remaining_sessions": len(context_manager._contexts)
            }
        else:
            raise HTTPException(status_code=500, detail="Context manager not available")

    @app.post("/process-whatsapp-message")
    async def process_whatsapp_message(request: Request):
        """Process WhatsApp message through the Behold agent."""
        try:
            data = await request.json()
            logger.info(f"Received WhatsApp data: {data}")

            user_id = data.get("user_id")
            message = data.get("message")
            message_id = data.get("message_id")

            if not user_id or not message:
                logger.error(f"Invalid request format. Expected user_id and message, got: {list(data.keys())}")
                raise HTTPException(status_code=400, detail="Missing user_id or message")

            logger.info(f"Processing message from {user_id}: {message}")

            # Use the ADK agent via Runner
            if agent_available and runner and session_service:
                try:
                    # Get or create session for this user
                    session_id = f"whatsapp_{user_id}"

                    # Track user and conversation in database
                    if tracking_service:
                        try:
                            tracking_service.get_or_create_user(user_id=user_id)
                            tracking_service.start_conversation(conversation_id=session_id, user_id=user_id)
                            logger.debug(f"Database tracking initialized for user {user_id}, session {session_id}")
                        except Exception as tracking_error:
                            logger.error(f"Failed to initialize database tracking: {tracking_error}")

                    # Get or create conversation context
                    context = context_manager.get_or_create_context(user_id=user_id, session_id=session_id)
                    logger.info(f"Context loaded: {len(context.conversation_history)} messages in history")

                    # Generate context summary for agent prompt
                    context_summary = context.get_context_summary()

                    # Check if session exists first
                    try:
                        existing_session = await session_service.get_session(
                            app_name=APP_NAME,
                            user_id=user_id,
                            session_id=session_id
                        )
                        if existing_session:
                            logger.info(f"Using existing session for user {user_id}")
                        else:
                            # Session doesn't exist, create it
                            await session_service.create_session(
                                app_name=APP_NAME,
                                user_id=user_id,
                                session_id=session_id
                            )
                            logger.info(f"Created new session for user {user_id}")
                    except Exception as session_error:
                        # If get_session fails, try creating a new session
                        try:
                            await session_service.create_session(
                                app_name=APP_NAME,
                                user_id=user_id,
                                session_id=session_id
                            )
                            logger.info(f"Created new session for user {user_id}")
                        except Exception as create_error:
                            logger.debug(f"Session already exists for {user_id}: {create_error}")

                    # Inject user WhatsApp ID, session context, and analytics IDs into the message
                    # The agent needs to know the user's WhatsApp ID for sending images
                    # AND the conversation_id/user_id for analytics tracking
                    enhanced_message = f"[USER WHATSAPP ID: {user_id}]\n"
                    enhanced_message += f"[CONVERSATION ID: {session_id}]\n"
                    enhanced_message += f"[USER ID FOR ANALYTICS: {user_id}]\n\n"
                    enhanced_message += "**IMPORTANT: Include these IDs in ALL Shopify operations:**\n"
                    enhanced_message += f"- conversation_id: \"{session_id}\"\n"
                    enhanced_message += f"- user_id: \"{user_id}\"\n\n"

                    if context_summary:
                        # Prepend context to user message (invisible to user, visible to agent)
                        enhanced_message += f"[CONTEXT FROM PREVIOUS TURNS]\n{context_summary}\n\n"

                    enhanced_message += f"[CURRENT USER MESSAGE]\n{message}"

                    # Track user message in database
                    if tracking_service:
                        try:
                            tracking_service.record_message(
                                conversation_id=session_id,
                                role="user",
                                content=message,
                                metadata={"message_id": message_id}
                            )
                        except Exception as tracking_error:
                            logger.error(f"Failed to track user message: {tracking_error}")

                    # Create user message content
                    user_message = Content(role="user", parts=[Part.from_text(text=enhanced_message)])

                    # Run agent asynchronously via Runner
                    logger.info(f"🎯 Starting agent execution for user {user_id}")
                    response_text = ""
                    whatsapp_tool_used = False
                    agent_actions = []  # Track actions for database

                    try:
                        async for event in runner.run_async(
                            user_id=user_id,
                            session_id=session_id,
                            new_message=user_message
                        ):
                            logger.debug(f"📥 Agent event received: {type(event).__name__}")
                            # Check if WhatsApp tools were used and track all function calls
                            if hasattr(event, 'content') and event.content:
                                for part in event.content.parts:
                                    if hasattr(part, 'function_call') and part.function_call:
                                        func_name = part.function_call.name
                                        func_args = dict(part.function_call.args) if part.function_call.args else {}

                                        # Track WhatsApp tool usage
                                        if func_name in ['send_whatsapp_message', 'send_whatsapp_image']:
                                            whatsapp_tool_used = True
                                            logger.info(f"Detected WhatsApp tool usage: {func_name}")

                                        # Collect agent action for database tracking
                                        agent_actions.append({
                                            "action_type": func_name,
                                            "parameters": func_args,
                                            "timestamp": "event_time"
                                        })

                                    # Track function responses (results)
                                    if hasattr(part, 'function_response') and part.function_response:
                                        func_name = part.function_response.name
                                        func_response = part.function_response.response

                                        # Find matching action and add result
                                        for action in agent_actions:
                                            if action["action_type"] == func_name and "result" not in action:
                                                action["result"] = dict(func_response) if func_response else {}
                                                action["success"] = True  # If we got a response, assume success
                                                break

                            if event.is_final_response():
                                logger.info(f"🏁 Final response received from agent")
                                response_text = event.content.parts[0].text
                                break
                        
                        logger.info(f"✅ Agent execution completed successfully")
                    except Exception as runner_error:
                        logger.error(f"❌ Exception during agent execution: {runner_error}", exc_info=True)
                        raise

                    if not response_text:
                        response_text = "Hello! I'm Behold, your Shopify assistant. How can I help you today?"

                    # Track assistant response in database
                    if tracking_service:
                        try:
                            tracking_service.record_message(
                                conversation_id=session_id,
                                role="assistant",
                                content=response_text,
                                metadata={"whatsapp_tool_used": whatsapp_tool_used}
                            )
                        except Exception as tracking_error:
                            logger.error(f"Failed to track assistant message: {tracking_error}")

                    # Track agent actions in database
                    if tracking_service and agent_actions:
                        for action in agent_actions:
                            try:
                                action_type = action.get("action_type", "unknown")
                                result_data = action.get("result", {})

                                # Track the action
                                tracking_service.record_agent_action(
                                    conversation_id=session_id,
                                    action_type=action_type,
                                    parameters=action.get("parameters", {}),
                                    result=result_data,
                                    success=action.get("success", True),
                                    error_message=action.get("error_message")
                                )

                                # Track product views from search results
                                if "search" in action_type.lower() or "product" in action_type.lower():
                                    try:
                                        products = result_data.get("products", [])
                                        for product in products[:10]:  # Track first 10 products shown
                                            product_id = product.get("id")
                                            if product_id:
                                                tracking_service.record_product_view(
                                                    conversation_id=session_id,
                                                    product_id=product_id,
                                                    product_title=product.get("title"),
                                                    product_price=float(product.get("priceRange", {}).get("minVariantPrice", {}).get("amount", 0)),
                                                    product_type=product.get("productType"),
                                                    recommended_by_agent=True
                                                )
                                    except Exception as pv_error:
                                        logger.error(f"Failed to track product views: {pv_error}")

                            except Exception as tracking_error:
                                logger.error(f"Failed to track agent action: {tracking_error}")

                    # Note: Message saving to state is now handled automatically by ADK callbacks
                    # in agent/agent.py (before_agent_callback and after_agent_callback)

                    logger.info(f"Agent response: {response_text}")
                    logger.info(f"WhatsApp tools used: {whatsapp_tool_used}")
                    
                    # Get the context for logging purposes (context is still maintained separately)
                    context = context_manager.get_or_create_context(user_id=user_id, session_id=session_id)
                    logger.info(f"Context status: {len(context.conversation_history)} messages in history")

                except Exception as agent_error:
                    logger.error(f"Agent processing failed: {agent_error}")
                    raise HTTPException(status_code=500, detail=f"Agent execution failed: {agent_error}")
            else:
                logger.error("Agent not available")
                raise HTTPException(status_code=500, detail="Agent not available")

            # If agent used WhatsApp tools, it already sent the message
            # If not, return the response so the bridge can send it
            if whatsapp_tool_used:
                logger.info("Agent used WhatsApp tools - no need to send response again")
                return {"status": "success", "message": "Agent sent messages directly via WhatsApp tools"}
            else:
                logger.info("Agent did not use WhatsApp tools - returning response for bridge to send")
                return {"reply": response_text}

        except Exception as e:
            logger.error(f"Error processing WhatsApp message: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    return app


# Create the app
app = create_application()


def main():
    """Main entry point."""
    # Log environment variable status but don't fail startup
    env_vars = [
        "SHOPIFY_STORE",
        "SHOPIFY_ADMIN_TOKEN", 
        "SHOPIFY_STOREFRONT_TOKEN",
        "WHATSAPP_BRIDGE_URL",
        "GOOGLE_API_KEY"
    ]
    
    missing_vars = [var for var in env_vars if not os.getenv(var)]
    if missing_vars:
        logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.warning("Some features may not work without these variables")

    # Get configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))  # Railway uses 8080 by default
    debug = os.getenv("DEBUG", "false").lower() == "true"

    logger.info(f"Starting server on {host}:{port}")

    # Run the application
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )


if __name__ == "__main__":
    main()