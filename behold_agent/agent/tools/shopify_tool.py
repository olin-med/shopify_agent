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
