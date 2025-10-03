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
import uvicorn

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Reduce verbosity of ADK model registry logs
logging.getLogger('google_adk.google.adk.models.registry').setLevel(logging.WARNING)

# Import agent conditionally - use when available, fallback when not
try:
    from agent.agent import root_agent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai.types import Content, Part

    agent_available = True
    logger.info("✅ Behold agent loaded successfully")

    # Initialize session service and runner
    APP_NAME = "behold_whatsapp_agent"
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    logger.info("✅ ADK Runner initialized")
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
    shopify_configured = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Behold WhatsApp Shopify Agent")
    yield
    logger.info("Shutting down Behold WhatsApp Shopify Agent")


def create_application() -> FastAPI:
    """Create FastAPI application with all components."""
    app = FastAPI(
        title="Behold WhatsApp Shopify Agent",
        description="WhatsApp integration for Shopify store assistance using Google ADK",
        version="1.0.0"
    )
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {"message": "Behold WhatsApp Shopify Agent is running"}
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "Behold WhatsApp Shopify Agent"}
    
    @app.post("/process-whatsapp-message")
    async def process_whatsapp_message(request: Request):
        """Process WhatsApp message through the Behold agent."""
        try:
            data = await request.json()
            user_id = data.get("user_id")
            message = data.get("message")
            message_id = data.get("message_id")

            if not user_id or not message:
                raise HTTPException(status_code=400, detail="Missing user_id or message")

            logger.info(f"Processing message from {user_id}: {message}")

            # Use the ADK agent via Runner
            if agent_available and runner and session_service:
                try:
                    # Get or create session for this user
                    session_id = f"whatsapp_{user_id}"

                    # Create session if it doesn't exist (await is required in ADK 1.0.0+)
                    await session_service.create_session(
                        app_name=APP_NAME,
                        user_id=user_id,
                        session_id=session_id
                    )

                    # Create user message content
                    user_message = Content(role="user", parts=[Part.from_text(text=message)])

                    # Run agent asynchronously via Runner
                    response_text = ""
                    async for event in runner.run_async(
                        user_id=user_id,
                        session_id=session_id,
                        new_message=user_message
                    ):
                        if event.is_final_response():
                            response_text = event.content.parts[0].text
                            break

                    if not response_text:
                        response_text = "Hello! I'm Behold, your Shopify assistant. How can I help you today?"

                    logger.info(f"Agent response: {response_text}")

                except Exception as agent_error:
                    logger.error(f"Agent processing failed: {agent_error}")
                    raise HTTPException(status_code=500, detail=f"Agent execution failed: {agent_error}")
            else:
                logger.error("Agent not available")
                raise HTTPException(status_code=500, detail="Agent not available")

            return {"reply": response_text}

        except Exception as e:
            logger.error(f"Error processing WhatsApp message: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    return app


# Create the app
app = create_application()
app.router.lifespan_context = lifespan


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