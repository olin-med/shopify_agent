"""
Shopify webhook handler for order completion events.
Receives order/create webhooks and attributes orders to agent conversations.
"""

import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
import os

from .tracking_service import tracking_service
from .cart_attribution import extract_attribution_from_order

logger = logging.getLogger(__name__)


def verify_shopify_webhook(
    data: bytes,
    hmac_header: str,
    secret: str
) -> bool:
    """
    Verify that webhook request is from Shopify.

    Args:
        data: Raw request body
        hmac_header: X-Shopify-Hmac-SHA256 header value
        secret: Shopify webhook secret

    Returns:
        True if verification succeeds, False otherwise
    """
    try:
        # Log debug information for troubleshooting
        logger.debug(f"Webhook verification - Body length: {len(data)} bytes")
        logger.debug(f"Webhook verification - Secret length: {len(secret)} chars")
        logger.debug(f"Webhook verification - Received HMAC: {hmac_header}")

        # Shopify uses HMAC-SHA256 for webhook verification
        digest = hmac.new(
            secret.encode('utf-8'),
            data,
            hashlib.sha256
        ).digest()

        # Shopify sends the HMAC as base64
        import base64
        computed_hmac = base64.b64encode(digest).decode()

        logger.debug(f"Webhook verification - Computed HMAC: {computed_hmac}")

        # Compare HMACs
        is_valid = hmac.compare_digest(computed_hmac, hmac_header)

        if is_valid:
            logger.info("Webhook signature verified successfully")
        else:
            logger.warning(
                f"Webhook signature mismatch!\n"
                f"  Received: {hmac_header}\n"
                f"  Computed: {computed_hmac}\n"
                f"  Body length: {len(data)} bytes\n"
                f"  Secret length: {len(secret)} chars"
            )

        return is_valid
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}", exc_info=True)
        return False


