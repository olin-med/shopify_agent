"""
WhatsApp-specific tools for the Behold agent.

These tools allow the agent to generate interactive WhatsApp elements
like buttons and formatted responses while keeping the intelligence in the agent.
"""

import json
from typing import Dict, Any, List, Optional


def create_whatsapp_buttons(
    message_text: str,
    buttons: List[Dict[str, str]],
    header_text: Optional[str] = None,
    footer_text: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a WhatsApp interactive message with buttons.
    
    The agent can use this to generate structured interactive responses
    instead of having formatting logic in the API layer.
    
    Args:
        message_text: Main message body text
        buttons: List of button dicts with 'id' and 'title' keys
        header_text: Optional header text
        footer_text: Optional footer text
        
    Returns:
        Structured response for WhatsApp API
    """
    # Validate buttons
    if len(buttons) > 3:
        buttons = buttons[:3]  # WhatsApp limit
    
    for button in buttons:
        if 'id' not in button or 'title' not in button:
            raise ValueError("Each button must have 'id' and 'title' keys")
        
        # Truncate title if too long
        if len(button['title']) > 20:
            button['title'] = button['title'][:17] + "..."
    
    response = {
        "type": "interactive_buttons",
        "message_text": message_text,
        "buttons": buttons
    }
    
    if header_text:
        response["header_text"] = header_text
    
    if footer_text:
        response["footer_text"] = footer_text
    
    return response


def create_whatsapp_list(
    message_text: str,
    list_items: List[Dict[str, str]],
    button_text: str = "Choose an option",
    header_text: Optional[str] = None,
    footer_text: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a WhatsApp interactive message with a list.
    
    Use this when you have more than 3 options to present to the user.
    
    Args:
        message_text: Main message body text
        list_items: List of items with 'id', 'title', and optional 'description'
        button_text: Text for the list button
        header_text: Optional header text
        footer_text: Optional footer text
        
    Returns:
        Structured response for WhatsApp API
    """
    # Validate list items
    if len(list_items) > 10:
        list_items = list_items[:10]  # WhatsApp limit
    
    for item in list_items:
        if 'id' not in item or 'title' not in item:
            raise ValueError("Each list item must have 'id' and 'title' keys")
        
        # Truncate title if too long
        if len(item['title']) > 24:
            item['title'] = item['title'][:21] + "..."
        
        # Truncate description if present and too long
        if 'description' in item and len(item['description']) > 72:
            item['description'] = item['description'][:69] + "..."
    
    response = {
        "type": "interactive_list",
        "message_text": message_text,
        "list_items": list_items,
        "button_text": button_text
    }
    
    if header_text:
        response["header_text"] = header_text
    
    if footer_text:
        response["footer_text"] = footer_text
    
    return response


def create_product_showcase(
    products: List[Dict[str, Any]], 
    intro_text: str = "Here's what I found for you:",
    max_products: int = 5
) -> Dict[str, Any]:
    """
    Create a formatted product showcase for WhatsApp.
    
    The agent can use this to present products in a mobile-friendly format
    with proper pricing and call-to-action buttons.
    
    Args:
        products: List of product data from Shopify
        intro_text: Introduction text for the product list
        max_products: Maximum number of products to show
        
    Returns:
        Structured response with products and action buttons
    """
    if not products:
        return {
            "type": "text",
            "message_text": "Sorry, I couldn't find any products matching that. Try a different search term! 🔍"
        }
    
    # Limit products
    products_to_show = products[:max_products]
    
    # Build message text
    message_lines = [intro_text, ""]
    
    buttons = []
    
    for i, product_edge in enumerate(products_to_show, 1):
        product = product_edge.get("node", {}) if "node" in product_edge else product_edge
        
        title = product.get("title", "Unknown Product")
        handle = product.get("handle", "")
        
        # Get price
        price_range = product.get("priceRange", {})
        min_price = price_range.get("minVariantPrice", {})
        
        if min_price:
            amount = min_price.get("amount", "0")
            currency = min_price.get("currencyCode", "USD")
            
            # Format price
            try:
                price_float = float(amount)
                if currency == "USD":
                    price_text = f"${price_float:.2f}" if price_float % 1 else f"${int(price_float)}"
                else:
                    price_text = f"{amount} {currency}"
            except:
                price_text = f"{amount} {currency}"
        else:
            price_text = "Price on request"
        
        # Add product line
        message_lines.append(f"{i}. *{title}*")
        message_lines.append(f"   {price_text}")
        
        # Check availability
        available = product.get("availableForSale", True)
        if available:
            message_lines.append("   ✅ In stock")
            
            # Add button for available products
            product_id = product.get("id", "").split("/")[-1] if product.get("id") else str(i)
            buttons.append({
                "id": f"view_product_{product_id}",
                "title": f"View #{i}"
            })
        else:
            message_lines.append("   ❌ Out of stock")
        
        message_lines.append("")  # Empty line
    
    # Add "show more" info if there are more products
    if len(products) > max_products:
        remaining = len(products) - max_products
        message_lines.append(f"_...and {remaining} more! Ask me to show more products._")
    
    message_text = "\n".join(message_lines)
    
    # Add general action buttons
    if len(buttons) < 3:
        buttons.append({
            "id": "search_more",
            "title": "Search More"
        })
    
    if len(buttons) < 3:
        buttons.append({
            "id": "view_cart", 
            "title": "My Cart 🛒"
        })
    
    return create_whatsapp_buttons(
        message_text=message_text,
        buttons=buttons[:3],  # WhatsApp limit
        footer_text="Tap a button to continue shopping! 🛍️"
    )


def create_cart_summary(
    cart_data: Dict[str, Any],
    include_checkout: bool = True
) -> Dict[str, Any]:
    """
    Create a formatted cart summary for WhatsApp.
    
    Args:
        cart_data: Cart data from Shopify
        include_checkout: Whether to include checkout button
        
    Returns:
        Structured response with cart summary and action buttons
    """
    # Check if cart is empty
    lines = cart_data.get("lines", {}).get("edges", [])
    
    if not lines:
        return {
            "type": "text",
            "message_text": (
                "Your cart is empty! 🛒\n\n"
                "Let me help you find something amazing. "
                "What are you looking for today?"
            )
        }
    
    # Build cart summary
    message_lines = ["🛒 *Your Cart*", ""]
    
    total_items = 0
    
    for line_edge in lines:
        line = line_edge.get("node", {})
        quantity = line.get("quantity", 1)
        merchandise = line.get("merchandise", {})
        
        # Product info
        product = merchandise.get("product", {})
        product_title = product.get("title", "Product")
        
        # Price
        price = merchandise.get("price", {})
        amount = price.get("amount", "0")
        currency = price.get("currencyCode", "USD")
        
        try:
            price_float = float(amount)
            if currency == "USD":
                formatted_price = f"${price_float:.2f}" if price_float % 1 else f"${int(price_float)}"
            else:
                formatted_price = f"{amount} {currency}"
        except:
            formatted_price = f"{amount} {currency}"
        
        # Add line item
        message_lines.append(f"• {quantity}x *{product_title}*")
        message_lines.append(f"  {formatted_price} each")
        message_lines.append("")
        
        total_items += quantity
    
    # Add totals
    cost = cart_data.get("cost", {})
    total = cost.get("totalAmount", {})
    
    if total:
        total_amount = total.get("amount", "0")
        currency = total.get("currencyCode", "USD")
        
        try:
            total_float = float(total_amount)
            if currency == "USD":
                formatted_total = f"${total_float:.2f}" if total_float % 1 else f"${int(total_float)}"
            else:
                formatted_total = f"{total_amount} {currency}"
        except:
            formatted_total = f"{total_amount} {currency}"
        
        message_lines.append(f"*Total: {formatted_total}*")
        message_lines.append(f"Items: {total_items}")
    
    message_text = "\n".join(message_lines)
    
    # Create action buttons
    buttons = []
    
    if include_checkout:
        buttons.append({
            "id": "checkout_now",
            "title": "Checkout 💳"
        })
    
    buttons.append({
        "id": "modify_cart",
        "title": "Modify Cart"
    })
    
    buttons.append({
        "id": "continue_shopping",
        "title": "Keep Shopping"
    })
    
    return create_whatsapp_buttons(
        message_text=message_text,
        buttons=buttons[:3],
        header_text="Cart Summary",
        footer_text="What would you like to do next?"
    )


def format_checkout_message(checkout_url: str, cart_total: str = None) -> Dict[str, Any]:
    """
    Create a checkout message with the secure link.
    
    Args:
        checkout_url: Secure Shopify checkout URL
        cart_total: Optional cart total to display
        
    Returns:
        Structured response with checkout link
    """
    message_lines = [
        "🎉 *Ready to complete your purchase!*",
        "",
        "I've created a secure checkout link for you:"
    ]
    
    if cart_total:
        message_lines.insert(1, f"Total: *{cart_total}*")
    
    message_lines.extend([
        "",
        "👆 Tap the link above to complete your order securely through our website.",
        "",
        "✅ Secure payment processing",
        "🚚 Multiple shipping options",
        "📱 Mobile-friendly checkout",
        "",
        "Need help with anything else?"
    ])
    
    return {
        "type": "text",
        "message_text": "\n".join(message_lines),
        "checkout_url": checkout_url  # This will be handled specially by the API layer
    }


def create_greeting_message(user_name: str = None) -> Dict[str, Any]:
    """
    Create a personalized greeting message.
    
    Args:
        user_name: Optional user name for personalization
        
    Returns:
        Structured greeting response with action buttons
    """
    if user_name:
        greeting = f"Hey {user_name}! 👋"
    else:
        greeting = "Hey there! 👋"
    
    message_text = (
        f"{greeting} Welcome to our store!\n\n"
        "I'm your personal shopping assistant. I can help you:\n"
        "• Find products you'll love\n"
        "• Add items to your cart\n"
        "• Calculate shipping costs\n"
        "• Answer any questions\n\n"
        "What are you looking for today?"
    )
    
    buttons = [
        {"id": "browse_popular", "title": "Popular Items 🔥"},
        {"id": "search_products", "title": "Search Products 🔍"},
        {"id": "my_cart", "title": "My Cart 🛒"}
    ]
    
    return create_whatsapp_buttons(
        message_text=message_text,
        buttons=buttons,
        header_text="Welcome! 🛍️",
        footer_text="I'm here to help you find exactly what you need!"
    )

