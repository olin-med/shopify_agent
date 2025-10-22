import os
import subprocess
import json
import requests
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def validate_graphql_with_mcp(query: str, api: str = "admin", version: str = "2025-07") -> Dict[str, Any]:
    """
    Validates a GraphQL query using Shopify MCP server.
    
    Args:
        query (str): The GraphQL query to validate
        api (str): The API to validate against (default: "admin")
        version (str): The API version to validate against

    Returns:
        Dict[str, Any]: Validation result with status and details
    """
    try:
        # Prepare the MCP command to validate GraphQL
        mcp_command = [
            "npx", "-y", "@shopify/dev-mcp@latest"
        ]
        
        # Create the validation request
        validation_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "validate_graphql_codeblocks",
                "arguments": {
                    "codeblocks": [query],
                    "api": api,
                    "version": version
                }
            }
        }
        
        # Run the MCP server validation
        result = subprocess.run(
            mcp_command,
            input=json.dumps(validation_request),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                if "result" in response:
                    return {
                        "status": "success",
                        "validation_result": response["result"]
                    }
                else:
                    return {
                        "status": "error",
                        "error_message": f"Unexpected MCP response format: {response}"
                    }
            except json.JSONDecodeError as e:
                return {
                    "status": "error", 
                    "error_message": f"Failed to parse MCP response: {e}"
                }
        else:
            return {
                "status": "error",
                "error_message": f"MCP validation failed: {result.stderr}"
            }
            
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error_message": "GraphQL validation timed out"
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Validation error: {str(e)}"
        }


def introspect_graphql_schema(search_term: str, api: str = "admin", version: str = "2025-07", 
                            filter_types: List[str] = ["all"]) -> Dict[str, Any]:
    """
    Introspects Shopify GraphQL schema using MCP server.
    
    Args:
        search_term (str): Term to search for in the schema
        api (str): The API to introspect (default: "admin")
        version (str): The API version to introspect
        filter_types (List[str]): Types to filter ["all", "types", "queries", "mutations"]
    
    Returns:
        Dict[str, Any]: Schema introspection result
    """
    try:
        # Prepare the MCP command
        mcp_command = [
            "npx", "-y", "@shopify/dev-mcp@latest"
        ]
        
        # Create the introspection request
        introspection_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "introspect_graphql_schema",
                "arguments": {
                    "query": search_term,
                    "api": api,
                    "version": version,
                    "filter": filter_types
                }
            }
        }
        
        # Run the MCP server introspection
        result = subprocess.run(
            mcp_command,
            input=json.dumps(introspection_request),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                if "result" in response:
                    return {
                        "status": "success",
                        "schema_info": response["result"]
                    }
                else:
                    return {
                        "status": "error",
                        "error_message": f"Unexpected MCP response format: {response}"
                    }
            except json.JSONDecodeError as e:
                return {
                    "status": "error",
                    "error_message": f"Failed to parse MCP response: {e}"
                }
        else:
            return {
                "status": "error",
                "error_message": f"MCP introspection failed: {result.stderr}"
            }
            
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error_message": "Schema introspection timed out"
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Introspection error: {str(e)}"
        }


def fetch_shopify_graphql(
    query: str,
    variables: Optional[Dict[str, Any]] = None,
    shop: Optional[str] = None,
    api_version: Optional[str] = None,
    access_token: Optional[str] = None,
    validate_query: bool = True
) -> Dict[str, Any]:
    """
    Fetches data from Shopify GraphQL API endpoint with optional validation.
    
    Args:
        query (str): The GraphQL query string
        variables (Optional[Dict[str, Any]]): GraphQL variables if needed
        shop (Optional[str]): The shop name (without .myshopify.com). If not provided, uses SHOPIFY_STORE from .env
        api_version (Optional[str]): The API version (e.g., "2024-01"). If not provided, uses SHOPIFY_API_VERSION from .env
        access_token (Optional[str]): The Shopify access token. If not provided, uses SHOPIFY_ADMIN_TOKEN from .env
        validate_query (bool): Whether to validate the query using Shopify MCP before executing (default: True)
    
    Returns:
        Dict[str, Any]: Response data or error information
    """
    # Get values from environment variables if not provided
    shop = shop or os.getenv("SHOPIFY_STORE")
    api_version = api_version or os.getenv("SHOPIFY_API_VERSION", "2025-07")
    access_token = access_token or os.getenv("SHOPIFY_ADMIN_TOKEN")
    
    # Validate required parameters
    if not shop:
        return {
            "status": "error",
            "error_message": "Shop name is required. Set SHOPIFY_STORE in .env file or pass as parameter."
        }
    
    if not access_token:
        return {
            "status": "error",
            "error_message": "Access token is required. Set SHOPIFY_ADMIN_TOKEN in .env file or pass as parameter."
        }
    
    # Validate GraphQL query using MCP if requested
    if validate_query:
        validation_result = validate_graphql_with_mcp(query, "admin", api_version)
        if validation_result["status"] == "error":
            return {
                "status": "validation_error",
                "error_message": f"GraphQL validation failed: {validation_result['error_message']}",
                "validation_details": validation_result
            }
        
        # Check if validation found issues with the query
        validation_info = validation_result.get("validation_result", {})
        if validation_info.get("isError", False):
            return {
                "status": "validation_error", 
                "error_message": "GraphQL query validation failed",
                "validation_details": validation_info.get("content", [{}])[0].get("text", "Unknown validation error")
            }
    
    url = f"https://{shop}.myshopify.com/admin/api/{api_version}/graphql.json"
    
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token
    }
    
    payload = {
        "query": query
    }
    
    if variables:
        payload["variables"] = variables
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        if "errors" in data:
            return {
                "status": "error",
                "error_message": f"GraphQL errors: {data['errors']}"
            }
        
        return {
            "status": "success",
            "data": data.get("data", {}),
            "extensions": data.get("extensions", {})
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "error_message": f"Request failed: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Unexpected error: {str(e)}"
        }


