from google.adk.agents import Agent
import logging
from .prompt import BEHOLD_AGENT_PROMPT
from .callbacks import before_agent_callback, after_agent_callback
from .tools import (
    fetch_shopify_graphql,
    validate_graphql_with_mcp,
    introspect_graphql_schema,
    fetch_shopify_storefront_graphql,
    execute_shopify_operation,
    get_store_info,
    send_whatsapp_message,
    send_whatsapp_image,
    get_whatsapp_client_info,
    check_whatsapp_status,
    get_whatsapp_qr_info,
    start_whatsapp_bridge,
)

logger = logging.getLogger(__name__)


root_agent = Agent(
    model="gemini-2.5-flash",
    name="behold_agent",
    description=(
        "Intelligent Shopify sales assistant that proactively helps customers by automatically accessing store data "
        "to provide product recommendations, answer questions, guide purchasing decisions, manage carts, create checkouts, "
        "and calculate shipping fees."
    ),
    instruction=(BEHOLD_AGENT_PROMPT),
    tools=[
        # Core GraphQL tools
        fetch_shopify_graphql,
        fetch_shopify_storefront_graphql,
        validate_graphql_with_mcp,
        introspect_graphql_schema,

        # Universal operation tool
        execute_shopify_operation,

        # Store discovery tool
        get_store_info,

        # WhatsApp communication tools
        send_whatsapp_message,
        send_whatsapp_image,
        get_whatsapp_client_info,
        check_whatsapp_status,
        get_whatsapp_qr_info,
        start_whatsapp_bridge,
    ],
    # ADK callbacks for automatically saving messages to state
    before_agent_callback=before_agent_callback,
    after_agent_callback=after_agent_callback,
)
