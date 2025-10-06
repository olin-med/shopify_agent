import os
import subprocess
import json
import requests
import uuid
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logger for this module
logger = logging.getLogger(__name__)

# Global conversation state for MCP
_mcp_conversation_id = None
_mcp_api_contexts = {}  # Track which APIs have been initialized


class MCPError(Exception):
    """Custom exception for MCP-related errors"""
    pass


def _run_mcp_command(request: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    """
    Execute an MCP command and return parsed response.

    Args:
        request: JSON-RPC request dictionary
        timeout: Command timeout in seconds

    Returns:
        Dict containing the MCP response

    Raises:
        MCPError: If MCP command fails
    """
    try:
        mcp_command = ["npx", "-y", "@shopify/dev-mcp@latest"]

        logger.debug(f"Running MCP command: {' '.join(mcp_command)}")
        logger.debug(f"MCP request: {json.dumps(request, indent=2)}")

        # Use Popen with communicate() for proper stdio handling
        # MCP stdio protocol requires line-delimited JSON messages
        proc = subprocess.Popen(
            mcp_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffering for proper MCP stdio communication
        )

        try:
            # Send JSON with newline (MCP expects line-delimited JSON-RPC)
            stdout, stderr = proc.communicate(
                input=json.dumps(request) + '\n',
                timeout=timeout
            )
        except subprocess.TimeoutExpired:
            proc.kill()
            logger.error(f"MCP command timed out after {timeout}s")
            raise MCPError("MCP command timed out")

        if proc.returncode != 0:
            logger.error(f"MCP command failed with return code {proc.returncode}")
            logger.error(f"MCP stderr: {stderr}")
            raise MCPError(f"MCP command failed: {stderr}")

        # Check if stdout is empty
        if not stdout or stdout.strip() == "":
            logger.error("MCP returned empty response")
            logger.error(f"MCP stderr: {stderr}")
            raise MCPError("MCP returned empty response - the MCP service may not be responding correctly")

        # Parse JSON from multi-line output (MCP may output debug logs + JSON)
        # Try to find and parse the JSON-RPC response line
        response = None
        for line in stdout.strip().split('\n'):
            line = line.strip()
            # Skip debug/log lines (e.g., [shopify-dev-fetch] ...)
            if not line or line.startswith('[') or not line.startswith('{'):
                continue
            try:
                parsed = json.loads(line)
                # Check if it's a valid JSON-RPC response
                if 'jsonrpc' in parsed and 'id' in parsed:
                    response = parsed
                    break
            except json.JSONDecodeError:
                continue

        if response is None:
            logger.error(f"Failed to parse JSON from MCP output. Raw output: {stdout}")
            raise MCPError("MCP returned invalid JSON response")

        logger.debug(f"MCP response: {json.dumps(response, indent=2)}")

        if "error" in response:
            logger.error(f"MCP returned error: {response['error']}")
            raise MCPError(f"MCP error: {response['error']}")

        return response

    except MCPError:
        # Re-raise MCPError as-is
        raise
    except FileNotFoundError as e:
        # npx not found - likely Node.js not installed or not in PATH
        logger.warning(f"npx command not found. Node.js may not be installed or not in PATH. Falling back to hardcoded queries.")
        raise MCPError("MCP unavailable: npx command not found (Node.js required). Using fallback queries.")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse MCP response: {str(e)}")
        raise MCPError(f"Failed to parse MCP response: {e}. MCP may not be available or is not responding correctly.")
    except Exception as e:
        logger.error(f"Unexpected MCP error: {str(e)}", exc_info=True)
        raise MCPError(f"MCP command error: {str(e)}")


def _normalize_api_for_mcp(api: str) -> str:
    """
    Normalize API parameter for MCP (which expects 'storefront-graphql' not 'storefront').

    Args:
        api: API name ("admin" or "storefront")

    Returns:
        MCP-compatible API name
    """
    if api == "storefront":
        return "storefront-graphql"
    return api


def initialize_mcp_conversation(api: str = "admin") -> str:
    """
    Initialize MCP conversation for a specific API.

    Args:
        api: Shopify API to initialize ("admin" or "storefront")

    Returns:
        Conversation ID for subsequent MCP calls
    """
    global _mcp_conversation_id, _mcp_api_contexts

    # Normalize API for MCP
    mcp_api = _normalize_api_for_mcp(api)

    # Generate conversation ID if not exists
    if _mcp_conversation_id is None:
        _mcp_conversation_id = str(uuid.uuid4())

    # Skip if this API context is already initialized
    if mcp_api in _mcp_api_contexts:
        return _mcp_conversation_id

    try:
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "learn_shopify_api",
                "arguments": {
                    "api": mcp_api,
                    "conversationId": _mcp_conversation_id
                }
            }
        }

        response = _run_mcp_command(request)

        if response.get("result"):
            _mcp_api_contexts[mcp_api] = True
            return _mcp_conversation_id
        else:
            raise MCPError(f"Failed to initialize {mcp_api} API context")

    except Exception as e:
        raise MCPError(f"Failed to initialize MCP conversation for {mcp_api}: {str(e)}")


