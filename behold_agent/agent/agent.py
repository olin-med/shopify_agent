from google.adk.agents import Agent
from .prompt import BEHOLD_AGENT_PROMPT
from .tools import (
    fetch_shopify_graphql, 
    validate_graphql_with_mcp, 
    introspect_graphql_schema,
    fetch_shopify_storefront_graphql,
    create_cart,
    modify_cart,
    get_cart,
    create_checkout,
    get_store_policies,
    search_products,
    calculate_shipping_estimate,
    apply_discount_code,
    get_product_recommendations,
    find_product_alternatives,
    get_subscription_products,
    explain_subscription_options,
    create_whatsapp_buttons,
    create_whatsapp_list,
    create_product_showcase,
    create_cart_summary,
    format_checkout_message,
    create_greeting_message
)


root_agent = Agent(
    model="gemini-2.0-flash",
    name="behold_agent",
    description=(
        "Intelligent Shopify sales assistant that proactively helps customers by automatically accessing store data "
        "to provide product recommendations, answer questions, guide purchasing decisions, manage carts, create checkouts, "
        "and calculate shipping fees."
    ),
    instruction=(BEHOLD_AGENT_PROMPT),
    tools=[
        # Admin API tools
        fetch_shopify_graphql, 
        validate_graphql_with_mcp, 
        introspect_graphql_schema,
        # Storefront API tools
        fetch_shopify_storefront_graphql,
        create_cart,
        modify_cart,
        get_cart,
        create_checkout,
        get_store_policies,
        search_products,
        calculate_shipping_estimate,
        apply_discount_code,
        # Intelligence tools
        get_product_recommendations,
        find_product_alternatives,
        get_subscription_products,
        explain_subscription_options,
        # WhatsApp formatting tools
        create_whatsapp_buttons,
        create_whatsapp_list,
        create_product_showcase,
        create_cart_summary,
        format_checkout_message,
        create_greeting_message
    ],
)
