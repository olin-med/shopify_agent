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

from agent.agent import root_agent
from analytics import analytics_router, webhooks_router, db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Behold WhatsApp Shopify Agent")

    # Initialize database
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
        version="1.0.0",
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

    # Include analytics and webhook routers
    app.include_router(analytics_router)
    app.include_router(webhooks_router)

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "message": "Behold WhatsApp Shopify Agent is running",
            "features": [
                "WhatsApp Sales Agent",
                "Business Intelligence & Analytics",
                "Order Attribution & Tracking",
                "Shopify Integration"
            ],
            "endpoints": {
                "analytics": "/analytics/overview",
                "webhooks": "/webhooks/shopify/orders/create",
                "health": "/health",
                "docs": "/docs"
            }
        }

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

            # Process message through the Behold agent
            # For now, return a simple response
            # TODO: Integrate with actual agent processing
            response_text = f"Thanks for your message! I'm your Shopify assistant. You said: '{message}'. How can I help you find products?"

            return {"reply": response_text}

        except Exception as e:
            logger.error(f"Error processing WhatsApp message: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    return app


# Create the app
app = create_application()


def main():
    """Main entry point."""
    # Check required environment variables
    required_vars = [
        "SHOPIFY_STORE",
        "SHOPIFY_ADMIN_TOKEN",
        "SHOPIFY_STOREFRONT_TOKEN",
        "WHATSAPP_BRIDGE_URL"
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file")
        return

    # Get configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
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