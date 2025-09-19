"""
WhatsApp Message Formatters

Formats agent responses and Shopify data into WhatsApp-friendly messages
with rich formatting, emojis, and interactive elements.
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class WhatsAppFormatter:
    """
    Formats messages for WhatsApp Business API.
    
    Converts agent responses, product data, and cart information into
    WhatsApp-compatible formats with proper formatting and interactive elements.
    """
    
    def __init__(self):
        """Initialize the formatter."""
        # Character limits for WhatsApp
        self.TEXT_LIMIT = 4096
        self.BUTTON_TITLE_LIMIT = 20
        self.BUTTON_DESCRIPTION_LIMIT = 72
        self.HEADER_LIMIT = 60
        self.FOOTER_LIMIT = 60
        
        # Emoji mappings for different contexts
        self.emojis = {
            "cart": "🛒",
            "product": "🏷️",
            "price": "💰",
            "shipping": "🚚",
            "checkout": "✅",
            "search": "🔍",
            "store": "🏪",
            "heart": "❤️",
            "star": "⭐",
            "fire": "🔥",
            "new": "🆕",
            "sale": "🏷️",
            "free": "🆓",
            "fast": "⚡",
            "location": "📍",
            "phone": "📞",
            "email": "📧",
            "warning": "⚠️",
            "info": "ℹ️",
            "success": "✅",
            "error": "❌"
        }
    
    def _truncate_text(self, text: str, limit: int, suffix: str = "...") -> str:
        """
        Truncate text to fit within character limits.
        
        Args:
            text: Text to truncate
            limit: Character limit
            suffix: Suffix to add if truncated
            
        Returns:
            Truncated text
        """
        if len(text) <= limit:
            return text
        
        truncated = text[:limit - len(suffix)].rsplit(" ", 1)[0]
        return truncated + suffix
    
    def _clean_html(self, text: str) -> str:
        """
        Remove HTML tags and entities from text.
        
        Args:
            text: Text with HTML
            
        Returns:
            Clean text
        """
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        
        # Replace common HTML entities
        replacements = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&nbsp;': ' '
        }
        
        for entity, replacement in replacements.items():
            clean = clean.replace(entity, replacement)
        
        return clean.strip()
    
    def _format_price(self, amount: str, currency: str = "USD") -> str:
        """
        Format price with currency symbol.
        
        Args:
            amount: Price amount as string
            currency: Currency code
            
        Returns:
            Formatted price string
        """
        try:
            price_float = float(amount)
            
            # Currency symbol mapping
            symbols = {
                "USD": "$",
                "EUR": "€",
                "GBP": "£",
                "CAD": "C$",
                "AUD": "A$",
                "JPY": "¥"
            }
            
            symbol = symbols.get(currency, currency)
            
            # Format with 2 decimal places unless it's a whole number
            if price_float == int(price_float):
                return f"{symbol}{int(price_float)}"
            else:
                return f"{symbol}{price_float:.2f}"
                
        except (ValueError, TypeError):
            return f"{amount} {currency}"
    
    def format_product_list(
        self,
        products: List[Dict[str, Any]],
        show_details: bool = True,
        max_products: int = 5
    ) -> str:
        """
        Format a list of products for WhatsApp.
        
        Args:
            products: List of product data from Shopify
            show_details: Whether to show detailed product info
            max_products: Maximum number of products to show
            
        Returns:
            Formatted product list text
        """
        if not products:
            return f"{self.emojis['search']} No products found. Try a different search term!"
        
        # Limit products shown
        products_to_show = products[:max_products]
        
        # Build product list
        lines = [f"{self.emojis['store']} *Found {len(products)} products*\n"]
        
        for i, product_edge in enumerate(products_to_show, 1):
            product = product_edge.get("node", {})
            
            title = product.get("title", "Unknown Product")
            handle = product.get("handle", "")
            
            # Price range
            price_range = product.get("priceRange", {})
            min_price = price_range.get("minVariantPrice", {})
            max_price = price_range.get("maxVariantPrice", {})
            
            price_text = ""
            if min_price and max_price:
                min_amount = min_price.get("amount", "0")
                max_amount = max_price.get("amount", "0")
                currency = min_price.get("currencyCode", "USD")
                
                if min_amount == max_amount:
                    price_text = self._format_price(min_amount, currency)
                else:
                    price_text = f"{self._format_price(min_amount, currency)} - {self._format_price(max_amount, currency)}"
            
            # Product line
            product_line = f"{i}. *{title}*"
            if price_text:
                product_line += f" - {price_text}"
            
            lines.append(product_line)
            
            # Add description if showing details
            if show_details:
                description = product.get("description", "")
                if description:
                    clean_desc = self._clean_html(description)
                    short_desc = self._truncate_text(clean_desc, 100)
                    lines.append(f"   {short_desc}")
                
                # Availability
                available = product.get("availableForSale", False)
                if available:
                    lines.append(f"   {self.emojis['success']} In Stock")
                else:
                    lines.append(f"   {self.emojis['warning']} Out of Stock")
            
            lines.append("")  # Empty line between products
        
        # Add "view more" hint if there are more products
        if len(products) > max_products:
            remaining = len(products) - max_products
            lines.append(f"_{remaining} more products available. Ask me to show more!_")
        
        return "\n".join(lines)
    
    def format_product_details(self, product: Dict[str, Any]) -> str:
        """
        Format detailed product information.
        
        Args:
            product: Product data from Shopify
            
        Returns:
            Formatted product details
        """
        title = product.get("title", "Unknown Product")
        description = product.get("description", "")
        vendor = product.get("vendor", "")
        product_type = product.get("productType", "")
        tags = product.get("tags", [])
        
        # Price information
        price_range = product.get("priceRange", {})
        min_price = price_range.get("minVariantPrice", {})
        max_price = price_range.get("maxVariantPrice", {})
        
        lines = [f"{self.emojis['product']} *{title}*\n"]
        
        # Price
        if min_price and max_price:
            min_amount = min_price.get("amount", "0")
            max_amount = max_price.get("amount", "0")
            currency = min_price.get("currencyCode", "USD")
            
            if min_amount == max_amount:
                price_text = self._format_price(min_amount, currency)
            else:
                price_text = f"{self._format_price(min_amount, currency)} - {self._format_price(max_amount, currency)}"
            
            lines.append(f"{self.emojis['price']} *Price:* {price_text}")
        
        # Vendor and type
        if vendor:
            lines.append(f"{self.emojis['store']} *Brand:* {vendor}")
        
        if product_type:
            lines.append(f"{self.emojis['info']} *Category:* {product_type}")
        
        # Description
        if description:
            clean_desc = self._clean_html(description)
            formatted_desc = self._truncate_text(clean_desc, 500)
            lines.append(f"\n*Description:*\n{formatted_desc}")
        
        # Tags
        if tags and len(tags) > 0:
            tag_text = " • ".join(tags[:5])  # Show first 5 tags
            lines.append(f"\n*Tags:* {tag_text}")
        
        # Availability
        available = product.get("availableForSale", False)
        if available:
            lines.append(f"\n{self.emojis['success']} *In Stock - Ready to ship!*")
        else:
            lines.append(f"\n{self.emojis['warning']} *Currently out of stock*")
        
        return "\n".join(lines)
    
    def format_cart_summary(self, cart_data: Dict[str, Any]) -> str:
        """
        Format cart summary for WhatsApp.
        
        Args:
            cart_data: Cart data from Shopify
            
        Returns:
            Formatted cart summary
        """
        lines = [f"{self.emojis['cart']} *Your Shopping Cart*\n"]
        
        # Get cart lines
        cart_lines = cart_data.get("lines", {}).get("edges", [])
        
        if not cart_lines:
            return f"{self.emojis['cart']} Your cart is empty. Let me help you find some great products!"
        
        total_items = 0
        
        # Format each line item
        for line_edge in cart_lines:
            line = line_edge.get("node", {})
            quantity = line.get("quantity", 1)
            merchandise = line.get("merchandise", {})
            
            # Product info
            product = merchandise.get("product", {})
            product_title = product.get("title", "Product")
            variant_title = merchandise.get("title", "")
            
            # Price
            price = merchandise.get("price", {})
            amount = price.get("amount", "0")
            currency = price.get("currencyCode", "USD")
            formatted_price = self._format_price(amount, currency)
            
            # Line total
            try:
                line_total = float(amount) * quantity
                formatted_total = self._format_price(str(line_total), currency)
            except (ValueError, TypeError):
                formatted_total = f"{quantity} × {formatted_price}"
            
            # Format line item
            item_text = f"• {quantity}× *{product_title}*"
            if variant_title and variant_title != "Default Title":
                item_text += f" ({variant_title})"
            
            item_text += f"\n  {formatted_price} each = {formatted_total}"
            
            lines.append(item_text)
            total_items += quantity
        
        lines.append("")  # Empty line before totals
        
        # Cart totals
        cost = cart_data.get("cost", {})
        subtotal = cost.get("subtotalAmount", {})
        total = cost.get("totalAmount", {})
        
        if subtotal:
            subtotal_amount = subtotal.get("amount", "0")
            currency = subtotal.get("currencyCode", "USD")
            lines.append(f"*Subtotal:* {self._format_price(subtotal_amount, currency)}")
        
        if total:
            total_amount = total.get("amount", "0")
            currency = total.get("currencyCode", "USD")
            lines.append(f"*Total:* {self._format_price(total_amount, currency)}")
        
        lines.append(f"\n*Items in cart:* {total_items}")
        
        return "\n".join(lines)
    
    def format_shipping_estimate(
        self,
        shipping_data: Dict[str, Any],
        address: Dict[str, str]
    ) -> str:
        """
        Format shipping estimate information.
        
        Args:
            shipping_data: Shipping cost data from Shopify
            address: Shipping address
            
        Returns:
            Formatted shipping estimate
        """
        lines = [f"{self.emojis['shipping']} *Shipping Estimate*\n"]
        
        # Address
        city = address.get("city", "")
        province = address.get("province", "")
        country = address.get("country", "")
        
        if city and province:
            lines.append(f"{self.emojis['location']} *Shipping to:* {city}, {province}, {country}")
        elif country:
            lines.append(f"{self.emojis['location']} *Shipping to:* {country}")
        
        lines.append("")
        
        # Shipping costs
        cost = shipping_data.get("cost", {})
        
        # Subtotal
        subtotal = cost.get("subtotalAmount", {})
        if subtotal:
            amount = subtotal.get("amount", "0")
            currency = subtotal.get("currencyCode", "USD")
            lines.append(f"Subtotal: {self._format_price(amount, currency)}")
        
        # Tax
        tax = cost.get("totalTaxAmount", {})
        if tax and tax.get("amount", "0") != "0":
            amount = tax.get("amount", "0")
            currency = tax.get("currencyCode", "USD")
            lines.append(f"Tax: {self._format_price(amount, currency)}")
        
        # Duty
        duty = cost.get("totalDutyAmount", {})
        if duty and duty.get("amount", "0") != "0":
            amount = duty.get("amount", "0")
            currency = duty.get("currencyCode", "USD")
            lines.append(f"Duty: {self._format_price(amount, currency)}")
        
        # Total
        total = cost.get("totalAmount", {})
        if total:
            amount = total.get("amount", "0")
            currency = total.get("currencyCode", "USD")
            lines.append(f"\n*Total: {self._format_price(amount, currency)}*")
        
        lines.append(f"\n{self.emojis['fast']} _Standard shipping (5-7 business days)_")
        
        return "\n".join(lines)
    
    def format_store_policies(self, policies: Dict[str, Any]) -> str:
        """
        Format store policies information.
        
        Args:
            policies: Store policies data from Shopify
            
        Returns:
            Formatted policies text
        """
        lines = [f"{self.emojis['store']} *Store Information & Policies*\n"]
        
        # Store name and description
        store_name = policies.get("name", "Our Store")
        description = policies.get("description", "")
        
        lines.append(f"*{store_name}*")
        
        if description:
            clean_desc = self._clean_html(description)
            short_desc = self._truncate_text(clean_desc, 200)
            lines.append(f"{short_desc}\n")
        
        # Shipping Policy
        shipping_policy = policies.get("shippingPolicy")
        if shipping_policy:
            title = shipping_policy.get("title", "Shipping Policy")
            body = shipping_policy.get("body", "")
            
            lines.append(f"{self.emojis['shipping']} *{title}*")
            if body:
                clean_body = self._clean_html(body)
                short_body = self._truncate_text(clean_body, 300)
                lines.append(f"{short_body}\n")
        
        # Return Policy
        refund_policy = policies.get("refundPolicy")
        if refund_policy:
            title = refund_policy.get("title", "Return Policy")
            body = refund_policy.get("body", "")
            
            lines.append(f"{self.emojis['info']} *{title}*")
            if body:
                clean_body = self._clean_html(body)
                short_body = self._truncate_text(clean_body, 300)
                lines.append(f"{short_body}\n")
        
        # Privacy Policy
        privacy_policy = policies.get("privacyPolicy")
        if privacy_policy:
            title = privacy_policy.get("title", "Privacy Policy")
            lines.append(f"{self.emojis['info']} *{title}*")
            lines.append("We protect your privacy and personal information.\n")
        
        return "\n".join(lines)
    
    def format_agent_response(self, response: str) -> str:
        """
        Format general agent response for WhatsApp.
        
        Args:
            response: Agent response text
            
        Returns:
            Formatted response
        """
        # Clean HTML if present
        clean_response = self._clean_html(response)
        
        # Truncate if too long
        formatted = self._truncate_text(clean_response, self.TEXT_LIMIT - 100)
        
        # Add some emojis for common patterns
        patterns = [
            (r'\b(hello|hi|hey)\b', f'{self.emojis["heart"]} '),
            (r'\b(thank you|thanks)\b', f'{self.emojis["heart"]} '),
            (r'\b(sale|discount|deal)\b', f'{self.emojis["sale"]} '),
            (r'\b(new|latest)\b', f'{self.emojis["new"]} '),
            (r'\b(fast|quick|speed)\b', f'{self.emojis["fast"]} '),
            (r'\b(free)\b', f'{self.emojis["free"]} '),
        ]
        
        for pattern, emoji in patterns:
            formatted = re.sub(pattern, emoji + r'\g<0>', formatted, flags=re.IGNORECASE)
        
        return formatted
    
    def create_product_buttons(
        self,
        products: List[Dict[str, Any]],
        max_buttons: int = 3
    ) -> List[Dict[str, str]]:
        """
        Create interactive buttons for products.
        
        Args:
            products: List of product data
            max_buttons: Maximum number of buttons to create
            
        Returns:
            List of button dictionaries
        """
        buttons = []
        
        for i, product_edge in enumerate(products[:max_buttons]):
            product = product_edge.get("node", {})
            product_id = product.get("id", "")
            title = product.get("title", f"Product {i+1}")
            
            # Truncate title for button
            button_title = self._truncate_text(title, self.BUTTON_TITLE_LIMIT, "")
            
            buttons.append({
                "id": f"view_product_{product_id}",
                "title": f"View {button_title}"
            })
        
        return buttons
    
    def create_cart_buttons(self, has_items: bool = True) -> List[Dict[str, str]]:
        """
        Create interactive buttons for cart actions.
        
        Args:
            has_items: Whether cart has items
            
        Returns:
            List of button dictionaries
        """
        if has_items:
            return [
                {"id": "checkout_cart", "title": f"{self.emojis['checkout']} Checkout"},
                {"id": "modify_cart", "title": "Modify Cart"},
                {"id": "continue_shopping", "title": "Keep Shopping"}
            ]
        else:
            return [
                {"id": "browse_products", "title": "Browse Products"},
                {"id": "search_products", "title": "Search Products"}
            ]
    
    def create_main_menu_buttons(self) -> List[Dict[str, str]]:
        """
        Create main menu buttons.
        
        Returns:
            List of button dictionaries
        """
        return [
            {"id": "browse_products", "title": f"{self.emojis['search']} Browse"},
            {"id": "view_cart", "title": f"{self.emojis['cart']} My Cart"},
            {"id": "store_info", "title": f"{self.emojis['store']} Store Info"}
        ]
    
    def format_error_message(self, error: str) -> str:
        """
        Format error message for WhatsApp.
        
        Args:
            error: Error message
            
        Returns:
            Formatted error message
        """
        return f"{self.emojis['error']} Sorry, something went wrong: {error}\n\nPlease try again or contact support if the issue persists."
    
    def format_success_message(self, message: str) -> str:
        """
        Format success message for WhatsApp.
        
        Args:
            message: Success message
            
        Returns:
            Formatted success message
        """
        return f"{self.emojis['success']} {message}"