async def handle_order_create_webhook(
    request: Request
) -> Dict[str, Any]:
    """
    Handle Shopify orders/create webhook.

    This webhook is triggered when an order is created (customer completes checkout).
    We extract attribution data from the order to link it back to agent conversations.

    Args:
        request: FastAPI request object

    Returns:
        Response dict
    """
    try:
        # Get raw body for HMAC verification
        body = await request.body()

        # Extract headers directly from request
        x_shopify_hmac_sha256 = request.headers.get("x-shopify-hmac-sha256")
        x_shopify_topic = request.headers.get("x-shopify-topic")

        # Verify webhook authenticity - REQUIRED for security
        webhook_secret = os.getenv("SHOPIFY_WEBHOOK_SECRET")
        if not webhook_secret:
            logger.error("SHOPIFY_WEBHOOK_SECRET not configured - webhook verification required!")
            raise HTTPException(status_code=500, detail="Webhook secret not configured")

        if not x_shopify_hmac_sha256:
            logger.warning("No HMAC signature in webhook request")
            raise HTTPException(status_code=401, detail="Missing webhook signature")

        if not verify_shopify_webhook(body, x_shopify_hmac_sha256, webhook_secret):
            logger.warning(
                f"Invalid webhook signature - rejecting webhook. "
                f"Check that SHOPIFY_WEBHOOK_SECRET matches the secret configured in Shopify Admin. "
                f"Body size: {len(body)} bytes, Header: {x_shopify_hmac_sha256[:20]}..."
            )
            raise HTTPException(
                status_code=401,
                detail="Invalid webhook signature. Verify SHOPIFY_WEBHOOK_SECRET matches Shopify configuration."
            )

        logger.info("Webhook signature verified successfully")

        # Parse order data
        order_data = json.loads(body)

        logger.info(f"Received order webhook: {order_data.get('id', 'unknown')} - Topic: {x_shopify_topic}")

        # Extract attribution from order custom attributes
        attribution = extract_attribution_from_order(order_data)

        if not attribution["is_agent_attributed"]:
            logger.info(f"Order {order_data.get('id')} is not attributed to agent - skipping")
            return {"status": "success", "message": "Order not attributed to agent"}

        # Extract order details
        order_id = str(order_data.get("id", ""))
        conversation_id = attribution["conversation_id"]
        user_id = attribution["user_id"]
        order_number = order_data.get("order_number", order_data.get("name"))

        # Financial details
        total_price = float(order_data.get("total_price", 0))
        subtotal_price = float(order_data.get("subtotal_price", 0))
        total_tax = float(order_data.get("total_tax", 0))
        total_shipping = float(order_data.get("total_shipping_price_set", {}).get("shop_money", {}).get("amount", 0))
        total_discounts = float(order_data.get("total_discounts", 0))
        currency = order_data.get("currency", "BRL")

        # Line items
        line_items = []
        for item in order_data.get("line_items", []):
            line_items.append({
                "product_id": item.get("product_id"),
                "variant_id": item.get("variant_id"),
                "title": item.get("title"),
                "quantity": item.get("quantity"),
                "price": item.get("price"),
                "sku": item.get("sku"),
            })

        # Customer info
        customer_email = order_data.get("email") or order_data.get("customer", {}).get("email")

        # Try to find cart_id from cart_token or note_attributes
        cart_id = None
        cart_token = order_data.get("cart_token")
        if cart_token:
            cart_id = f"gid://shopify/Cart/{cart_token}"

        # Record order in database
        tracking_service.record_order_completion(
            order_id=order_id,
            conversation_id=conversation_id,
            user_id=user_id,
            cart_id=cart_id,
            order_number=order_number,
            total_amount=total_price,
            subtotal_amount=subtotal_price,
            tax_amount=total_tax,
            shipping_amount=total_shipping,
            discount_amount=total_discounts,
            currency=currency,
            items=line_items,
            customer_email=customer_email,
            attribution_data=attribution
        )

        # Mark products as purchased
        for item in line_items:
            product_id = item.get("product_id")
            if product_id:
                tracking_service.mark_product_purchased(conversation_id, str(product_id))

        logger.info(f"Successfully processed order {order_id} - Revenue: {total_price} {currency}")

        return {
            "status": "success",
            "message": f"Order {order_id} attributed to conversation {conversation_id}",
            "order_id": order_id,
            "revenue": total_price
        }

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    except Exception as e:
        logger.error(f"Error processing order webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


async def handle_cart_create_webhook(
    request: Request
) -> Dict[str, Any]:
    """
    Handle Shopify carts/create webhook (if enabled).

    This can track when carts are created, though we already track this
    via the agent's cart creation action.

    Args:
        request: FastAPI request object

    Returns:
        Response dict
    """
    try:
        body = await request.body()

        # Extract headers directly from request
        x_shopify_hmac_sha256 = request.headers.get("x-shopify-hmac-sha256")

        # Verify webhook authenticity - REQUIRED for security
        webhook_secret = os.getenv("SHOPIFY_WEBHOOK_SECRET")
        if not webhook_secret:
            logger.error("SHOPIFY_WEBHOOK_SECRET not configured - webhook verification required!")
            raise HTTPException(status_code=500, detail="Webhook secret not configured")

        if not x_shopify_hmac_sha256:
            logger.warning("No HMAC signature in cart webhook request")
            raise HTTPException(status_code=401, detail="Missing webhook signature")

        if not verify_shopify_webhook(body, x_shopify_hmac_sha256, webhook_secret):
            logger.warning(
                f"Invalid cart webhook signature - rejecting webhook. "
                f"Check that SHOPIFY_WEBHOOK_SECRET matches the secret configured in Shopify Admin. "
                f"Body size: {len(body)} bytes"
            )
            raise HTTPException(
                status_code=401,
                detail="Invalid webhook signature. Verify SHOPIFY_WEBHOOK_SECRET matches Shopify configuration."
            )

        cart_data = json.loads(body)
        logger.info(f"Received cart create webhook: {cart_data.get('id', 'unknown')}")

        # You can add additional cart tracking here if needed
        return {"status": "success", "message": "Cart webhook received"}

    except Exception as e:
        logger.error(f"Error processing cart webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


def setup_shopify_webhooks_guide() -> Dict[str, Any]:
    """
    Return instructions for setting up Shopify webhooks.

    Merchants need to configure webhooks in their Shopify admin:
    Settings -> Notifications -> Webhooks

    Returns:
        Dict with webhook setup instructions
    """
    webhook_url_base = os.getenv("APP_URL", "https://your-app.com")

    return {
        "webhook_setup_instructions": {
            "step_1": "Go to your Shopify Admin: Settings -> Notifications -> Webhooks",
            "step_2": "Click 'Create webhook'",
            "step_3": "Configure the following webhooks:",
            "webhooks": [
                {
                    "event": "Order creation",
                    "format": "JSON",
                    "url": f"{webhook_url_base}/webhooks/shopify/orders/create",
                    "api_version": "2025-01 or latest"
                }
            ],
            "step_4": "Set webhook secret in your .env file",
            "env_var": "SHOPIFY_WEBHOOK_SECRET=your_webhook_secret_from_shopify",
            "verification": "Test the webhook in Shopify admin to verify it's working"
        },
        "webhook_endpoints": {
            "order_create": "/webhooks/shopify/orders/create",
            "cart_create": "/webhooks/shopify/carts/create (optional)"
        },
        "important_notes": [
            "Webhooks enable automatic order attribution to agent conversations",
            "Without webhooks, you won't know when customers complete purchases",
            "The webhook secret is used to verify requests are from Shopify",
            "Make sure your APP_URL environment variable is set correctly"
        ]
    }
