"""
Cart attribution system for tracking agent-generated sales.
Adds conversation metadata to Shopify carts for order attribution.
"""

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


def add_attribution_to_cart_input(
    cart_input: Dict[str, Any],
    conversation_id: str,
    user_id: str,
    session_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Add attribution metadata to cart creation input.
    This enables tracking which carts were created by the agent.

    Args:
        cart_input: The cart input dict for cartCreate mutation
        conversation_id: Unique conversation/session ID
        user_id: WhatsApp user ID
        session_metadata: Additional session metadata

    Returns:
        Modified cart_input with attribution attributes
    """
    # Shopify Cart API supports custom attributes for attribution
    # These will be preserved when the cart converts to an order

    if "attributes" not in cart_input:
        cart_input["attributes"] = []

    # Add agent attribution attributes
    attribution_attributes = [
        {"key": "_agent_conversation_id", "value": conversation_id},
        {"key": "_agent_user_id", "value": user_id},
        {"key": "_agent_source", "value": "behold_whatsapp_agent"},
        {"key": "_agent_timestamp", "value": str(session_metadata.get("timestamp", ""))} if session_metadata else None,
    ]

    # Filter out None values and add to cart input
    cart_input["attributes"].extend([attr for attr in attribution_attributes if attr])

    logger.info(f"Added attribution to cart for conversation {conversation_id}, user {user_id}")

    return cart_input


def extract_attribution_from_order(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract agent attribution data from Shopify order.
    When a cart converts to an order, custom attributes are preserved.

    Args:
        order_data: Shopify order data from webhook or API

    Returns:
        Dict with attribution metadata (conversation_id, user_id, etc.)
    """
    attribution = {
        "conversation_id": None,
        "user_id": None,
        "source": None,
        "timestamp": None,
        "is_agent_attributed": False
    }

    # Check for custom attributes in order
    custom_attributes = order_data.get("customAttributes", order_data.get("custom_attributes", []))
    note_attributes = order_data.get("noteAttributes", order_data.get("note_attributes", []))

    # Combine both attribute sources
    all_attributes = list(custom_attributes) + list(note_attributes)

    for attr in all_attributes:
        key = attr.get("key", attr.get("name", ""))
        value = attr.get("value", "")

        if key == "_agent_conversation_id":
            attribution["conversation_id"] = value
            attribution["is_agent_attributed"] = True
        elif key == "_agent_user_id":
            attribution["user_id"] = value
        elif key == "_agent_source":
            attribution["source"] = value
        elif key == "_agent_timestamp":
            attribution["timestamp"] = value

    if attribution["is_agent_attributed"]:
        logger.info(f"Order attributed to agent conversation: {attribution['conversation_id']}")

    return attribution


def build_attributed_cart_query(lines: List[Dict[str, Any]], conversation_id: str, user_id: str) -> str:
    """
    Build a GraphQL cart creation mutation with attribution attributes.

    Args:
        lines: Cart line items
        conversation_id: Conversation ID for attribution
        user_id: User ID for attribution

    Returns:
        GraphQL mutation string with attribution
    """
    # This returns the GraphQL query structure that includes attribution
    # The actual execution will be done by the shopify_tool

    return """
    mutation cartCreate($input: CartInput!) {
        cartCreate(input: $input) {
            cart {
                id
                checkoutUrl
                attributes {
                    key
                    value
                }
                lines(first: 10) {
                    edges {
                        node {
                            id
                            quantity
                            merchandise {
                                ... on ProductVariant {
                                    id
                                    title
                                    price {
                                        amount
                                        currencyCode
                                    }
                                    product {
                                        title
                                    }
                                }
                            }
                        }
                    }
                }
                cost {
                    totalAmount {
                        amount
                        currencyCode
                    }
                    subtotalAmount {
                        amount
                        currencyCode
                    }
                }
            }
            userErrors {
                field
                message
            }
        }
    }
    """


def get_cart_with_attribution_query() -> str:
    """
    Get GraphQL query for retrieving cart with attribution attributes.

    Returns:
        GraphQL query string
    """
    return """
    query getCart($id: ID!) {
        cart(id: $id) {
            id
            checkoutUrl
            attributes {
                key
                value
            }
            lines(first: 50) {
                edges {
                    node {
                        id
                        quantity
                        merchandise {
                            ... on ProductVariant {
                                id
                                title
                                price {
                                    amount
                                    currencyCode
                                }
                                product {
                                    title
                                    handle
                                }
                            }
                        }
                    }
                }
            }
            cost {
                totalAmount {
                    amount
                    currencyCode
                }
                subtotalAmount {
                    amount
                    currencyCode
                }
            }
        }
    }
    """


def verify_cart_attribution(cart_data: Dict[str, Any], expected_conversation_id: str) -> bool:
    """
    Verify that a cart has the expected attribution metadata.

    Args:
        cart_data: Cart data from Shopify
        expected_conversation_id: Expected conversation ID

    Returns:
        True if attribution matches, False otherwise
    """
    attributes = cart_data.get("attributes", [])

    for attr in attributes:
        if attr.get("key") == "_agent_conversation_id":
            return attr.get("value") == expected_conversation_id

    return False