def search_shopify_docs(query: str, api: str = "admin", max_results: int = 5) -> Dict[str, Any]:
    """
    Search Shopify documentation for relevant information.
    
    Args:
        query: Search query
        api: Shopify API context
        max_results: Maximum number of results
    
    Returns:
        Search results from Shopify documentation
    """
    try:
        conversation_id = initialize_mcp_conversation(api)
        
        request = {
            "jsonrpc": "2.0", 
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search_docs_chunks",
                "arguments": {
                    "conversationId": conversation_id,
                    "prompt": query,
                    "max_num_results": max_results
                }
            }
        }
        
        response = _run_mcp_command(request)
        return {
            "status": "success",
            "docs": response.get("result", {}),
            "query": query
        }
        
    except MCPError as e:
        return {
            "status": "error",
            "error_message": f"Documentation search failed: {str(e)}"
        }


def introspect_shopify_schema(search_term: str, api: str = "admin",
                             filter_types: List[str] = ["all"]) -> Dict[str, Any]:
    """
    Introspect Shopify GraphQL schema using MCP.

    Args:
        search_term: Term to search for in schema
        api: API to introspect ("admin" or "storefront")
        filter_types: Types to filter (types, queries, mutations, all)

    Returns:
        Schema introspection results
    """
    try:
        conversation_id = initialize_mcp_conversation(api)
        mcp_api = _normalize_api_for_mcp(api)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "introspect_graphql_schema",
                "arguments": {
                    "conversationId": conversation_id,
                    "query": search_term,
                    "api": mcp_api,
                    "filter": filter_types
                }
            }
        }

        response = _run_mcp_command(request)
        return {
            "status": "success",
            "schema": response.get("result", {}),
            "search_term": search_term
        }

    except MCPError as e:
        return {
            "status": "error",
            "error_message": f"Schema introspection failed: {str(e)}"
        }


def validate_graphql_query(query: str, api: str = "admin") -> Dict[str, Any]:
    """
    Validate GraphQL query using MCP.

    Args:
        query: GraphQL query to validate
        api: API to validate against ("admin" or "storefront")

    Returns:
        Validation results
    """
    try:
        conversation_id = initialize_mcp_conversation(api)
        mcp_api = _normalize_api_for_mcp(api)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "validate_graphql_codeblocks",
                "arguments": {
                    "conversationId": conversation_id,
                    "api": mcp_api,
                    "codeblocks": [query]
                }
            }
        }

        response = _run_mcp_command(request)
        result = response.get("result", {})

        if result and len(result.get("content", [])) > 0:
            validation = result["content"][0]
            is_valid = not validation.get("isError", True)

            return {
                "status": "success" if is_valid else "error",
                "is_valid": is_valid,
                "validation_details": validation,
                "query": query
            }

        return {
            "status": "error",
            "error_message": "No validation results returned"
        }

    except MCPError as e:
        return {
            "status": "error",
            "error_message": f"Query validation failed: {str(e)}"
        }