def fetch_shopify_storefront_graphql(
    query: str,
    variables: Optional[Dict[str, Any]] = None,
    shop: Optional[str] = None,
    api_version: Optional[str] = None,
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetches data from Shopify Storefront API endpoint.
    
    Args:
        query (str): The GraphQL query string
        variables (Optional[Dict[str, Any]]): GraphQL variables if needed
        shop (Optional[str]): The shop name (without .myshopify.com). If not provided, uses SHOPIFY_STORE from .env
        api_version (Optional[str]): The API version (e.g., "2024-01"). If not provided, uses SHOPIFY_API_VERSION from .env
        access_token (Optional[str]): The Shopify Storefront access token. If not provided, uses SHOPIFY_STOREFRONT_TOKEN from .env
    
    Returns:
        Dict[str, Any]: Response data or error information
    """
    # Get values from environment variables if not provided
    shop = shop or os.getenv("SHOPIFY_STORE")
    api_version = api_version or os.getenv("SHOPIFY_API_VERSION", "2025-07")
    access_token = access_token or os.getenv("SHOPIFY_STOREFRONT_TOKEN")
    
    # Validate required parameters
    if not shop:
        return {
            "status": "error",
            "error_message": "Shop name is required. Set SHOPIFY_STORE in .env file or pass as parameter."
        }
    
    if not access_token:
        return {
            "status": "error",
            "error_message": "Storefront access token is required. Set SHOPIFY_STOREFRONT_TOKEN in .env file or pass as parameter."
        }
    
    url = f"https://{shop}.myshopify.com/api/{api_version}/graphql.json"
    
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Storefront-Access-Token": access_token
    }
    
    payload = {
        "query": query
    }
    
    if variables:
        payload["variables"] = variables
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        if "errors" in data:
            return {
                "status": "error",
                "error_message": f"GraphQL errors: {data['errors']}"
            }
        
        return {
            "status": "success",
            "data": data.get("data", {}),
            "extensions": data.get("extensions", {})
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "error_message": f"Request failed: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Unexpected error: {str(e)}"
        }


def create_cart(
    lines: List[Dict[str, Any]],
    shop: Optional[str] = None,
    api_version: Optional[str] = None,
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a new cart with specified line items.
    
    Args:
        lines (List[Dict[str, Any]]): List of cart line items with 'merchandiseId' and 'quantity'
        shop (Optional[str]): The shop name (without .myshopify.com)
        api_version (Optional[str]): The API version
        access_token (Optional[str]): The Shopify Storefront access token
    
    Returns:
        Dict[str, Any]: Cart creation result with cart ID and checkout URL
    """
    # Input validation
    if not lines or not isinstance(lines, list):
        return {
            "status": "error",
            "error_message": "I need at least one product to create a cart. What would you like to add?"
        }
    
    # Validate each line item
    for i, line in enumerate(lines):
        if not isinstance(line, dict):
            return {
                "status": "error",
                "error_message": f"Invalid product information for item {i+1}. Please check the product details."
            }
        
        if not line.get('merchandiseId'):
            return {
                "status": "error", 
                "error_message": f"Missing product variant ID for item {i+1}. Please select a specific product variant."
            }
        
        quantity = line.get('quantity', 1)
        if not isinstance(quantity, int) or quantity < 1:
            return {
                "status": "error",
                "error_message": f"Invalid quantity for item {i+1}. Quantity must be a positive number."
            }
        
        if quantity > 100:  # Reasonable limit
            return {
                "status": "error",
                "error_message": f"Quantity too high for item {i+1}. Maximum 100 items per product allowed."
            }
    query = """
    mutation cartCreate($input: CartInput!) {
        cartCreate(input: $input) {
            cart {
                id
                checkoutUrl
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
                                        id
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
            userErrors {
                field
                message
            }
        }
    }
    """
    
    variables = {
        "input": {
            "lines": lines
        }
    }
    
    result = fetch_shopify_storefront_graphql(query, variables, shop, api_version, access_token)
    
    if result["status"] == "success":
        cart_data = result["data"].get("cartCreate", {})
        cart = cart_data.get("cart")
        user_errors = cart_data.get("userErrors", [])
        
        if user_errors:
            return {
                "status": "error",
                "error_message": f"Cart creation errors: {user_errors}"
            }
        
        return {
            "status": "success",
            "cart_id": cart.get("id"),
            "checkout_url": cart.get("checkoutUrl"),
            "cart_data": cart
        }
    
    return result


def modify_cart(
    cart_id: str,
    lines: List[Dict[str, Any]],
    shop: Optional[str] = None,
    api_version: Optional[str] = None,
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Modifies an existing cart by adding/updating/removing line items.
    
    Args:
        cart_id (str): The ID of the cart to modify
        lines (List[Dict[str, Any]]): List of cart line operations with 'id', 'merchandiseId', and 'quantity'
        shop (Optional[str]): The shop name (without .myshopify.com)
        api_version (Optional[str]): The API version
        access_token (Optional[str]): The Shopify Storefront access token
    
    Returns:
        Dict[str, Any]: Cart modification result
    """
    query = """
    mutation cartLinesUpdate($cartId: ID!, $lines: [CartLineUpdateInput!]!) {
        cartLinesUpdate(cartId: $cartId, lines: $lines) {
            cart {
                id
                checkoutUrl
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
                                        id
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
            userErrors {
                field
                message
            }
        }
    }
    """
    
    variables = {
        "cartId": cart_id,
        "lines": lines
    }
    
    result = fetch_shopify_storefront_graphql(query, variables, shop, api_version, access_token)
    
    if result["status"] == "success":
        cart_data = result["data"].get("cartLinesUpdate", {})
        cart = cart_data.get("cart")
        user_errors = cart_data.get("userErrors", [])
        
        if user_errors:
            return {
                "status": "error",
                "error_message": f"Cart modification errors: {user_errors}"
            }
        
        return {
            "status": "success",
            "cart_id": cart.get("id"),
            "checkout_url": cart.get("checkoutUrl"),
            "cart_data": cart
        }
    
    return result


def get_cart(
    cart_id: str,
    shop: Optional[str] = None,
    api_version: Optional[str] = None,
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieves cart information by cart ID.
    
    Args:
        cart_id (str): The ID of the cart to retrieve
        shop (Optional[str]): The shop name (without .myshopify.com)
        api_version (Optional[str]): The API version
        access_token (Optional[str]): The Shopify Storefront access token
    
    Returns:
        Dict[str, Any]: Cart information
    """
    query = """
    query getCart($id: ID!) {
        cart(id: $id) {
            id
            checkoutUrl
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
                                    id
                                    title
                                    handle
                                    images(first: 1) {
                                        edges {
                                            node {
                                                url
                                                altText
                                            }
                                        }
                                    }
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
    
    variables = {
        "id": cart_id
    }
    
    result = fetch_shopify_storefront_graphql(query, variables, shop, api_version, access_token)
    
    if result["status"] == "success":
        cart = result["data"].get("cart")
        if cart:
            return {
                "status": "success",
                "cart_data": cart
            }
        else:
            return {
                "status": "error",
                "error_message": "Cart not found"
            }
    
    return result


def create_checkout(
    cart_id: str,
    shop: Optional[str] = None,
    api_version: Optional[str] = None,
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a checkout from an existing cart.
    
    Args:
        cart_id (str): The ID of the cart to create checkout from
        shop (Optional[str]): The shop name (without .myshopify.com)
        api_version (Optional[str]): The API version
        access_token (Optional[str]): The Shopify Storefront access token
    
    Returns:
        Dict[str, Any]: Checkout creation result with checkout URL
    """
    # First get the cart to ensure it exists and get checkout URL
    cart_result = get_cart(cart_id, shop, api_version, access_token)
    
    if cart_result["status"] == "success":
        cart_data = cart_result["cart_data"]
        checkout_url = cart_data.get("checkoutUrl")
        
        if checkout_url:
            return {
                "status": "success",
                "checkout_url": checkout_url,
                "cart_data": cart_data
            }
        else:
            return {
                "status": "error",
                "error_message": "No checkout URL available for this cart"
            }
    
    return cart_result


def get_store_policies(
    shop: Optional[str] = None,
    api_version: Optional[str] = None,
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieves store policies including shipping, return, and privacy policies.
    
    Args:
        shop (Optional[str]): The shop name (without .myshopify.com)
        api_version (Optional[str]): The API version
        access_token (Optional[str]): The Shopify Storefront access token
    
    Returns:
        Dict[str, Any]: Store policies information
    """
    query = """
    query getShopPolicies {
        shop {
            name
            description
            shippingPolicy {
                body
                handle
                id
                title
                url
            }
            refundPolicy {
                body
                handle
                id
                title
                url
            }
            privacyPolicy {
                body
                handle
                id
                title
                url
            }
            termsOfService {
                body
                handle
                id
                title
                url
            }
        }
    }
    """
    
    result = fetch_shopify_storefront_graphql(query, None, shop, api_version, access_token)
    
    if result["status"] == "success":
        shop_data = result["data"].get("shop", {})
        return {
            "status": "success",
            "policies": shop_data
        }
    
    return result


def search_products(
    query: str,
    first: int = 20,
    shop: Optional[str] = None,
    api_version: Optional[str] = None,
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Searches for products using a query string.
    
    Args:
        query (str): Search query string
        first (int): Number of products to return (default: 20)
        shop (Optional[str]): The shop name (without .myshopify.com)
        api_version (Optional[str]): The API version
        access_token (Optional[str]): The Shopify Storefront access token
    
    Returns:
        Dict[str, Any]: Search results with products
    """
    # Input validation
    if not query or not isinstance(query, str):
        return {
            "status": "error",
            "error_message": "Please tell me what you're looking for so I can find the perfect products for you!"
        }
    
    # Clean and validate search query
    cleaned_query = query.strip()
    if len(cleaned_query) < 2:
        return {
            "status": "error",
            "error_message": "Please provide at least 2 characters to search for products."
        }
    
    if len(cleaned_query) > 200:  # Reasonable limit
        cleaned_query = cleaned_query[:200]
    
    # Validate and limit first parameter
    if not isinstance(first, int) or first < 1:
        first = 20
    elif first > 100:  # Reasonable limit
        first = 100
    graphql_query = """
    query searchProducts($query: String!, $first: Int!) {
        products(first: $first, query: $query) {
            edges {
                node {
                    id
                    title
                    handle
                    description
                    descriptionHtml
                    availableForSale
                    createdAt
                    updatedAt
                    tags
                    productType
                    vendor
                    priceRange {
                        minVariantPrice {
                            amount
                            currencyCode
                        }
                        maxVariantPrice {
                            amount
                            currencyCode
                        }
                    }
                    images(first: 5) {
                        edges {
                            node {
                                id
                                url
                                altText
                                width
                                height
                            }
                        }
                    }
                    variants(first: 10) {
                        edges {
                            node {
                                id
                                title
                                availableForSale
                                price {
                                    amount
                                    currencyCode
                                }
                                compareAtPrice {
                                    amount
                                    currencyCode
                                }
                                selectedOptions {
                                    name
                                    value
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    variables = {
        "query": cleaned_query,
        "first": first
    }
    
    result = fetch_shopify_storefront_graphql(graphql_query, variables, shop, api_version, access_token)
    
    if result["status"] == "success":
        products_data = result["data"].get("products", {})
        products = products_data.get("edges", [])
        
        # Provide helpful feedback when no products found
        if not products:
            return {
                "status": "success",
                "products": [],
                "search_query": cleaned_query,
                "message": f"I couldn't find any products matching '{cleaned_query}'. Try different keywords or browse our categories!"
            }
        
        return {
            "status": "success", 
            "products": products,
            "search_query": cleaned_query,
            "total_found": len(products)
        }
    
    # Handle search failures gracefully
    error_msg = result.get("error_message", "Search temporarily unavailable")
    return {
        "status": "error",
        "error_message": f"I'm having trouble searching right now. Please try again in a moment! ({error_msg})"
    }


def calculate_shipping_estimate(
    cart_id: str,
    address: Dict[str, str],
    shop: Optional[str] = None,
    api_version: Optional[str] = None,
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculates shipping estimate by creating a temporary checkout to get shipping rates.
    This is the proper way to get shipping estimates in Shopify.
    
    Args:
        cart_id (str): The ID of the cart
        address (Dict[str, str]): Address information with 'country', 'province', 'city', 'zip'
        shop (Optional[str]): The shop name (without .myshopify.com)
        api_version (Optional[str]): The API version
        access_token (Optional[str]): The Shopify Storefront access token
    
    Returns:
        Dict[str, Any]: Shipping estimate with available shipping rates
    """
    # Validate required address fields
    required_fields = ['country']
    missing_fields = [field for field in required_fields if not address.get(field)]
    if missing_fields:
        return {
            "status": "error",
            "error_message": f"I need a country to calculate shipping rates. Could you please provide your country?"
        }
    
    # First check if cart exists and has items
    cart_check = get_cart(cart_id, shop, api_version, access_token)
    if cart_check["status"] != "success":
        return {
            "status": "error", 
            "error_message": "I couldn't find your cart. Please add some items first, then I can calculate shipping costs."
        }
    
    cart_data = cart_check.get("cart_data", {})
    lines = cart_data.get("lines", {}).get("edges", [])
    if not lines:
        return {
            "status": "error",
            "error_message": "Your cart is empty. Please add some items first, then I can calculate shipping costs."
        }
    
    # Use the proper approach: get available shipping rates through checkout
    # First, set the shipping address on the cart
    address_query = """
    mutation cartShippingAddressUpdate($cartId: ID!, $address: MailingAddressInput!) {
        cartShippingAddressUpdate(cartId: $cartId, address: $address) {
            cart {
                id
                checkoutUrl
                deliveryGroups(first: 5) {
                    edges {
                        node {
                            id
                            deliveryOptions {
                                estimatedCost {
                                    amount
                                    currencyCode
                                }
                                handle
                                title
                                description
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
                    totalTaxAmount {
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
    
    variables = {
        "cartId": cart_id,
        "address": address
    }
    
    try:
        result = fetch_shopify_storefront_graphql(address_query, variables, shop, api_version, access_token)
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"I'm having trouble connecting to calculate shipping rates. Please try again in a moment!"
        }
    
    if result["status"] == "success":
        cart_update_data = result["data"].get("cartShippingAddressUpdate", {})
        updated_cart = cart_update_data.get("cart")
        user_errors = cart_update_data.get("userErrors", [])
        
        if user_errors:
            # Check if it's an address validation error
            address_errors = [err for err in user_errors if 'address' in err.get('field', '').lower()]
            if address_errors:
                return {
                    "status": "error",
                    "error_message": "I need a more complete address to calculate accurate shipping rates. Could you provide your city and postal code?"
                }
            return {
                "status": "error",
                "error_message": f"I'm having trouble calculating shipping for this address: {user_errors[0].get('message', 'Address validation failed')}"
            }
        
        if not updated_cart:
            return {
                "status": "error",
                "error_message": "I couldn't update the cart with your address. Please try again!"
            }
        
        # Extract delivery options/shipping rates
        delivery_groups = updated_cart.get("deliveryGroups", {}).get("edges", [])
        shipping_options = []
        
        for group_edge in delivery_groups:
            group = group_edge.get("node", {})
            delivery_options = group.get("deliveryOptions", [])
            
            for option in delivery_options:
                estimated_cost = option.get("estimatedCost", {})
                if estimated_cost:
                    shipping_options.append({
                        "title": option.get("title", "Standard Shipping"),
                        "description": option.get("description", ""),
                        "handle": option.get("handle", ""),
                        "cost": estimated_cost
                    })
        
        # If no delivery options available, try to get cost from cart totals
        cart_cost = updated_cart.get("cost", {})
        
        if not shipping_options and cart_cost:
            # Estimate shipping based on total vs subtotal difference
            total = float(cart_cost.get("totalAmount", {}).get("amount", 0))
            subtotal = float(cart_cost.get("subtotalAmount", {}).get("amount", 0))
            tax = float(cart_cost.get("totalTaxAmount", {}).get("amount", 0))
            
            estimated_shipping = total - subtotal - tax
            if estimated_shipping > 0:
                currency = cart_cost.get("totalAmount", {}).get("currencyCode", "USD")
                shipping_options.append({
                    "title": "Standard Shipping",
                    "description": "Estimated shipping cost",
                    "handle": "standard",
                    "cost": {
                        "amount": str(estimated_shipping),
                        "currencyCode": currency
                    }
                })
        
        return {
            "status": "success",
            "shipping_options": shipping_options,
            "cart_totals": cart_cost,
            "address": address,
            "checkout_url": updated_cart.get("checkoutUrl")
        }
    
    # Handle API call failures
    error_msg = result.get("error_message", "Unknown error occurred")
    return {
        "status": "error",
        "error_message": f"I'm having trouble calculating shipping rates right now. Please try again in a moment! ({error_msg})"
    }


def apply_discount_code(
    cart_id: str,
    discount_codes: List[str],
    shop: Optional[str] = None,
    api_version: Optional[str] = None,
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Applies discount codes to a cart.
    
    Args:
        cart_id (str): The ID of the cart to apply discounts to
        discount_codes (List[str]): List of discount codes to apply
        shop (Optional[str]): The shop name (without .myshopify.com)
        api_version (Optional[str]): The API version
        access_token (Optional[str]): The Shopify Storefront access token
    
    Returns:
        Dict[str, Any]: Cart with applied discounts
    """
    # Input validation
    if not cart_id or not isinstance(cart_id, str):
        return {
            "status": "error",
            "error_message": "I need a valid cart to apply discount codes. Please add some items to your cart first."
        }
    
    if not discount_codes or not isinstance(discount_codes, list):
        return {
            "status": "error",
            "error_message": "Please provide a discount code to apply."
        }
    
    # Clean and validate discount codes
    valid_codes = []
    for code in discount_codes:
        if isinstance(code, str) and code.strip():
            cleaned_code = code.strip().upper()
            if len(cleaned_code) <= 50:  # Reasonable limit
                valid_codes.append(cleaned_code)
    
    if not valid_codes:
        return {
            "status": "error",
            "error_message": "Please provide valid discount codes (letters and numbers only)."
        }
    
    # Check if cart exists first
    cart_check = get_cart(cart_id, shop, api_version, access_token)
    if cart_check["status"] != "success":
        return {
            "status": "error",
            "error_message": "I couldn't find your cart. Please add some items first, then I can apply discount codes."
        }
    query = """
    mutation cartDiscountCodesUpdate($cartId: ID!, $discountCodes: [String!]) {
        cartDiscountCodesUpdate(cartId: $cartId, discountCodes: $discountCodes) {
            cart {
                id
                checkoutUrl
                discountCodes {
                    code
                    applicable
                }
                discountAllocations {
                    discountedAmount {
                        amount
                        currencyCode
                    }
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
                                        id
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
                    totalTaxAmount {
                        amount
                        currencyCode
                    }
                    totalDutyAmount {
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
    
    variables = {
        "cartId": cart_id,
        "discountCodes": valid_codes
    }
    
    result = fetch_shopify_storefront_graphql(query, variables, shop, api_version, access_token)
    
    if result["status"] == "success":
        cart_data = result["data"].get("cartDiscountCodesUpdate", {})
        cart = cart_data.get("cart")
        user_errors = cart_data.get("userErrors", [])
        
        if user_errors:
            # Provide specific feedback for common discount code errors
            error_msg = user_errors[0].get("message", "Invalid discount code")
            if "not found" in error_msg.lower() or "invalid" in error_msg.lower():
                return {
                    "status": "error",
                    "error_message": f"The discount code '{valid_codes[0]}' isn't valid. Please check the code and try again!"
                }
            elif "expired" in error_msg.lower():
                return {
                    "status": "error", 
                    "error_message": f"The discount code '{valid_codes[0]}' has expired. Do you have another code to try?"
                }
            elif "minimum" in error_msg.lower():
                return {
                    "status": "error",
                    "error_message": f"Your cart doesn't meet the minimum requirements for the discount code '{valid_codes[0]}'. Add more items to qualify!"
                }
            else:
                return {
                    "status": "error",
                    "error_message": f"I couldn't apply the discount code '{valid_codes[0]}': {error_msg}"
                }
        
        # Check if discounts were actually applied
        discount_codes = cart.get("discountCodes", [])
        applied_codes = [dc for dc in discount_codes if dc.get("applicable", False)]
        
        if not applied_codes and valid_codes:
            return {
                "status": "error", 
                "error_message": f"The discount code '{valid_codes[0]}' couldn't be applied to your current cart items."
            }
        
        return {
            "status": "success",
            "cart_id": cart.get("id"),
            "checkout_url": cart.get("checkoutUrl"),
            "discount_codes": discount_codes,
            "discount_allocations": cart.get("discountAllocations", []),
            "applied_codes": applied_codes,
            "cart_data": cart,
            "message": f"✅ Applied discount code '{applied_codes[0].get('code')}' to your cart!" if applied_codes else "Discount codes updated"
        }
    
    return result


def get_product_recommendations(
    product_id: str,
    recommendation_type: str = "related",
    limit: int = 5,
    shop: Optional[str] = None,
    api_version: Optional[str] = None,
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Gets product recommendations for upsell and cross-sell.
    
    Args:
        product_id (str): The ID of the base product
        recommendation_type (str): Type of recommendations ("related", "upsell", "crosssell")
        limit (int): Number of recommendations to return
        shop (Optional[str]): The shop name (without .myshopify.com)
        api_version (Optional[str]): The API version
        access_token (Optional[str]): The Shopify Admin access token
    
    Returns:
        Dict[str, Any]: Product recommendations
    """
    # First get the base product details
    base_product_query = """
    query getProduct($id: ID!) {
        product(id: $id) {
            id
            title
            handle
            productType
            vendor
            tags
            collections(first: 5) {
                edges {
                    node {
                        id
                        handle
                        title
                    }
                }
            }
            variants(first: 10) {
                edges {
                    node {
                        id
                        title
                        price {
                            amount
                            currencyCode
                        }
                        compareAtPrice {
                            amount
                            currencyCode
                        }
                        availableForSale
                        selectedOptions {
                            name
                            value
                        }
                    }
                }
            }
            priceRange {
                minVariantPrice {
                    amount
                    currencyCode
                }
                maxVariantPrice {
                    amount
                    currencyCode
                }
            }
        }
    }
    """
    
    variables = {"id": product_id}
    
    result = fetch_shopify_graphql(base_product_query, variables, shop, api_version, access_token)
    
    if result["status"] != "success":
        return result
    
    base_product = result["data"].get("product")
    if not base_product:
        return {
            "status": "error",
            "error_message": "Base product not found"
        }
    
    # Build search query based on recommendation type
    if recommendation_type == "upsell":
        # Find products with higher price in same category
        search_query = f"product_type:{base_product['productType']} AND vendor:{base_product['vendor']}"
    elif recommendation_type == "crosssell":
        # Find complementary products by tags and collections
        tags = base_product.get("tags", [])[:3]  # Use first 3 tags
        if tags:
            tag_query = " OR ".join([f"tag:{tag}" for tag in tags])
            search_query = f"({tag_query})"
        else:
            search_query = f"product_type:{base_product['productType']}"
    else:  # related
        # Find similar products
        search_query = f"product_type:{base_product['productType']} OR vendor:{base_product['vendor']}"
    
    # Search for recommendations
    recommendations = search_products(search_query, limit + 5, shop, api_version, access_token)
    
    if recommendations["status"] != "success":
        return recommendations
    
    # Filter out the base product and apply recommendation logic
    filtered_recommendations = []
    base_price = float(base_product["priceRange"]["minVariantPrice"]["amount"])
    
    for edge in recommendations["products"]:
        product = edge["node"]
        if product["id"] == product_id:
            continue  # Skip the base product
        
        product_price = float(product["priceRange"]["minVariantPrice"]["amount"])
        
        # Apply filtering based on recommendation type
        if recommendation_type == "upsell" and product_price <= base_price:
            continue  # Upsells should be more expensive
        elif recommendation_type == "crosssell":
            # Cross-sells can be any price, but prefer similar price range
            price_diff_ratio = abs(product_price - base_price) / base_price
            if price_diff_ratio > 2.0:  # Skip if price is too different
                continue
        
        filtered_recommendations.append(edge)
        
        if len(filtered_recommendations) >= limit:
            break
    
    return {
        "status": "success",
        "base_product": base_product,
        "recommendations": filtered_recommendations,
        "recommendation_type": recommendation_type,
        "search_query": search_query
    }


def find_product_alternatives(
    product_id: str,
    reason: str = "out_of_stock",
    limit: int = 5,
    shop: Optional[str] = None,
    api_version: Optional[str] = None,
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Finds alternative products when the requested item is unavailable.
    
    Args:
        product_id (str): The ID of the unavailable product
        reason (str): Reason for finding alternatives ("out_of_stock", "discontinued", etc.)
        limit (int): Number of alternatives to return
        shop (Optional[str]): The shop name (without .myshopify.com)
        api_version (Optional[str]): The API version
        access_token (Optional[str]): The Shopify Admin access token
    
    Returns:
        Dict[str, Any]: Alternative product suggestions
    """
    # Get the unavailable product details
    base_product_query = """
    query getProduct($id: ID!) {
        product(id: $id) {
            id
            title
            handle
            productType
            vendor
            tags
            availableForSale
            priceRange {
                minVariantPrice {
                    amount
                    currencyCode
                }
                maxVariantPrice {
                    amount
                    currencyCode
                }
            }
            collections(first: 5) {
                edges {
                    node {
                        id
                        handle
                        title
                    }
                }
            }
        }
    }
    """
    
    variables = {"id": product_id}
    
    result = fetch_shopify_graphql(base_product_query, variables, shop, api_version, access_token)
    
    if result["status"] != "success":
        return result
    
    unavailable_product = result["data"].get("product")
    if not unavailable_product:
        return {
            "status": "error",
            "error_message": "Product not found"
        }
    
    # Build search query for alternatives
    product_type = unavailable_product.get("productType", "")
    vendor = unavailable_product.get("vendor", "")
    tags = unavailable_product.get("tags", [])[:3]
    
    # Priority search strategy:
    # 1. Same brand (vendor) and type
    # 2. Same type, different brand
    # 3. Similar tags
    search_queries = []
    
    if vendor and product_type:
        search_queries.append(f"vendor:{vendor} AND product_type:{product_type} AND available_for_sale:true")
    
    if product_type:
        search_queries.append(f"product_type:{product_type} AND available_for_sale:true")
    
    if tags:
        tag_query = " OR ".join([f"tag:{tag}" for tag in tags])
        search_queries.append(f"({tag_query}) AND available_for_sale:true")
    
    # Search for alternatives using each query
    all_alternatives = []
    base_price = float(unavailable_product["priceRange"]["minVariantPrice"]["amount"])
    
    for search_query in search_queries:
        alternatives = search_products(search_query, limit * 2, shop, api_version, access_token)
        
        if alternatives["status"] == "success":
            for edge in alternatives["products"]:
                product = edge["node"]
                if product["id"] == product_id:
                    continue  # Skip the unavailable product
                
                # Calculate price similarity score
                product_price = float(product["priceRange"]["minVariantPrice"]["amount"])
                price_diff_ratio = abs(product_price - base_price) / base_price
                
                # Add scoring for similarity
                similarity_score = 0
                if product.get("vendor") == vendor:
                    similarity_score += 3
                if product.get("productType") == product_type:
                    similarity_score += 2
                
                # Check tag overlap
                product_tags = product.get("tags", [])
                tag_overlap = len(set(tags) & set(product_tags))
                similarity_score += tag_overlap
                
                # Prefer similar price range
                if price_diff_ratio < 0.2:  # Within 20% price difference
                    similarity_score += 2
                elif price_diff_ratio < 0.5:  # Within 50% price difference
                    similarity_score += 1
                
                edge["similarity_score"] = similarity_score
                edge["price_diff_ratio"] = price_diff_ratio
                
                all_alternatives.append(edge)
    
    # Remove duplicates and sort by similarity score
    seen_ids = set()
    unique_alternatives = []
    for alt in all_alternatives:
        product_id_alt = alt["node"]["id"]
        if product_id_alt not in seen_ids:
            seen_ids.add(product_id_alt)
            unique_alternatives.append(alt)
    
    # Sort by similarity score (descending)
    unique_alternatives.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
    
    return {
        "status": "success",
        "unavailable_product": unavailable_product,
        "alternatives": unique_alternatives[:limit],
        "reason": reason,
        "total_found": len(unique_alternatives)
    }


def get_subscription_products(
    shop: Optional[str] = None,
    api_version: Optional[str] = None,
    access_token: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Gets products that support subscriptions/recurring orders.
    
    Args:
        shop (Optional[str]): The shop name (without .myshopify.com)
        api_version (Optional[str]): The API version
        access_token (Optional[str]): The Shopify Admin access token
        limit (int): Number of products to return
    
    Returns:
        Dict[str, Any]: Subscription-enabled products
    """
    # Search for products with subscription-related tags or selling plans
    query = """
    query getSubscriptionProducts($first: Int!, $query: String!) {
        products(first: $first, query: $query) {
            edges {
                node {
                    id
                    title
                    handle
                    description
                    productType
                    vendor
                    tags
                    availableForSale
                    priceRange {
                        minVariantPrice {
                            amount
                            currencyCode
                        }
                        maxVariantPrice {
                            amount
                            currencyCode
                        }
                    }
                    images(first: 3) {
                        edges {
                            node {
                                id
                                url
                                altText
                            }
                        }
                    }
                    variants(first: 5) {
                        edges {
                            node {
                                id
                                title
                                price {
                                    amount
                                    currencyCode
                                }
                                availableForSale
                                selectedOptions {
                                    name
                                    value
                                }
                                sellingPlanAllocations(first: 5) {
                                    edges {
                                        node {
                                            sellingPlan {
                                                id
                                                name
                                                description
                                                options {
                                                    name
                                                    value
                                                }
                                                recurringDeliveries
                                                priceAdjustments {
                                                    adjustmentType
                                                    adjustmentValue {
                                                        ... on SellingPlanFixedAmountPriceAdjustment {
                                                            adjustmentAmount {
                                                                amount
                                                                currencyCode
                                                            }
                                                        }
                                                        ... on SellingPlanPercentagePriceAdjustment {
                                                            adjustmentPercentage
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    # Search for products with subscription indicators
    search_query = "tag:subscription OR tag:recurring OR tag:monthly OR tag:weekly OR available_for_sale:true"
    
    variables = {
        "first": limit,
        "query": search_query
    }
    
    result = fetch_shopify_graphql(query, variables, shop, api_version, access_token)
    
    if result["status"] == "success":
        products_data = result["data"].get("products", {})
        products = products_data.get("edges", [])
        
        # Filter products that actually have selling plans or subscription tags
        subscription_products = []
        for edge in products:
            product = edge["node"]
            tags = product.get("tags", [])
            has_subscription_tag = any(tag.lower() in ["subscription", "recurring", "monthly", "weekly", "daily"] for tag in tags)
            
            # Check if any variant has selling plans
            has_selling_plans = False
            for variant_edge in product.get("variants", {}).get("edges", []):
                variant = variant_edge["node"]
                if variant.get("sellingPlanAllocations", {}).get("edges"):
                    has_selling_plans = True
                    break
            
            if has_subscription_tag or has_selling_plans:
                subscription_products.append(edge)
        
        return {
            "status": "success",
            "subscription_products": subscription_products,
            "total_found": len(subscription_products),
            "search_query": search_query
        }
    
    return result


def explain_subscription_options(
    product_id: str,
    shop: Optional[str] = None,
    api_version: Optional[str] = None,
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Explains subscription options for a specific product.
    
    Args:
        product_id (str): The ID of the product
        shop (Optional[str]): The shop name (without .myshopify.com)
        api_version (Optional[str]): The API version
        access_token (Optional[str]): The Shopify Admin access token
    
    Returns:
        Dict[str, Any]: Subscription options explanation
    """
    query = """
    query getProductSubscriptionOptions($id: ID!) {
        product(id: $id) {
            id
            title
            handle
            description
            tags
            variants(first: 10) {
                edges {
                    node {
                        id
                        title
                        price {
                            amount
                            currencyCode
                        }
                        availableForSale
                        sellingPlanAllocations(first: 10) {
                            edges {
                                node {
                                    sellingPlan {
                                        id
                                        name
                                        description
                                        options {
                                            name
                                            value
                                        }
                                        recurringDeliveries
                                        priceAdjustments {
                                            adjustmentType
                                            adjustmentValue {
                                                ... on SellingPlanFixedAmountPriceAdjustment {
                                                    adjustmentAmount {
                                                        amount
                                                        currencyCode
                                                    }
                                                }
                                                ... on SellingPlanPercentagePriceAdjustment {
                                                    adjustmentPercentage
                                                }
                                            }
                                        }
                                        billingPolicy {
                                            ... on SellingPlanRecurringBillingPolicy {
                                                interval
                                                intervalCount
                                            }
                                        }
                                        deliveryPolicy {
                                            ... on SellingPlanRecurringDeliveryPolicy {
                                                interval
                                                intervalCount
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    variables = {"id": product_id}
    
    result = fetch_shopify_graphql(query, variables, shop, api_version, access_token)
    
    if result["status"] == "success":
        product = result["data"].get("product")
        if not product:
            return {
                "status": "error",
                "error_message": "Product not found"
            }
        
        # Extract subscription options
        subscription_options = []
        for variant_edge in product.get("variants", {}).get("edges", []):
            variant = variant_edge["node"]
            for plan_edge in variant.get("sellingPlanAllocations", {}).get("edges", []):
                plan = plan_edge["node"]["sellingPlan"]
                
                # Build human-readable explanation
                explanation = {
                    "plan_id": plan["id"],
                    "plan_name": plan["name"],
                    "description": plan.get("description", ""),
                    "variant_id": variant["id"],
                    "variant_title": variant["title"],
                    "base_price": variant["price"],
                    "recurring": plan.get("recurringDeliveries", False)
                }
                
                # Parse billing and delivery policies
                billing_policy = plan.get("billingPolicy", {})
                delivery_policy = plan.get("deliveryPolicy", {})
                
                if billing_policy:
                    interval = billing_policy.get("interval", "")
                    interval_count = billing_policy.get("intervalCount", 1)
                    explanation["billing_frequency"] = f"Every {interval_count} {interval.lower()}{'s' if interval_count > 1 else ''}"
                
                if delivery_policy:
                    interval = delivery_policy.get("interval", "")
                    interval_count = delivery_policy.get("intervalCount", 1)
                    explanation["delivery_frequency"] = f"Every {interval_count} {interval.lower()}{'s' if interval_count > 1 else ''}"
                
                # Calculate discounted price
                price_adjustments = plan.get("priceAdjustments", [])
                if price_adjustments:
                    base_amount = float(variant["price"]["amount"])
                    for adjustment in price_adjustments:
                        adj_value = adjustment.get("adjustmentValue", {})
                        if "adjustmentPercentage" in adj_value:
                            discount_percent = adj_value["adjustmentPercentage"]
                            discounted_amount = base_amount * (1 - discount_percent / 100)
                            explanation["discounted_price"] = {
                                "amount": str(discounted_amount),
                                "currencyCode": variant["price"]["currencyCode"]
                            }
                            explanation["discount_percentage"] = discount_percent
                        elif "adjustmentAmount" in adj_value:
                            discount_amount = float(adj_value["adjustmentAmount"]["amount"])
                            discounted_amount = base_amount - discount_amount
                            explanation["discounted_price"] = {
                                "amount": str(discounted_amount),
                                "currencyCode": variant["price"]["currencyCode"]
                            }
                            explanation["discount_amount"] = adj_value["adjustmentAmount"]
                
                subscription_options.append(explanation)
        
        # Check for subscription-related tags
        tags = product.get("tags", [])
        subscription_tags = [tag for tag in tags if tag.lower() in ["subscription", "recurring", "monthly", "weekly", "daily"]]
        
        return {
            "status": "success",
            "product": {
                "id": product["id"],
                "title": product["title"],
                "handle": product["handle"],
                "description": product.get("description", "")
            },
            "subscription_options": subscription_options,
            "subscription_tags": subscription_tags,
            "has_subscriptions": len(subscription_options) > 0 or len(subscription_tags) > 0
        }
    
    return result
