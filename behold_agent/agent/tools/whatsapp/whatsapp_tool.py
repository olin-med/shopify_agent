"""
WhatsApp Tool for Behold Shopify Agent

This tool provides WhatsApp Web.js functionality through the Node.js bridge.
Communicates with the whatsapp-bridge server for sending and receiving messages.
"""

import os
from typing import Dict, Any, Optional
import requests
import logging

logger = logging.getLogger(__name__)


def send_whatsapp_message(to: str, message: str) -> Dict[str, Any]:
    """
    Send a message via WhatsApp Web.js bridge.

    Args:
        to: Recipient phone number (with country code, no + symbol)
        message: Message text to send

    Returns:
        Dict containing success status and response details
    """
    bridge_url = os.getenv("WHATSAPP_BRIDGE_URL", "http://localhost:3001")

    try:
        response = requests.post(
            f"{bridge_url}/send-message",
            json={
                "to": to,
                "message": message
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            logger.info(f"WhatsApp message sent successfully to {to}")

            return {
                "success": True,
                "recipient": result.get("to", to),
                "message": result.get("text", message),
                "bridge_response": result
            }
        elif response.status_code == 503:
            # WhatsApp client not ready
            return {
                "success": False,
                "error": "WhatsApp client is not ready. Please scan QR code first.",
                "recipient": to,
                "status_code": 503
            }
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {"error": response.text}
            return {
                "success": False,
                "error": f"Bridge error: {error_data.get('error', 'Unknown error')}",
                "recipient": to,
                "status_code": response.status_code
            }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": f"Cannot connect to WhatsApp bridge at {bridge_url}. Is the bridge server running?",
            "recipient": to
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Timeout communicating with WhatsApp bridge",
            "recipient": to
        }
    except Exception as e:
        error_msg = f"Unexpected error sending WhatsApp message: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "recipient": to
        }


def get_whatsapp_client_info() -> Dict[str, Any]:
    """
    Get WhatsApp client information from the bridge.

    Returns:
        Dict containing client configuration and status details
    """
    bridge_url = os.getenv("WHATSAPP_BRIDGE_URL", "http://localhost:3001")

    try:
        response = requests.get(f"{bridge_url}/client-info", timeout=10)

        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "bridge_url": bridge_url,
                "client_info": result.get("client_info", {}),
                "bridge_response": result
            }
        elif response.status_code == 503:
            return {
                "success": False,
                "error": "WhatsApp client is not ready",
                "bridge_url": bridge_url,
                "status_code": 503
            }
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {"error": response.text}
            return {
                "success": False,
                "error": f"Bridge error: {error_data.get('error', 'Unknown error')}",
                "bridge_url": bridge_url,
                "status_code": response.status_code
            }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": f"Cannot connect to WhatsApp bridge at {bridge_url}. Is the bridge server running?",
            "bridge_url": bridge_url
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get client info: {str(e)}",
            "bridge_url": bridge_url
        }


def check_whatsapp_status() -> Dict[str, Any]:
    """
    Check WhatsApp bridge and client status.

    Returns:
        Dict containing status information
    """
    bridge_url = os.getenv("WHATSAPP_BRIDGE_URL", "http://localhost:3001")

    try:
        response = requests.get(f"{bridge_url}/health", timeout=10)

        if response.status_code == 200:
            result = response.json()
            return {
                "bridge_status": "connected",
                "bridge_url": bridge_url,
                "whatsapp_ready": result.get("whatsapp_ready", False),
                "has_qr_code": result.get("has_qr_code", False),
                "service": result.get("service", "WhatsApp Bridge"),
                "bridge_response": result
            }
        else:
            return {
                "bridge_status": "error",
                "bridge_url": bridge_url,
                "error": f"Bridge returned status {response.status_code}",
                "response_text": response.text
            }

    except requests.exceptions.ConnectionError:
        return {
            "bridge_status": "disconnected",
            "bridge_url": bridge_url,
            "error": f"Cannot connect to WhatsApp bridge at {bridge_url}. Is the bridge server running?"
        }
    except Exception as e:
        return {
            "bridge_status": "error",
            "bridge_url": bridge_url,
            "error": f"Failed to check bridge status: {str(e)}"
        }


def get_whatsapp_qr_info() -> Dict[str, Any]:
    """
    Get QR code information for WhatsApp authentication.

    Returns:
        Dict containing QR code details and authentication instructions
    """
    bridge_url = os.getenv("WHATSAPP_BRIDGE_URL", "http://localhost:3001")

    status = check_whatsapp_status()

    if status.get("bridge_status") != "connected":
        return {
            "success": False,
            "error": "Bridge is not connected",
            "bridge_status": status
        }

    if status.get("whatsapp_ready"):
        return {
            "success": True,
            "authenticated": True,
            "message": "WhatsApp is already authenticated and ready",
            "qr_url": None
        }
    elif status.get("has_qr_code"):
        return {
            "success": True,
            "authenticated": False,
            "message": "QR code is available for scanning",
            "qr_url": f"{bridge_url}/qr",
            "instructions": [
                f"1. Open your browser and go to: {bridge_url}/qr",
                "2. Open WhatsApp on your phone",
                "3. Go to Settings > Linked Devices",
                "4. Tap 'Link a Device'",
                "5. Scan the QR code displayed on the web page"
            ]
        }
    else:
        return {
            "success": False,
            "authenticated": False,
            "message": "Bridge is starting up, QR code not yet available",
            "qr_url": None
        }


def start_whatsapp_bridge() -> Dict[str, Any]:
    """
    Provides instructions for starting the WhatsApp bridge server.

    Returns:
        Dict containing startup instructions
    """
    bridge_path = "/Users/leostuart/Documents/behold/shopify_agent/whatsapp-bridge"

    return {
        "success": True,
        "message": "WhatsApp bridge startup instructions",
        "bridge_path": bridge_path,
        "instructions": [
            f"1. Navigate to the bridge directory: cd {bridge_path}",
            "2. Install dependencies (if not done): npm install",
            "3. Start the bridge server: npm start",
            "4. The server will start on port 3001 by default",
            "5. Use get_whatsapp_qr_info() to get QR code for authentication"
        ],
        "commands": {
            "install": f"cd {bridge_path} && npm install",
            "start": f"cd {bridge_path} && npm start",
            "dev": f"cd {bridge_path} && npm run dev"
        }
    }