def execute_shopify_graphql(
    query: str,
    variables: Optional[Dict[str, Any]] = None,
    api: str = "storefront",
    shop: Optional[str] = None,
    api_version: Optional[str] = None,
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute a validated GraphQL query against Shopify APIs.

    Args:
        query: GraphQL query string
        variables: Query variables
        api: API type ("admin" or "storefront")
        shop: Shop name (from env if not provided)
        api_version: API version (from env if not provided)
        access_token: Access token (from env if not provided)

    Returns:
        GraphQL response data
    """
    # Get environment variables
    shop = shop or os.getenv("SHOPIFY_STORE")
    api_version = api_version or os.getenv("SHOPIFY_API_VERSION", "2025-07")

    if api == "admin":
        access_token = access_token or os.getenv("SHOPIFY_ADMIN_TOKEN")
        url = f"https://{shop}.myshopify.com/admin/api/{api_version}/graphql.json"
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token
        }
    else:  # storefront
        access_token = access_token or os.getenv("SHOPIFY_STOREFRONT_TOKEN")
        url = f"https://{shop}.myshopify.com/api/{api_version}/graphql.json"
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Storefront-Access-Token": access_token
        }

    # Validate required parameters
    if not shop:
        logger.error("SHOPIFY_STORE environment variable is not set")
        return {
            "status": "error",
            "error_message": "Shop name is required. Set SHOPIFY_STORE in .env file."
        }

    if not access_token:
        token_env = "SHOPIFY_ADMIN_TOKEN" if api == "admin" else "SHOPIFY_STOREFRONT_TOKEN"
        logger.error(f"{token_env} environment variable is not set")
        return {
            "status": "error",
            "error_message": f"Access token is required. Set {token_env} in .env file."
        }

    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    logger.debug(f"Executing {api} GraphQL query to: {url}")
    logger.debug(f"Query: {query[:200]}...")  # Log first 200 chars

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()

        if "errors" in data:
            logger.error(f"GraphQL returned errors: {json.dumps(data['errors'], indent=2)}")
            return {
                "status": "error",
                "error_message": f"GraphQL errors: {data['errors']}"
            }

        logger.debug(f"GraphQL query successful. Response data keys: {list(data.get('data', {}).keys())}")
        return {
            "status": "success",
            "data": data.get("data", {}),
            "extensions": data.get("extensions", {})
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"GraphQL request failed: {str(e)}", exc_info=True)
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        return {
            "status": "error",
            "error_message": f"Request failed: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Unexpected error in GraphQL execution: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error_message": f"Unexpected error: {str(e)}"
        }


def build_dynamic_query(intent: str, parameters: Dict[str, Any], api: str = "storefront") -> Dict[str, Any]:
    """
    Build GraphQL query dynamically using MCP documentation search.
    
    Args:
        intent: User intent (e.g., "search products", "create cart", "calculate shipping")
        parameters: Parameters for the operation
        api: Target API ("admin" or "storefront")
    
    Returns:
        Dict containing query and variables, or error
    """
    try:
        # Search for relevant documentation and examples
        search_result = search_shopify_docs(f"{intent} GraphQL {api} API", api)
        
        if search_result["status"] != "success":
            return search_result
        
        docs = search_result.get("docs", {})
        
        # Extract GraphQL examples from documentation
        content_items = docs.get("content", [])
        
        if not content_items:
            return {
                "status": "error",
                "error_message": f"No documentation found for '{intent}' in {api} API"
            }
        
        # Look for GraphQL code blocks in the documentation
        query_examples = []
        for item in content_items:
            text = item.get("text", "")
            if "query" in text.lower() or "mutation" in text.lower():
                # Extract potential GraphQL from text
                lines = text.split('\n')
                in_code_block = False
                current_query = []
                
                for line in lines:
                    if '```' in line and ('graphql' in line.lower() or 'gql' in line.lower()):
                        in_code_block = True
                        continue
                    elif '```' in line and in_code_block:
                        if current_query:
                            query_examples.append('\n'.join(current_query))
                            current_query = []
                        in_code_block = False
                        continue
                    elif in_code_block:
                        current_query.append(line)
        
        if not query_examples:
            # Try to introspect schema for relevant fields
            schema_result = introspect_shopify_schema(intent.split()[0], api)
            if schema_result["status"] == "success":
                return {
                    "status": "info",
                    "message": f"Found schema information for '{intent}' but no query examples. Manual query building required.",
                    "schema_info": schema_result["schema"]
                }
        
        # Use the first suitable query example
        base_query = query_examples[0] if query_examples else None
        
        if not base_query:
            return {
                "status": "error", 
                "error_message": f"Could not find suitable GraphQL query for '{intent}'"
            }
        
        # Validate the query
        validation_result = validate_graphql_query(base_query, api)
        
        if validation_result["status"] != "success":
            return {
                "status": "error",
                "error_message": f"Generated query is invalid: {validation_result.get('error_message')}"
            }
        
        return {
            "status": "success",
            "query": base_query,
            "variables": parameters,
            "validation": validation_result
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Query building failed: {str(e)}"
        }


def execute_shopify_operation(
    intent: str,
    parameters: Dict[str, Any],
    api: str
) -> Dict[str, Any]:
    """
    Unified function to execute any Shopify operation using MCP-powered query building.

    Args:
        intent: User intent (e.g., "search products", "create cart", "get shipping rates")
        parameters: Operation parameters
        api: Target API ("admin" or "storefront")

    Returns:
        Operation result with user-friendly error handling
    """
    try:
        # Set default API if not provided
        if not api:
            api = "storefront"

        # Input validation
        if not intent or not isinstance(intent, str):
            return {
                "status": "error",
                "error_message": "Please specify what you'd like to do (e.g., 'search products', 'create cart')"
            }

        if not isinstance(parameters, dict):
            parameters = {}
        
        # Build query dynamically using MCP
        query_result = build_dynamic_query(intent, parameters, api)
        
        if query_result["status"] != "success":
            # If dynamic building fails, try some common hardcoded patterns
            return _fallback_operation(intent, parameters, api)
        
        query = query_result["query"]
        variables = query_result["variables"]
        
        # Execute the query
        execution_result = execute_shopify_graphql(query, variables, api)
        
        if execution_result["status"] != "success":
            return {
                "status": "error",
                "error_message": f"Operation '{intent}' failed: {execution_result.get('error_message')}"
            }
        
        # Process and format the response based on intent
        formatted_result = _format_operation_result(intent, execution_result["data"], parameters)
        
        return {
            "status": "success",
            "intent": intent,
            "data": formatted_result,
            "raw_data": execution_result["data"]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Operation '{intent}' encountered an error: {str(e)}"
        }


def _fallback_operation(intent: str, parameters: Dict[str, Any], api: str) -> Dict[str, Any]:
    """
    Fallback to hardcoded queries for common operations when MCP fails.
    """
    intent_lower = intent.lower()
    
    # Product search fallback
    if "search" in intent_lower and "product" in intent_lower:
        return _execute_product_search(parameters.get("query", ""), parameters.get("first", 20))
    
    # Cart creation fallback
    elif "create" in intent_lower and "cart" in intent_lower:
        return _execute_cart_creation(parameters.get("lines", []))
    
    # Get cart fallback
    elif "get" in intent_lower and "cart" in intent_lower:
        return _execute_get_cart(parameters.get("cart_id", ""))
    
    # Apply discount fallback
    elif "discount" in intent_lower or "coupon" in intent_lower:
        return _execute_apply_discount(parameters.get("cart_id", ""), parameters.get("codes", []))
    
    # Shipping calculation fallback
    elif "shipping" in intent_lower or "delivery" in intent_lower:
        return _execute_shipping_calculation(parameters.get("cart_id", ""), parameters.get("address", {}))
    
    else:
        return {
            "status": "error",
            "error_message": f"I don't know how to '{intent}'. Please try rephrasing your request."
        }


def _format_operation_result(intent: str, data: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format GraphQL response data into user-friendly format based on operation intent.
    """
    intent_lower = intent.lower()
    
    # Format product search results
    if "search" in intent_lower and "product" in intent_lower:
        # Handle both GraphQL format (edges) and direct array format
        if "edges" in data.get("products", {}):
            # Raw GraphQL format
            products = data.get("products", {}).get("edges", [])
            return {
                "products": [edge["node"] for edge in products],
                "total_found": len(products),
                "search_query": parameters.get("query", "")
            }
        else:
            # Direct array format from fallback
            products = data.get("products", [])
            return {
                "products": products,
                "total_found": len(products),
                "search_query": parameters.get("query", "")
            }
    
    # Format cart operations
    elif "cart" in intent_lower:
        if "cartCreate" in data:
            cart_data = data["cartCreate"]["cart"]
            return {
                "cart_id": cart_data.get("id"),
                "checkout_url": cart_data.get("checkoutUrl"),
                "total_quantity": len(cart_data.get("lines", {}).get("edges", [])),
                "cost": cart_data.get("cost", {})
            }
        elif "cart" in data:
            cart_data = data["cart"]
            return {
                "cart_id": cart_data.get("id"),
                "checkout_url": cart_data.get("checkoutUrl"), 
                "lines": cart_data.get("lines", {}).get("edges", []),
                "cost": cart_data.get("cost", {})
            }
    
    # Format shipping results
    elif "shipping" in intent_lower:
        if "cartShippingAddressUpdate" in data:
            cart_data = data["cartShippingAddressUpdate"]["cart"]
            delivery_groups = cart_data.get("deliveryGroups", {}).get("edges", [])
            
            shipping_options = []
            for group in delivery_groups:
                options = group.get("node", {}).get("deliveryOptions", [])
                shipping_options.extend(options)
            
            return {
                "shipping_options": shipping_options,
                "cart_totals": cart_data.get("cost", {}),
                "total_options": len(shipping_options)
            }
    
    # Default formatting - return raw data
    return data


# Fallback implementations for core operations
def _execute_product_search(query: str, first: int = 20) -> Dict[str, Any]:
    """Fallback product search with intelligent query handling."""
    if not query:
        return {
            "status": "error",
            "error_message": "Please provide a search term to find products."
        }
    
    # Clean the query
    cleaned_query = query.strip()
    
    # If query is very generic or short, get all products
    if not cleaned_query or len(cleaned_query) <= 2 or cleaned_query.lower() in ['*', 'all', 'any', 'product', 'item']:
        # Get all products without filter
        graphql_query = """
        query getAllProducts($first: Int!) {
            products(first: $first) {
                edges {
                    node {
                        id
                        title
                        handle
                        description
                        availableForSale
                        priceRange {
                            minVariantPrice {
                                amount
                                currencyCode
                            }
                        }
                        images(first: 1) {
                            edges {
                                node {
                                    url
                                    altText
                                }
                            }
                        }
                        variants(first: 3) {
                            edges {
                                node {
                                    id
                                    title
                                    availableForSale
                                    price {
                                        amount
                                        currencyCode
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        variables = {"first": min(first, 100)}
    else:
        # Use search query
        graphql_query = """
        query searchProducts($query: String!, $first: Int!) {
            products(first: $first, query: $query) {
                edges {
                    node {
                        id
                        title
                        handle
                        description
                        availableForSale
                        priceRange {
                            minVariantPrice {
                                amount
                                currencyCode
                            }
                        }
                        images(first: 1) {
                            edges {
                                node {
                                    url
                                    altText
                                }
                            }
                        }
                        variants(first: 3) {
                            edges {
                                node {
                                    id
                                    title
                                    availableForSale
                                    price {
                                        amount
                                        currencyCode
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        variables = {"query": cleaned_query, "first": min(first, 100)}
    
    result = execute_shopify_graphql(graphql_query, variables, "storefront")
    
    if result["status"] == "success":
        products = result["data"].get("products", {}).get("edges", [])
        
        # If search query returned no results, try getting all products as fallback
        if not products and cleaned_query and len(cleaned_query) > 2:
            print(f"No products found for '{cleaned_query}', getting all products...")
            fallback_query = """
            query getAllProducts($first: Int!) {
                products(first: $first) {
                    edges {
                        node {
                            id
                            title
                            handle
                            description
                            availableForSale
                            priceRange {
                                minVariantPrice {
                                    amount
                                    currencyCode
                                }
                            }
                        }
                    }
                }
            }
            """
            fallback_result = execute_shopify_graphql(fallback_query, {"first": min(first, 100)}, "storefront")
            if fallback_result["status"] == "success":
                products = fallback_result["data"].get("products", {}).get("edges", [])
        
        return {
            "status": "success",
            "products": [edge["node"] for edge in products],
            "total_found": len(products),
            "search_query": cleaned_query
        }
    
    return result


def _execute_cart_creation(lines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Fallback cart creation with hardcoded query."""
    if not lines:
        return {
            "status": "error",
            "error_message": "Please provide items to add to the cart."
        }
    
    graphql_query = """
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
                }
            }
            userErrors {
                field
                message
            }
        }
    }
    """
    
    variables = {"input": {"lines": lines}}
    result = execute_shopify_graphql(graphql_query, variables, "storefront")
    
    if result["status"] == "success":
        cart_data = result["data"].get("cartCreate", {})
        if cart_data.get("userErrors"):
            return {
                "status": "error",
                "error_message": f"Cart creation failed: {cart_data['userErrors'][0].get('message')}"
            }
        
        cart = cart_data.get("cart", {})
        return {
            "status": "success",
            "cart_id": cart.get("id"),
            "checkout_url": cart.get("checkoutUrl"),
            "total_quantity": len(cart.get("lines", {}).get("edges", [])),
            "cost": cart.get("cost", {})
        }
    
    return result


def _execute_get_cart(cart_id: str) -> Dict[str, Any]:
    """Fallback get cart with hardcoded query."""
    if not cart_id:
        return {
            "status": "error", 
            "error_message": "Please provide a cart ID."
        }
    
    graphql_query = """
    query getCart($id: ID!) {
        cart(id: $id) {
            id
            checkoutUrl
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
    
    variables = {"id": cart_id}
    result = execute_shopify_graphql(graphql_query, variables, "storefront")
    
    if result["status"] == "success":
        cart = result["data"].get("cart")
        if not cart:
            return {
                "status": "error",
                "error_message": "Cart not found."
            }
        
        return {
            "status": "success",
            "cart_id": cart.get("id"),
            "checkout_url": cart.get("checkoutUrl"),
            "lines": cart.get("lines", {}).get("edges", []),
            "cost": cart.get("cost", {})
        }
    
    return result


def _execute_apply_discount(cart_id: str, codes: List[str]) -> Dict[str, Any]:
    """Fallback discount application with hardcoded query."""
    if not cart_id or not codes:
        return {
            "status": "error",
            "error_message": "Please provide both cart ID and discount codes."
        }
    
    graphql_query = """
    mutation cartDiscountCodesUpdate($cartId: ID!, $discountCodes: [String!]) {
        cartDiscountCodesUpdate(cartId: $cartId, discountCodes: $discountCodes) {
            cart {
                id
                discountCodes {
                    code
                    applicable
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
    
    variables = {"cartId": cart_id, "discountCodes": codes}
    result = execute_shopify_graphql(graphql_query, variables, "storefront")
    
    if result["status"] == "success":
        discount_data = result["data"].get("cartDiscountCodesUpdate", {})
        if discount_data.get("userErrors"):
            return {
                "status": "error",
                "error_message": f"Discount application failed: {discount_data['userErrors'][0].get('message')}"
            }
        
        cart = discount_data.get("cart", {})
        applied_codes = [dc for dc in cart.get("discountCodes", []) if dc.get("applicable")]
        
        return {
            "status": "success",
            "cart_id": cart.get("id"),
            "applied_codes": applied_codes,
            "total_discounts": len(applied_codes),
            "cost": cart.get("cost", {})
        }
    
    return result


def _execute_shipping_calculation(cart_id: str, address: Dict[str, str]) -> Dict[str, Any]:
    """Modern shipping calculation using the 2025-01 CartDelivery API."""
    if not cart_id or not address.get("country"):
        return {
            "status": "error",
            "error_message": "Please provide cart ID and shipping address with at least a country."
        }

    # Step 1: Update buyer identity with country code
    buyer_identity_query = """
    mutation cartBuyerIdentityUpdate($cartId: ID!, $buyerIdentity: CartBuyerIdentityInput!) {
        cartBuyerIdentityUpdate(cartId: $cartId, buyerIdentity: $buyerIdentity) {
            cart {
                id
            }
            userErrors {
                field
                message
            }
        }
    }
    """

    # Step 2: Add delivery address using correct 2025-01 format
    add_delivery_address_query = """
    mutation cartDeliveryAddressesAdd($cartId: ID!, $addresses: [CartSelectableAddressInput!]!) {
        cartDeliveryAddressesAdd(cartId: $cartId, addresses: $addresses) {
            cart {
                id
                deliveryGroups(first: 5) {
                    edges {
                        node {
                            id
                            deliveryOptions {
                                handle
                                title
                                description
                                estimatedCost {
                                    amount
                                    currencyCode
                                }
                            }
                            selectedDeliveryOption {
                                handle
                                title
                                estimatedCost {
                                    amount
                                    currencyCode
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
                }
            }
            userErrors {
                field
                message
            }
            warnings {
                message
            }
        }
    }
    """

    # Normalize country code - handle common country name variations
    def normalize_country_code(country_input: str) -> str:
        """Convert country names/codes to proper ISO 3166-1 alpha-2 codes"""
        country_map = {
            # Common variations for major countries
            "BRAZIL": "BR",
            "BRASIL": "BR",
            "UNITED STATES": "US",
            "USA": "US",
            "AMERICA": "US",
            "CANADA": "CA",
            "UNITED KINGDOM": "GB",
            "UK": "GB",
            "ENGLAND": "GB",
            "FRANCE": "FR",
            "GERMANY": "DE",
            "ITALY": "IT",
            "SPAIN": "ES",
            "AUSTRALIA": "AU",
            "JAPAN": "JP",
            "CHINA": "CN",
            "INDIA": "IN",
            "MEXICO": "MX",
            "ARGENTINA": "AR",
        }

        country_upper = country_input.upper().strip()
        return country_map.get(country_upper, country_upper)

    # Normalize the country code
    normalized_country = normalize_country_code(address.get("country", "US"))

    try:
        # Step 1: Update buyer identity with country code only
        buyer_identity = {
            "countryCode": normalized_country
        }

        variables = {
            "cartId": cart_id,
            "buyerIdentity": buyer_identity
        }

        result = execute_shopify_graphql(buyer_identity_query, variables, "storefront")

        if result["status"] != "success":
            return {
                "status": "error",
                "error_message": f"Failed to update buyer identity: {result.get('error_message', 'Unknown error')}"
            }

        # Check for user errors in buyer identity update
        buyer_data = result["data"].get("cartBuyerIdentityUpdate", {})
        user_errors = buyer_data.get("userErrors", [])

        if user_errors:
            error_details = user_errors[0]
            return {
                "status": "error",
                "error_message": f"Buyer identity error: {error_details.get('message', 'Unknown error')}"
            }

        # Step 2: Create proper address structure for 2025-01 API
        # Build CartDeliveryAddressInput format with correct field names
        delivery_address = {
            "countryCode": normalized_country  # Use countryCode, not country
        }

        # Add optional fields with correct field names
        if address.get("city"):
            delivery_address["city"] = address.get("city")

        if address.get("province") or address.get("state"):
            delivery_address["provinceCode"] = address.get("province", address.get("state", ""))  # Use provinceCode

        if address.get("zip") or address.get("postal_code") or address.get("zipcode"):
            delivery_address["zip"] = address.get("zip", address.get("postal_code", address.get("zipcode", "")))

        if address.get("address1") or address.get("street"):
            delivery_address["address1"] = address.get("address1", address.get("street", ""))

        if address.get("address2") or address.get("street2"):
            delivery_address["address2"] = address.get("address2", address.get("street2", ""))

        if address.get("company"):
            delivery_address["company"] = address.get("company")

        if address.get("phone"):
            delivery_address["phone"] = address.get("phone")

        if address.get("firstName"):
            delivery_address["firstName"] = address.get("firstName")

        if address.get("lastName"):
            delivery_address["lastName"] = address.get("lastName")

        # Create CartSelectableAddressInput with proper structure
        delivery_address_input = {
            "address": {
                "deliveryAddress": delivery_address
            },
            "selected": True,  # Mark as selected to trigger shipping calculation
            "oneTimeUse": True  # Don't save to customer addresses
        }

        variables = {
            "cartId": cart_id,
            "addresses": [delivery_address_input]
        }

        result = execute_shopify_graphql(add_delivery_address_query, variables, "storefront")

        if result["status"] == "success":
            shipping_data = result["data"].get("cartDeliveryAddressesAdd", {})
            user_errors = shipping_data.get("userErrors", [])

            if user_errors:
                error_details = user_errors[0]
                error_message = error_details.get('message', 'Unknown error')
                error_field = error_details.get('field', '')

                # Provide more helpful error messages for common issues
                if 'country' in error_message.lower() or 'country' in error_field.lower():
                    return {
                        "status": "error",
                        "error_message": f"Invalid country code '{normalized_country}'. Please use a valid country (e.g., Brazil=BR, United States=US, etc.)"
                    }
                elif 'address' in error_message.lower():
                    return {
                        "status": "error",
                        "error_message": f"Address format issue: {error_message}. Please provide at least country and city."
                    }
                else:
                    return {
                        "status": "error",
                        "error_message": f"Shipping calculation failed: {error_message}"
                    }

            # Check for warnings (non-critical issues)
            warnings = shipping_data.get("warnings", [])
            warning_messages = [w.get("message", "") for w in warnings] if warnings else []

            cart = shipping_data.get("cart", {})
            delivery_groups = cart.get("deliveryGroups", {}).get("edges", [])

            # Extract shipping options
            shipping_options = []
            for group_edge in delivery_groups:
                group = group_edge.get("node", {})
                options = group.get("deliveryOptions", [])

                for option in options:
                    estimated_cost = option.get("estimatedCost", {})
                    shipping_options.append({
                        "handle": option.get("handle", ""),
                        "title": option.get("title", "Standard Shipping"),
                        "description": option.get("description", ""),
                        "estimatedCost": estimated_cost
                    })

            return {
                "status": "success",
                "shipping_options": shipping_options,
                "total_options": len(shipping_options),
                "cart_totals": cart.get("cost", {}),
                "normalized_country": normalized_country,
                "warnings": warning_messages,
                "delivery_address_used": delivery_address  # For debugging
            }

        return {
            "status": "error",
            "error_message": f"Shipping calculation failed: {result.get('error_message', 'Unknown error')}. Country used: {normalized_country}"
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Unexpected error during shipping calculation: {str(e)}"
        }


# =============================================================================
# EXPORTED API FUNCTIONS
# =============================================================================
# Only the essential functions are exported - all operations go through execute_shopify_operation

# Legacy compatibility functions (kept for agent tool compatibility)
def fetch_shopify_graphql(query: str, variables: Optional[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
    """Legacy compatibility wrapper for direct GraphQL execution."""
    if variables is None:
        variables = {}
    return execute_shopify_graphql(query, variables, api="admin", **kwargs)


def fetch_shopify_storefront_graphql(query: str, variables: Optional[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
    """Legacy compatibility wrapper for direct GraphQL execution."""
    if variables is None:
        variables = {}
    return execute_shopify_graphql(query, variables, api="storefront", **kwargs)


def validate_graphql_with_mcp(query: str, api: str, **kwargs) -> Dict[str, Any]:
    """Legacy compatibility wrapper for GraphQL validation."""
    if not api:
        api = "admin"
    return validate_graphql_query(query, api)


def introspect_graphql_schema(search_term: str, api: str, **kwargs) -> Dict[str, Any]:
    """Legacy compatibility wrapper for schema introspection."""
    if not api:
        api = "admin"
    return introspect_shopify_schema(search_term, api)


def get_store_info() -> Dict[str, Any]:
    """
    Get basic store information including name and available product types.
    This helps the agent understand what it's actually selling.
    """
    try:
        logger.info("Fetching store information...")

        # Query to get store info and product categories
        store_query = """
        query getStoreInfo {
            shop {
                name
                description
                primaryDomain {
                    host
                }
            }
            products(first: 100) {
                edges {
                    node {
                        productType
                        vendor
                        tags
                    }
                }
            }
        }
        """

        result = execute_shopify_graphql(store_query, {}, "storefront")

        if result["status"] == "success":
            data = result["data"]
            shop = data.get("shop", {})
            products = data.get("products", {}).get("edges", [])

            # Extract unique product types and categories
            product_types = set()
            vendors = set()
            tags = set()

            for edge in products:
                node = edge.get("node", {})
                if node.get("productType"):
                    product_types.add(node["productType"])
                if node.get("vendor"):
                    vendors.add(node["vendor"])
                if node.get("tags"):
                    for tag in node["tags"]:
                        tags.add(tag)

            store_info = {
                "status": "success",
                "name": shop.get("name", "Our Store"),
                "description": shop.get("description", ""),
                "domain": shop.get("primaryDomain", {}).get("host", ""),
                "product_types": list(product_types),
                "vendors": list(vendors),
                "tags": list(tags),
                "total_products": len(products)
            }

            logger.info(f"Store info fetched successfully: {shop.get('name')} with {len(products)} products")
            return store_info

        logger.error(f"Failed to fetch store info: {result.get('error_message')}")
        return {
            "status": "error",
            "error_message": f"Failed to fetch store info: {result.get('error_message', 'Unknown error')}"
        }

    except Exception as e:
        logger.error(f"Error getting store info: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error_message": f"Error getting store info: {str(e)}"
        }