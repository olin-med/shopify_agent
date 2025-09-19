#!/usr/bin/env python3
"""
Behold WhatsApp Integration Runner

This script starts the WhatsApp webhook server and integrates it with the Behold Shopify agent.
It provides a single entry point for running the complete WhatsApp e-commerce solution.
"""

import os
import sys
import asyncio
import logging
import signal
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after path setup
from whatsapp_server import app
import uvicorn


def setup_logging():
    """Configure logging for the application."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('whatsapp_bot.log')
        ]
    )
    
    # Reduce noise from some libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def check_environment():
    """Check that required environment variables are set."""
    required_vars = [
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID", 
        "WHATSAPP_VERIFY_TOKEN",
        "SHOPIFY_STORE",
        "SHOPIFY_ADMIN_TOKEN",
        "SHOPIFY_STOREFRONT_TOKEN"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Please check your .env file and ensure all variables are set.")
        print("   See env.example for reference.")
        return False
    
    return True


def check_dependencies():
    """Check that required dependencies are installed."""
    required_packages = [
        "fastapi",
        "uvicorn", 
        "aiohttp",
        "pydantic",
        "aiofiles",
        "python-dotenv"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Install missing packages with:")
        print("   pip install -r requirements-whatsapp.txt")
        return False
    
    return True


def create_directories():
    """Create necessary directories for the application."""
    directories = [
        "data",
        "data/sessions",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def print_startup_info():
    """Print startup information and instructions."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    print("🚀 Behold WhatsApp Integration")
    print("=" * 50)
    print(f"📱 Server starting on: http://{host}:{port}")
    print(f"🔗 Health check: http://localhost:{port}/health")
    print(f"📞 Webhook endpoint: http://localhost:{port}/webhook")
    print()
    print("📋 Quick Setup Checklist:")
    print("  ✅ Environment variables configured")
    print("  ✅ Dependencies installed")
    print("  ✅ Directories created")
    print()
    print("🌐 For local testing with Meta:")
    print("  1. Install ngrok: npm install -g ngrok")
    print("  2. Run: ngrok http 8000")
    print("  3. Copy the HTTPS URL to Meta webhook config")
    print()
    print("📖 Full setup guide: WHATSAPP_SETUP.md")
    print("=" * 50)


async def main():
    """Main application entry point."""
    print("🔄 Starting Behold WhatsApp Integration...")
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Print startup info
    print_startup_info()
    
    # Get server configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    # Configure uvicorn
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        access_log=True,
        reload=False  # Set to True for development
    )
    
    # Create server
    server = uvicorn.Server(config)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal, stopping server...")
        server.should_exit = True
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("WhatsApp server starting...")
        await server.serve()
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        logger.info("WhatsApp server stopped")


if __name__ == "__main__":
    # Check if .env file exists
    if not Path(".env").exists():
        print("⚠️  Warning: .env file not found")
        print("📋 Please copy env.example to .env and configure your settings")
        print()
        
        # Ask if user wants to continue anyway (for Docker/cloud deployment)
        if input("Continue anyway? (y/N): ").lower() != 'y':
            sys.exit(1)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

